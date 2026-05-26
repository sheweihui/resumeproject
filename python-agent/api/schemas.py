"""请求/响应数据模型"""

from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    user_id: Optional[int] = None
    conversation_id: Optional[str] = None
    token: Optional[str] = None  # 后端 JWT token，用于 agent 调用后端 API


class ChatResponse(BaseModel):
    """对话响应"""
    reply: str
    conversation_id: str


class WordEnrichRequest(BaseModel):
    """单词补全请求"""
    word_text: str
    user_id: Optional[int] = None


class WordEnrichResponse(BaseModel):
    """单词补全响应"""
    content: str
    word_text: str


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    code: int = -1
