"""LLM 集成：对接 DeepSeek API（兼容 OpenAI SDK）"""

from typing import Optional
from openai import OpenAI, APIError
from loguru import logger

from config.settings import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_TIMEOUT,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
)


class LLMClient:
    """封装 LLM 调用"""

    def __init__(
        self,
        api_key: str = LLM_API_KEY,
        base_url: str = LLM_BASE_URL,
        model: str = LLM_MODEL,
    ):
        if not api_key:
            logger.warning("LLM_API_KEY 未配置，对话功能将不可用")
        self.model = model
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=LLM_TIMEOUT,
        )

    def chat(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
    ) -> str:
        """发送对话消息并返回回复"""
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        try:
            logger.debug(f"LLM 请求: model={self.model}, messages={len(full_messages)}条")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
            )
            reply = response.choices[0].message.content or ""
            logger.debug(f"LLM 回复: {reply[:100]}...")
            return reply

        except APIError as e:
            logger.error(f"LLM API 错误: {e}")
            return f"抱歉，AI 服务出错了: {e.message}"
        except Exception as e:
            logger.exception(f"LLM 调用异常")
            return f"抱歉，处理请求时发生了错误: {str(e)}"
