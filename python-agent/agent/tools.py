"""Agent 工具集 — 可被 Agent 调用的能力"""

from typing import Callable
from dataclasses import dataclass, field
from api.endpoints import Endpoints


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
            parameters={"page": "页码", "size": "每页数量"},
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
