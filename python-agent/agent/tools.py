"""Agent 工具集 — 可被 Agent 调用的能力"""

from typing import Callable
from dataclasses import dataclass, field
from loguru import logger

from api.endpoints import Endpoints
from api.client import ApiError


@dataclass
class Tool:
    name: str
    description: str
    fn: Callable
    parameters: dict = field(default_factory=dict)


def build_tools(api: Endpoints) -> list[Tool]:
    """构建 Agent 可用的工具列表"""
    return [
        Tool(
            name="search_word",
            description="查询单词的释义、音标、例句",
            fn=api.search_word,
            parameters={"keyword": "要查询的单词（英文）"},
        ),
        Tool(
            name="ai_fill_word",
            description="使用 AI 自动补全单词的音标、释义、例句等信息",
            fn=api.ai_fill_word,
            parameters={"word_text": "单词（英文）"},
        ),
        Tool(
            name="get_points_balance",
            description="查看当前用户的积分余额",
            fn=api.get_points_balance,
        ),
        Tool(
            name="daily_checkin",
            description="每日签到获取积分",
            fn=api.checkin,
        ),
        Tool(
            name="get_store_books",
            description="获取商店中的单词书列表",
            fn=lambda page=1, size=10: api.get_store_books(page, size),
            parameters={"page": "页码（可选，默认1）", "size": "每页数量（可选，默认10）"},
        ),
        Tool(
            name="get_flash_sale_list",
            description="查看当前秒杀活动列表",
            fn=api.get_flash_sale_list,
        ),
        Tool(
            name="get_user_books",
            description="获取用户的单词本列表",
            fn=lambda: api.get_book_list(api._c.auth.get_user_id()),
        ),
        Tool(
            name="get_book_words",
            description="获取单词本中的单词列表",
            fn=api.get_words_by_book,
            parameters={"book_id": "单词本 ID"},
        ),
    ]


# ============================================================
# OpenAI Function Calling 格式转换
# ============================================================

def to_openai_tool(tool: Tool) -> dict:
    """将 Tool 转换为 OpenAI function calling 格式"""
    properties = {}
    required = []
    for k, v in (tool.parameters or {}).items():
        properties[k] = {"type": "string", "description": v}
        required.append(k)

    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


def to_openai_tools(tools: list[Tool]) -> list[dict]:
    """批量转换工具列表为 OpenAI 格式"""
    return [to_openai_tool(t) for t in tools]


# ============================================================
# 工具执行
# ============================================================

def execute_tool(tool_name: str, arguments: dict, api: Endpoints) -> str:
    """执行工具并返回可读的结果字符串"""
    tool_map = {t.name: t for t in build_tools(api)}
    tool = tool_map.get(tool_name)
    if not tool:
        return f"错误：未知操作 '{tool_name}'"

    logger.info(f"执行工具: {tool_name} | 参数: {arguments}")
    try:
        result = tool.fn(**arguments)
        return _format_tool_result(tool_name, result)
    except ApiError as e:
        logger.error(f"工具 {tool_name} API 错误: {e}")
        return f"操作失败: {e}"
    except Exception as e:
        logger.exception(f"执行工具 {tool_name} 异常")
        return f"执行出错: {e}"


# ============================================================
# 结果格式化
# ============================================================

def _format_tool_result(name: str, result) -> str:
    """格式化工具执行结果（字符串形式，供 LLM 消费）"""
    if result is None:
        return "操作成功（无返回数据）"

    if name == "search_word":
        return _format_word_result(result)
    if name == "ai_fill_word":
        return _format_word_result(result)
    if name == "get_points_balance":
        return f"当前积分余额: {result.get('balance', 'N/A')}"
    if name == "daily_checkin":
        return (f"签到成功! 获得 {result.get('pointsEarned', 0)} 积分, "
                f"连续签到 {result.get('continuousDays', 0)} 天. "
                f"{result.get('message', '')}")
    if name == "get_flash_sale_list":
        return _format_flash_sales(result)
    if name in ("get_store_books", "get_user_books"):
        return _format_book_list(result)
    if name == "get_book_words":
        return _format_word_list(result)

    return str(result)


def _format_word_result(words) -> str:
    """格式化单词查询结果"""
    if isinstance(words, list) and words:
        return _format_single_word(words[0])
    if isinstance(words, dict):
        return _format_single_word(words)
    return "未找到该单词信息。"


def _format_single_word(w: dict) -> str:
    parts = []
    if w.get("wordText"):
        parts.append(f"单词: {w['wordText']}")
    if w.get("phonetic"):
        parts.append(f"音标: {w['phonetic']}")
    if w.get("partOfSpeech"):
        parts.append(f"词性: {w['partOfSpeech']}")
    if w.get("definition"):
        parts.append(f"释义: {w['definition']}")
    if w.get("exampleSentence"):
        parts.append(f"例句: {w['exampleSentence']}")
    if w.get("exampleTranslation"):
        parts.append(f"翻译: {w['exampleTranslation']}")
    return " | ".join(parts)


def _format_flash_sales(sales) -> str:
    if not sales:
        return "当前没有秒杀活动"
    lines = ["⚡ 秒杀活动列表:"]
    for s in sales:
        lines.append(f"  [{s.get('id')}] {s.get('name', '')} — "
                     f"¥{s.get('price', 0)} | 剩余: {s.get('stock', 0)}")
    return "\n".join(lines)


def _format_book_list(books) -> str:
    if not books:
        return "暂无数据"
    if isinstance(books, dict) and "records" in books:
        books = books["records"]
    lines = ["📚 单词书列表:"]
    for b in books[:10]:
        name = b.get("bookName") or b.get("name", "")
        price = b.get("price", "免费")
        lines.append(f"  [{b.get('id')}] {name} | ¥{price}")
    return "\n".join(lines)


def _format_word_list(words) -> str:
    if not words:
        return "该单词本中没有单词"
    lines = [f"共 {len(words)} 个单词:"]
    for w in words[:20]:
        text = w.get("wordText", "?")
        definition = w.get("definition", "")
        preview = definition[:50] + "..." if len(definition) > 50 else definition
        lines.append(f"  {text} — {preview}")
    return "\n".join(lines)
