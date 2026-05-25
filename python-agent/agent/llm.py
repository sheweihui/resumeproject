"""LLM 集成：对接 DeepSeek API（兼容 OpenAI SDK）"""

import json
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

    # ============================================================
    # Function Calling 支持
    # ============================================================

    def chat_with_tools(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        tools: Optional[list[dict]] = None,
    ) -> tuple[str, list[dict]]:
        """
        发送消息并支持工具/函数调用。

        返回 (content, tool_calls_list):
          - content: 文本回复（如果 LLM 只返回工具调用则为空字符串）
          - tool_calls_list: 工具调用列表，每项含 id/type/function/name/arguments
        """
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        kwargs = dict(
            model=self.model,
            messages=full_messages,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
        )
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            logger.debug(f"LLM 请求 (tools={len(tools or [])}): model={self.model}, "
                         f"messages={len(full_messages)}条")
            response = self.client.chat.completions.create(**kwargs)
            message = response.choices[0].message

            content = message.content or ""
            tool_calls = []
            if message.tool_calls:
                for tc in message.tool_calls:
                    tool_calls.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    })

            logger.debug(f"LLM 回复: content_len={len(content)}, tool_calls={len(tool_calls)}")
            return content, tool_calls

        except APIError as e:
            logger.error(f"LLM API 错误: {e}")
            return f"抱歉，AI 服务出错了: {e.message}", []
        except Exception as e:
            logger.exception("LLM 调用异常")
            return f"抱歉，处理请求时发生了错误: {str(e)}", []
