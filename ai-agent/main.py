import os
import time
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field


app = FastAPI(title="WordFlash AI Agent", version="0.1.0")

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8080")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")
MODEL_TIMEOUT = float(os.getenv("MODEL_TIMEOUT", "12"))


class ChatRequest(BaseModel):
    user_id: int = Field(..., description="WordFlash user id")
    message: str = Field(..., min_length=1, description="User message")
    token: Optional[str] = Field(default=None, description="Optional backend token")


class ToolCallResult(BaseModel):
    tool: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    latency_ms: int


class ChatResponse(BaseModel):
    answer: str
    mode: str
    tools: List[ToolCallResult]
    latency_ms: int


LOCAL_KNOWLEDGE = [
    {
        "title": "积分说明",
        "content": "WordFlash 中用户可以通过签到、学习任务和活动获得积分，积分可以用于购买单词书或参加限时活动。",
        "keywords": ["积分", "签到", "购买", "商城"],
    },
    {
        "title": "单词本说明",
        "content": "用户可以创建自己的单词本，也可以从积分商城购买公共单词书，购买后系统会复制单词关联到用户单词本。",
        "keywords": ["单词本", "单词书", "购买", "学习"],
    },
    {
        "title": "秒杀说明",
        "content": "限时秒杀活动使用 Redis 预扣库存和用户幂等标记，后端会校验库存、积分余额和活动时间。",
        "keywords": ["秒杀", "限时", "库存", "活动"],
    },
]


def now_ms() -> int:
    return int(time.time() * 1000)


def retrieve_context(message: str) -> List[Dict[str, str]]:
    matched: List[Dict[str, str]] = []
    for item in LOCAL_KNOWLEDGE:
        if any(keyword in message for keyword in item["keywords"]):
            matched.append({"title": item["title"], "content": item["content"]})
    return matched[:3]


def infer_tools(message: str) -> List[str]:
    tools: List[str] = []
    if any(word in message for word in ["积分", "余额", "多少分"]):
        tools.append("get_points")
    if any(word in message for word in ["签到", "打卡"]):
        tools.append("checkin")
    if any(word in message for word in ["单词本", "单词书", "我的单词"]):
        tools.append("list_books")
    return tools


async def call_backend_tool(tool: str, req: ChatRequest) -> ToolCallResult:
    start = now_ms()
    headers = {}
    if req.token:
        headers["Authorization"] = f"Bearer {req.token}"

    # These paths are intentionally thin adapters. Adjust them to match backend auth/interceptor rules.
    path_map = {
        "get_points": f"/api/store/points/balance?userId={req.user_id}",
        "checkin": "/api/store/checkin",
        "list_books": f"/api/store/books?page=1&size=5&userId={req.user_id}",
    }
    method_map = {
        "get_points": "GET",
        "checkin": "POST",
        "list_books": "GET",
    }

    path = path_map.get(tool)
    if not path:
        return ToolCallResult(tool=tool, success=False, error="unknown tool", latency_ms=now_ms() - start)

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.request(method_map[tool], BACKEND_BASE_URL + path, headers=headers)
            response.raise_for_status()
            return ToolCallResult(tool=tool, success=True, data=response.json(), latency_ms=now_ms() - start)
    except Exception as exc:
        # Degrade instead of failing the whole chat.
        return ToolCallResult(tool=tool, success=False, error=str(exc), latency_ms=now_ms() - start)


def build_prompt(req: ChatRequest, contexts: List[Dict[str, str]], tools: List[ToolCallResult]) -> str:
    context_text = "\n".join(f"- {item['title']}: {item['content']}" for item in contexts) or "暂无检索上下文"
    tool_text = "\n".join(
        f"- {tool.tool}: {'成功' if tool.success else '失败'}; data={tool.data}; error={tool.error}"
        for tool in tools
    ) or "未调用工具"
    return f"""
你是 WordFlash 单词学习助手，请用简洁、友好的中文回答用户。

用户问题：{req.message}

检索上下文：
{context_text}

工具调用结果：
{tool_text}

回答要求：
1. 如果工具失败，给出友好提示，不要暴露异常堆栈。
2. 如果上下文不足，说明可以继续补充问题。
3. 回答尽量具体，围绕单词学习、积分、单词本和活动场景。
""".strip()


async def call_model(prompt: str) -> Optional[str]:
    if not DEEPSEEK_API_KEY:
        return None

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "你是一个单词学习应用中的 AI 学习助手。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
    }
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=MODEL_TIMEOUT) as client:
            response = await client.post(f"{DEEPSEEK_BASE_URL}/v1/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except Exception:
        return None


def fallback_answer(req: ChatRequest, contexts: List[Dict[str, str]], tools: List[ToolCallResult]) -> str:
    if tools:
        success_tools = [tool for tool in tools if tool.success]
        if success_tools:
            return "我已经根据当前可用的后端数据帮你查询了相关信息。你可以继续问我积分、单词本或学习计划相关问题。"
        return "当前后端工具暂时不可用，我可以先根据本地知识给你基础建议，稍后再尝试查询具体数据。"
    if contexts:
        return contexts[0]["content"]
    return "我可以帮你查询积分、查看单词本、解释秒杀活动或给出单词学习建议。你可以换一种更具体的问法试试。"


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "wordflash-ai-agent",
        "model_configured": bool(DEEPSEEK_API_KEY),
        "backend_base_url": BACKEND_BASE_URL,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    start = now_ms()
    contexts = retrieve_context(req.message)
    tool_names = infer_tools(req.message)
    tool_results: List[ToolCallResult] = []

    for tool_name in tool_names[:3]:
        tool_results.append(await call_backend_tool(tool_name, req))

    prompt = build_prompt(req, contexts, tool_results)
    model_answer = await call_model(prompt)
    if model_answer:
        return ChatResponse(answer=model_answer, mode="model", tools=tool_results, latency_ms=now_ms() - start)

    return ChatResponse(
        answer=fallback_answer(req, contexts, tool_results),
        mode="fallback",
        tools=tool_results,
        latency_ms=now_ms() - start,
    )
