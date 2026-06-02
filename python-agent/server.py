#!/usr/bin/env python3
"""
背单词助手 Agent — FastAPI 服务

启动:
    python server.py
    uvicorn server:app --host 0.0.0.0 --port 8000

前端通过 /agent/chat 接口与 AI 对话。
"""

import json
import re
import sys
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from config.settings import (
    AGENT_HOST, AGENT_PORT, LOG_LEVEL, LOG_FILE,
    AGENT_NAME, AGENT_VERSION, LLM_API_KEY,
    TOOL_CALL_MAX_ROUNDS, CONVERSATION_MAX_AGE_DAYS,
)
from api.client import ApiClient
from api.endpoints import Endpoints
from api.schemas import (
    ChatRequest, ChatResponse, WordEnrichRequest, WordEnrichResponse,
    KnowledgeUploadRequest, KnowledgeUploadResponse, KnowledgeDocument,
)
from agent.llm import LLMClient
from agent.rag import RAGRetriever
from agent.conversation import ConversationManager
from agent.mcp_client import MCPClient
from agent.knowledge_base import KnowledgeBase

# ------------------------------------------------------------
# 全局组件
# ------------------------------------------------------------
api_client: ApiClient = None
api_endpoints: Endpoints = None
llm: LLMClient = None
rag: RAGRetriever = None
conversations: ConversationManager = None
mcp_client: MCPClient = None
kb: KnowledgeBase = None


def init_components():
    global api_client, api_endpoints, llm, rag, conversations, kb
    api_client = ApiClient()
    api_endpoints = Endpoints(api_client)
    kb = KnowledgeBase()
    rag = RAGRetriever(api_endpoints, kb=kb)
    conversations = ConversationManager()

    conversations.clean_expired(max_age_days=CONVERSATION_MAX_AGE_DAYS)

    if LLM_API_KEY and LLM_API_KEY != "sk-your-deepseek-api-key":
        llm = LLMClient()
        logger.info("LLM 已初始化 (DeepSeek)")
    else:
        llm = None
        logger.warning("LLM_API_KEY 未配置，将使用本地模式回复")


def check_backend_connectivity() -> dict:
    """启动时检查后端连通性"""
    results = {}
    try:
        import requests
        resp = requests.get(
            "http://localhost:8080/",
            timeout=3,
            headers={"Accept": "application/json"}
        )
        results["backend"] = f"connected (HTTP {resp.status_code})"
        logger.info(f"后端连通性检查: OK (HTTP {resp.status_code})")
    except requests.ConnectionError:
        results["backend"] = "unreachable: 无法连接到 localhost:8080"
        logger.warning("后端连通性检查: 无法连接 - 请确认后端已启动")
    except Exception as e:
        results["backend"] = f"unreachable: {e}"
        logger.warning(f"后端连通性检查: 异常 ({e})")
    return results


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_components()
    check_backend_connectivity()

    # 初始化 MCP 客户端
    global mcp_client
    try:
        mcp_client = MCPClient()
        await mcp_client.connect()
    except Exception as e:
        logger.warning(f"MCP 初始化失败，将使用本地模式: {e}")
        mcp_client = None

    yield

    if mcp_client:
        await mcp_client.close()
    logger.info("Agent 服务关闭")


app = FastAPI(
    title=AGENT_NAME,
    version=AGENT_VERSION,
    description="背单词 App AI 助手 — RAG + 对话 + Function Calling",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------
# 请求中间件（计时 + 请求 ID）
# ------------------------------------------------------------

@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = uuid.uuid4().hex[:8]
    start = time.time()
    response = await call_next(request)
    elapsed = (time.time() - start) * 1000
    logger.info(f"[{request_id}] {request.method} {request.url.path} "
                f"→ {response.status_code} ({elapsed:.0f}ms)")
    response.headers["X-Request-ID"] = request_id
    return response


# ------------------------------------------------------------
# Prompt 模板
# ------------------------------------------------------------
SYSTEM_PROMPT = """你是一个专业的英语学习助手，帮助用户背单词、学英语。

## 你的能力
1. 查单词：解释单词含义、音标、词性、例句
2. 推荐学习内容：根据用户水平推荐单词
3. 测试词汇量：出题测试用户
4. 解释句子：分析句子结构和含义
5. 学习建议：提供背单词方法和技巧

## 行为准则
- 回答简洁清晰，使用中文解释
- 涉及单词时标注音标、词性、中文释义
- 适当举例帮助理解
- 鼓励用户，保持积极正面
- 如果不知道答案，诚实告知，不要编造

## 上下文信息
{context}

## 可用操作
当用户要求执行以下操作时，请调用相应的函数（function calling）：
{tool_descriptions}

注意：如果用户只是提问或聊天（比如"hello"、"背单词有什么技巧"），直接回答即可，不需要调用函数。
"""


def _build_system_prompt(context: str = "") -> str:
    """构建带上下文和工具描述的系统提示词"""
    tool_descriptions = mcp_client.get_tool_descriptions() if mcp_client else "暂无可用操作。"
    return SYSTEM_PROMPT.format(
        context=context or "暂无额外上下文。",
        tool_descriptions=tool_descriptions,
    )


# ------------------------------------------------------------
# 路由
# ------------------------------------------------------------

@app.get("/agent/health")
def health():
    try:
        import psutil
        process = psutil.Process()
        mem = process.memory_info().rss / 1024 / 1024
        uptime = time.time() - process.create_time()
    except ImportError:
        mem = 0
        uptime = 0

    return {
        "status": "ok",
        "version": AGENT_VERSION,
        "llm_ready": llm is not None,
        "mcp_ready": mcp_client is not None and mcp_client.connected,
        "knowledge_base": kb is not None and kb.available,
        "uptime_s": round(uptime),
        "memory_mb": round(mem, 1) if mem else 0,
        "rag_cache_size": rag._cache.size if rag else 0,
    }


# ------------------------------------------------------------
# 知识库 API
# ------------------------------------------------------------


@app.post("/agent/knowledge/upload",
          response_model=KnowledgeUploadResponse)
def upload_knowledge(req: KnowledgeUploadRequest):
    """上传文档到知识库"""
    if not kb or not kb.available:
        raise HTTPException(status_code=503, detail="知识库不可用")

    if not req.title.strip():
        raise HTTPException(status_code=400, detail="标题不能为空")
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="内容不能为空")

    result = kb.add_document(req.title, req.content, req.user_id or 0)
    return KnowledgeUploadResponse(
        **result,
        message=f"上传成功，已分块为 {result['chunk_count']} 个片段",
    )


@app.get("/agent/knowledge/documents")
def list_knowledge_documents():
    """列出知识库中的所有文档"""
    if not kb or not kb.available:
        return {"documents": []}
    docs = kb.list_documents()
    return {"documents": docs}


@app.delete("/agent/knowledge/documents/{doc_id}")
def delete_knowledge_document(doc_id: str):
    """删除知识库中的文档"""
    if not kb or not kb.available:
        raise HTTPException(status_code=503, detail="知识库不可用")
    kb.delete_document(doc_id)
    return {"status": "ok", "doc_id": doc_id}


@app.post("/agent/knowledge/search")
def search_knowledge(query: str, user_id: int = 0, top_k: int = 3):
    """搜索知识库（调试用）"""
    if not kb or not kb.available:
        return {"results": []}
    results = kb.search(query, top_k=top_k, user_id=user_id if user_id else None)
    return {"results": results}


@app.post("/agent/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    # 1. Token 注入（同时持久化到 auth.json 供 MCP Server 读取）
    if req.token:
        api_client.auth.set_token(
            token=req.token,
            user_id=req.user_id or 0,
        )
        # 同步写入 auth.json，MCP Server 子进程通过 _reload_auth() 读取
        from api.auth import AuthSession
        api_client.auth.save_session(AuthSession(
            token=req.token,
            user_id=req.user_id or 0,
            username=f"user_{req.user_id or 0}",
        ))

    # 2. 创建/获取对话（优先按 user_id 续上次的对话）
    if req.conversation_id:
        conv_id = req.conversation_id
        conversations.update_metadata(conv_id, user_id=req.user_id)
    elif req.user_id:
        conv_id = conversations.find_by_user(req.user_id) or conversations.create_conversation(user_id=req.user_id)
    else:
        conv_id = conversations.create_conversation()

    user_msg_preview = req.message[:60].replace("\n", " ")
    logger.info(f"[对话 {conv_id}] 用户: {user_msg_preview}")

    # 3. 保存用户消息
    conversations.add_message(conv_id, "user", req.message)

    # 4. RAG 检索
    context = await rag.retrieve_context(req.user_id, req.message)

    # 5. 无 LLM 降级
    if not llm:
        reply = _local_fallback(req.message, context)
        conversations.add_message(conv_id, "assistant", reply)
        return ChatResponse(reply=reply, conversation_id=conv_id)

    # 6. 构建消息 + 工具定义
    history = conversations.get_history(conv_id)
    messages = [{"role": m["role"], "content": m["content"]} for m in history]
    tool_defs = mcp_client.get_tool_defs() if mcp_client else []
    system_prompt = _build_system_prompt(context)

    # 7. Tool-calling 循环
    final_reply = ""
    for rnd in range(1, TOOL_CALL_MAX_ROUNDS + 1):
        content, tool_calls = llm.chat_with_tools(messages, system_prompt, tool_defs)

        if not tool_calls:
            final_reply = content
            break

        logger.info(f"[对话 {conv_id}] 第 {rnd} 轮工具调用: {len(tool_calls)} 个")

        for tc in tool_calls:
            try:
                fn_name = tc["function"]["name"]
                fn_args = _safe_parse_json(tc["function"]["arguments"])
            except (KeyError, json.JSONDecodeError) as e:
                logger.warning(f"解析 tool_call 失败: {e}")
                continue

            logger.info(f"  执行工具: {fn_name}({fn_args})")
            result = await mcp_client.call_tool(fn_name, fn_args)

            assistant_msg = {"role": "assistant", "content": content if content else None}
            if tc:
                assistant_msg["tool_calls"] = [tc]
            messages.append(assistant_msg)

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })

    if not final_reply:
        logger.warning(f"[对话 {conv_id}] 工具循环结束但未获得回复")
        final_reply = "抱歉，处理请求时出现了问题，请稍后再试。"

    # 8. 保存回复
    conversations.add_message(conv_id, "assistant", final_reply)

    # 9. 首次消息推断话题
    try:
        conv_data = conversations._load(conv_id)
        if conv_data and conv_data.get("message_count", 0) <= 2:
            topic = _detect_topic(req.message)
            if topic:
                conversations.update_metadata(conv_id, topic=topic)
    except Exception:
        pass

    logger.info(f"[对话 {conv_id}] AI: {final_reply[:80]}...")
    return ChatResponse(reply=final_reply, conversation_id=conv_id)


@app.post("/agent/word/enrich", response_model=WordEnrichResponse)
def enrich_word(req: WordEnrichRequest):
    word_text = req.word_text.strip()
    if not word_text:
        raise HTTPException(status_code=400, detail="单词不能为空")
    if not llm:
        raise HTTPException(status_code=503, detail="LLM 不可用，无法补全单词")

    logger.info(f"[单词补全] {word_text} (user_id={req.user_id})")

    prompt = (
        f"请提供以下英文单词的详细信息，以JSON格式返回：\n"
        f"单词：{word_text}\n\n"
        f"要求返回以下字段：\n"
        f"- wordText: 单词本身\n"
        f"- phonetic: 音标（使用国际音标）\n"
        f"- partOfSpeech: 词性（如 n., v., adj., adv. 等）\n"
        f"- definition: 中文释义（简洁明了）\n"
        f"- exampleSentence: 英文例句（简单易懂）\n"
        f"- exampleTranslation: 例句的中文翻译\n\n"
        f"只返回JSON数据，不要有其他文字说明。"
    )

    reply = llm.chat(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="你是一个单词学习助手，必须只返回纯JSON格式数据。"
    )

    logger.info(f"[单词补全] {word_text} → {reply[:100]}...")
    return WordEnrichResponse(content=reply, word_text=word_text)


@app.get("/agent/conversations/{conv_id}/history")
def get_history(conv_id: str):
    messages = conversations.get_history(conv_id, limit=50)
    return {"conversation_id": conv_id, "messages": messages}


@app.delete("/agent/conversations/{conv_id}")
def clear_conversation(conv_id: str):
    conversations.clear(conv_id)
    return {"status": "ok"}


# ------------------------------------------------------------
# 辅助函数
# ------------------------------------------------------------

def _safe_parse_json(text: str) -> dict:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}


def _detect_topic(message: str) -> str:
    m = message.lower()

    if re.search(r"[a-z]{3,}", m) and not re.match(
        r"^(你好|hello|hi|help|嗨|哈喽|您好)$", m.strip()
    ):
        if any(kw in m for kw in ("意思", "什么", "翻译", "怎么读", "发音", "单词")):
            return "单词查询"
        return "英语学习"

    if "签到" in m or "checkin" in m or "打卡" in m:
        return "每日签到"
    if "积分" in m or "points" in m or "余额" in m:
        return "积分查询"
    if "单词本" in m or "book" in m or "词书" in m:
        return "单词本管理"
    if "秒杀" in m or "flash" in m or "抢购" in m:
        return "秒杀活动"
    if "建议" in m or "方法" in m or "技巧" in m or "怎么学" in m:
        return "学习建议"
    if "测试" in m or "题目" in m or "考" in m:
        return "词汇测试"

    return "日常对话"


# ------------------------------------------------------------
# 本地回退（无 LLM 时使用）
# ------------------------------------------------------------
def _local_fallback(message: str, context: str = "") -> str:
    msg = message.lower()

    if context and ("单词:" in context or "释义:" in context):
        return f"我找到了相关信息：\n\n{context}\n\n还想了解其他单词吗？"

    if "hello" in msg or "hi" in msg or "你好" in msg:
        return ("你好！我是你的英语学习助手。我可以帮你查单词、"
                "推荐学习内容、测试词汇量。请问有什么可以帮你的？")

    if any(kw in msg for kw in ("建议", "怎么学", "方法", "如何背")):
        return ("背单词小建议：\n\n"
                "1. 少量多次：每天背 10-15 个新词，不要贪多\n"
                "2. 结合例句：把单词放到句子里记，不要死记硬背\n"
                "3. 定期复习：第1天、第3天、第7天、第30天复习\n"
                "4. 多感官结合：看拼写、听发音、写下来、读出来\n"
                "5. 用起来：试着用新学的单词造句或写日记\n\n"
                "需要我帮你制定学习计划吗？")

    if "测试" in msg or "题目" in msg or "考考" in msg:
        return ("好的！来测试一下你的词汇量：\n\n"
                "'beautiful' 是什么意思？\n\n"
                "A. 聪明的\nB. 美丽的\nC. 勇敢的\nD. 善良的\n\n"
                "告诉我你的答案！")

    if "解释" in msg or "句子" in msg:
        return ("你可以发一个英文句子给我，我来帮你分析句子结构、"
                "解释每个单词的含义和语法作用！比如：\n"
                '"The quick brown fox jumps over the lazy dog."')

    if context:
        return f"根据你的学习数据：\n\n{context}\n\n有什么具体想了解的吗？"

    return ("收到你的消息了！你可以：\n\n"
            "* 查单词：直接输入英文单词\n"
            "* 学英语：输入'学习建议'\n"
            "* 测词汇：输入'测试'\n"
            "* 分析句子：发送一个英文句子\n\n"
            "有什么我能帮你的吗？")


# ------------------------------------------------------------
# 入口
# ------------------------------------------------------------
def main():
    logger.remove()
    logger.add(sys.stderr, level=LOG_LEVEL, format="<level>{level:7}</level> | {message}")
    logger.add(LOG_FILE, rotation="10 MB", level="DEBUG")

    import uvicorn
    logger.info(f"启动 {AGENT_NAME} v{AGENT_VERSION} → http://{AGENT_HOST}:{AGENT_PORT}")
    uvicorn.run(app, host=AGENT_HOST, port=AGENT_PORT)


if __name__ == "__main__":
    main()
