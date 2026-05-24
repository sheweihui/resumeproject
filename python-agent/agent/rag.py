"""RAG 检索模块：从后端拉取用户数据作为上下文"""

from typing import Optional
from api.client import ApiClient
from api.endpoints import Endpoints
from loguru import logger


class RAGRetriever:
    """从后端检索与用户问题相关的上下文"""

    def __init__(self, api: Endpoints):
        self.api = api

    async def retrieve_context(self, user_id: Optional[int], message: str) -> str:
        """
        根据用户问题检索相关上下文，返回拼装后的文本。
        """
        parts: list[str] = []
        message_lower = message.lower()

        # 1. 提取可能的单词（纯英文单词）
        words = self._extract_words(message)
        if words:
            for word in words[:3]:
                try:
                    result = self.api.search_word(word)
                    if result:
                        word_info = self._format_word_context(result)
                        if word_info:
                            parts.append(word_info)
                except Exception as e:
                    logger.debug(f"查词失败 {word}: {e}")

        # 2. 获取用户学习概况（如果有 user_id）
        if user_id:
            try:
                stats = self._get_user_stats(user_id)
                if stats:
                    parts.append(stats)
            except Exception as e:
                logger.debug(f"获取用户统计失败: {e}")

        context = "\n\n".join(parts)
        logger.debug(f"RAG 检索到的上下文长度: {len(context)} 字符")
        return context

    def _extract_words(self, text: str) -> list[str]:
        """从文本中提取可能的英文单词"""
        import re
        # 匹配 2-20 个字母的纯英文单词
        candidates = re.findall(r"\b[a-zA-Z]{2,20}\b", text)
        # 过滤掉常见停用词
        stopwords = {
            "the", "is", "are", "was", "were", "has", "have", "had", "do",
            "does", "did", "will", "would", "could", "should", "may", "might",
            "can", "shall", "am", "be", "been", "being", "it", "its", "this",
            "that", "these", "those", "what", "which", "who", "whom", "whose",
            "when", "where", "why", "how", "a", "an", "and", "or", "but", "if",
            "because", "so", "than", "too", "very", "just", "about", "above",
            "after", "again", "all", "also", "any", "back", "each", "every",
            "for", "from", "get", "got", "here", "him", "his", "into", "let",
            "like", "make", "more", "most", "much", "must", "my", "no", "not",
            "now", "of", "on", "one", "only", "other", "our", "out", "over",
            "own", "say", "she", "some", "tell", "their", "them", "then",
            "there", "they", "thing", "things", "think", "through", "upon",
            "use", "used", "way", "well", "with", "without", "you", "your",
            "want", "know", "help", "test", "learn", "study", "recommend",
            "need", "give", "tell", "show", "check", "see", "look",
        }
        return [w for w in candidates if w.lower() not in stopwords]

    def _format_word_context(self, result) -> str:
        """格式化单词查询结果为上下文"""
        if isinstance(result, list) and result:
            w = result[0]
        elif isinstance(result, dict):
            w = result
        else:
            return ""

        fields = []
        if w.get("wordText"):
            fields.append(f"单词: {w['wordText']}")
        if w.get("phonetic"):
            fields.append(f"音标: {w['phonetic']}")
        if w.get("partOfSpeech"):
            fields.append(f"词性: {w['partOfSpeech']}")
        if w.get("definition"):
            fields.append(f"释义: {w['definition']}")
        if w.get("exampleSentence"):
            fields.append(f"例句: {w['exampleSentence']}")
        if w.get("exampleTranslation"):
            fields.append(f"翻译: {w['exampleTranslation']}")

        return " | ".join(fields) if fields else ""

    def _get_user_stats(self, user_id: int) -> str:
        """获取用户学习统计"""
        try:
            balance = self.api.get_points_balance()
            stats_parts = [f"用户ID: {user_id}"]
            if balance and isinstance(balance, dict):
                stats_parts.append(f"积分余额: {balance.get('balance', '?')}")
            return " | ".join(stats_parts)
        except Exception:
            return ""
