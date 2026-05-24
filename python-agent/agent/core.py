"""Agent 核心逻辑"""

from loguru import logger

from api.client import ApiClient, ApiError
from api.endpoints import Endpoints
from .memory import AgentMemory
from .tools import build_tools


class Agent:
    """背单词助手 Agent，通过后端 API 与用户数据交互"""

    def __init__(self, api_client: ApiClient):
        self.api = Endpoints(api_client)
        self.memory = AgentMemory()
        self.tools = build_tools(self.api)
        self._tool_map = {t.name: t for t in self.tools}

    # ---- 身份认证 ----

    def login(self, username: str, password: str) -> str:
        """登录并保存会话"""
        try:
            self.api._c.login(username, password)
            self.memory.put("last_user", username)
            return f"登录成功！用户: {username}"
        except ApiError as e:
            return f"登录失败: {e}"

    def register(self, username: str, password: str, nickname: str = "") -> str:
        """注册新用户"""
        try:
            self.api._c.register(username, password, nickname)
            return f"注册成功！用户: {username}"
        except ApiError as e:
            return f"注册失败: {e}"

    # ---- 核心能力 ----

    def run(self, command: str, **kwargs) -> str:
        """执行命令并返回结果"""
        tool = self._tool_map.get(command)
        if not tool:
            available = ", ".join(self._tool_map.keys())
            return f"未知命令: {command}。可用命令: {available}"

        logger.info(f"执行命令: {command} | 参数: {kwargs}")
        try:
            result = tool.fn(**kwargs)
            return self._format_result(command, result)
        except ApiError as e:
            return f"操作失败: {e}"
        except Exception as e:
            logger.exception(f"执行 {command} 时出错")
            return f"发生未知错误: {e}"

    def _format_result(self, command: str, result) -> str:
        """格式化返回结果为可读文本"""
        if result is None:
            return "操作成功（无返回数据）"

        if command == "search_word":
            return self._format_word(result)
        elif command == "get_points_balance":
            return f"💰 当前积分余额: {result.get('balance', 'N/A')}"
        elif command == "daily_checkin":
            return (f"✅ {result.get('message', '签到成功!')} | "
                    f"获得 {result.get('pointsEarned', 0)} 积分 | "
                    f"连续签到 {result.get('continuousDays', 0)} 天")
        elif command == "get_flash_sale_list":
            return self._format_flash_sales(result)
        elif command == "get_store_books":
            return self._format_books(result)
        elif command == "get_user_books":
            return self._format_books(result)
        else:
            return str(result)

    def _format_word(self, words) -> str:
        if isinstance(words, list):
            lines = []
            for w in words[:5]:
                lines.append(f"📖 {w.get('wordText', '')} {w.get('phonetic', '')}")
                lines.append(f"   {w.get('partOfSpeech', '')} {w.get('definition', '')}")
                if w.get('exampleSentence'):
                    lines.append(f"   例句: {w['exampleSentence']}")
            return "\n".join(lines) if lines else "未找到单词"
        return str(words)

    def _format_flash_sales(self, sales) -> str:
        if not sales:
            return "当前没有秒杀活动"
        lines = ["⚡ 秒杀活动列表:"]
        for s in sales:
            lines.append(f"  [{s.get('id')}] {s.get('name', '')} — "
                         f"¥{s.get('price', 0)} | 剩余: {s.get('stock', 0)}")
        return "\n".join(lines)

    def _format_books(self, books) -> str:
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
