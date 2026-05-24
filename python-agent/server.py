#!/usr/bin/env python3
"""
背单词助手 Agent — FastAPI 服务

启动:
    python server.py
    uvicorn server:app --host 0.0.0.0 --port 8000

前端通过 /agent/chat 接口与 AI 对话。
"""

import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from config.settings import AGENT_HOST, AGENT_PORT, LOG_LEVEL, LOG_FILE, AGENT_NAME, AGENT_VERSION, LLM_API_KEY
from api.client import ApiClient
from api.endpoints import Endpoints
from api.schemas import ChatRequest, ChatResponse, ErrorResponse
from agent.llm import LLMClient
from agent.rag import RAGRetriever
from agent.conversation import ConversationManager

# ------------------------------------------------------------
# 全局组件
# ------------------------------------------------------------
api_client: ApiClient = None
api_endpoints: Endpoints = None
llm: LLMClient = None
rag: RAGRetriever = None
conversations: ConversationManager = None


def init_components():
    global api_client, api_endpoints, llm, rag, conversations
    api_client = ApiClient()
    api_endpoints = Endpoints(api_client)
    rag = RAGRetriever(api_endpoints)
    conversations = ConversationManager()

    if LLM_API_KEY and LLM_API_KEY != "sk-your-deepseek-api-key":
        llm = LLMClient()
        logger.info("✅ LLM 已初始化 (DeepSeek)")
    else:
        llm = None
        logger.warning("⚠️ LLM_API_KEY 未配置，将使用本地模式回复")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_components()
    yield


app = FastAPI(
    title=AGENT_NAME,
    version=AGENT_VERSION,
    description="背单词 App AI 助手 — RAG + 对话服务",
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
"""


def _build_system_prompt(context: str = "") -> str:
    return SYSTEM_PROMPT.format(context=context or "暂无额外上下文。")


# ------------------------------------------------------------
# 路由
# ------------------------------------------------------------
@app.get("/agent/health")
def health():
    return {
        "status": "ok",
        "version": AGENT_VERSION,
        "llm_ready": llm is not None,
    }


@app.post("/agent/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    # 1. 创建/获取对话 ID
    conv_id = req.conversation_id or conversations.create_conversation()
    logger.info(f"[对话 {conv_id}] 用户: {req.message[:60]}")

    # 2. RAG 检索上下文
    context = await rag.retrieve_context(req.user_id, req.message)

    # 3. 获取对话历史
    history = conversations.get_history(conv_id)

    # 4. 保存用户消息
    conversations.add_message(conv_id, "user", req.message)

    # 5. 调用 LLM 或本地回退
    if llm:
        messages = [{"role": m["role"], "content": m["content"]} for m in history[-6:]]
        reply = llm.chat(messages, system_prompt=_build_system_prompt(context))
    else:
        reply = _local_fallback(req.message, context)

    # 6. 保存 AI 回复
    conversations.add_message(conv_id, "assistant", reply)

    logger.info(f"[对话 {conv_id}] AI: {reply[:80]}...")
    return ChatResponse(reply=reply, conversation_id=conv_id)


@app.get("/agent/conversations/{conv_id}/history")
def get_history(conv_id: str):
    """获取指定对话的历史（用于前端回显）"""
    messages = conversations.get_history(conv_id, limit=50)
    return {"conversation_id": conv_id, "messages": messages}


@app.delete("/agent/conversations/{conv_id}")
def clear_conversation(conv_id: str):
    """清空对话"""
    conversations.clear(conv_id)
    return {"status": "ok"}


# ------------------------------------------------------------
# 本地回退（无 LLM 时使用）
# ------------------------------------------------------------
def _local_fallback(message: str, context: str = "") -> str:
    """当 LLM 不可用时，使用内置简单逻辑回复"""
    msg = message.lower()

    if context and ("单词:" in context or "释义:" in context):
        return f"我找到了相关信息：\n\n{context}\n\n还想了解其他单词吗？"

    if "hello" in msg or "hi" in msg or "你好" in msg:
        return "你好！我是你的英语学习助手。我可以帮你查单词、推荐学习内容、测试词汇量。请问有什么可以帮你的？"

    if any(kw in msg for kw in ("建议", "怎么学", "方法", "如何背")):
        return ("背单词小建议：\n\n"
                "1. **少量多次**：每天背 10-15 个新词，不要贪多\n"
                "2. **结合例句**：把单词放到句子里记，不要死记硬背\n"
                "3. **定期复习**：第1天、第3天、第7天、第30天复习\n"
                "4. **多感官结合**：看拼写、听发音、写下来、读出来\n"
                "5. **用起来**：试着用新学的单词造句或写日记\n\n"
                "需要我帮你制定学习计划吗？")

    if "测试" in msg or "题目" in msg or "考考" in msg:
        return ("好的！来测试一下你的词汇量：\n\n"
                "**'beautiful' 是什么意思？**\n\n"
                "A. 聪明的\nB. 美丽的\nC. 勇敢的\nD. 善良的\n\n"
                "告诉我你的答案！")

    if "解释" in msg or "句子" in msg:
        return ("你可以发一个英文句子给我，我来帮你分析句子结构、"
                "解释每个单词的含义和语法作用！比如：\n"
                '"The quick brown fox jumps over the lazy dog."')

    if context:
        return f"根据你的学习数据：\n\n{context}\n\n有什么具体想了解的吗？"

    return ("收到你的消息了！你可以：\n\n"
            "• **查单词**：直接输入英文单词\n"
            "• **学英语**：输入 '学习建议'\n"
            "• **测词汇**：输入 '测试'\n"
            "• **分析句子**：发送一个英文句子\n\n"
            "有什么我能帮你的吗？")


# ------------------------------------------------------------
# 入口
# ------------------------------------------------------------
def main():
    logger.remove()
    logger.add(sys.stderr, level=LOG_LEVEL, format="<level>{level:7}</level> | {message}")
    logger.add(LOG_FILE, rotation="10 MB", level="DEBUG")

    import uvicorn
    logger.info(f"🚀 启动 {AGENT_NAME} v{AGENT_VERSION} → http://{AGENT_HOST}:{AGENT_PORT}")
    logger.info(f"📚 LLM 状态: {'已就绪' if llm else '未配置（使用本地模式）'}")
    uvicorn.run(app, host=AGENT_HOST, port=AGENT_PORT)


if __name__ == "__main__":
    main()
