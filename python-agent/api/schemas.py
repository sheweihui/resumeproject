"""请求/响应数据模型"""

from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    user_id: Optional[int] = None
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    """对话响应"""
    reply: str
    conversation_id: str


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    code: int = -1
