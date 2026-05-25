"""RAG 检索模块：从后端拉取用户数据作为上下文"""

import asyncio
import time
from typing import Optional
from loguru import logger

from api.endpoints import Endpoints


class RAGRetriever:
    """从后端检索与用户问题相关的上下文"""

    def __init__(self, api: Endpoints):
        self.api = api
        # 简单内存缓存：key -> (value, expiry)
        self._cache: dict[str, tuple[str, float]] = {}

    def _cache_get(self, key: str) -> Optional[str]:
        entry = self._cache.get(key)
        if entry and entry[1] > time.time():
            return entry[0]
        if entry:
            del self._cache[key]
        return None

    def _cache_set(self, key: str, value: str, ttl: int = 60):
        self._cache[key] = (value, time.time() + ttl)

    async def retrieve_context(self, user_id: Optional[int], message: str) -> str:
        """
        根据用户问题和身份检索相关上下文，返回拼装后的 Markdown 文本。
        """
        parts: list[str] = []

        # 1. 提取可能的英文单词并查词
        words = self._extract_words(message)
        if words:
            for word in words[:3]:
                cache_key = f"word:{word}"
                cached = self._cache_get(cache_key)
                if cached:
                    parts.append(cached)
                else:
                    try:
                        result = await asyncio.to_thread(self.api.search_word, word)
                        if result:
                            word_info = self._format_word_context(result)
                            if word_info:
                                section = f"## 单词查询\n{word_info}"
                                parts.append(section)
                                self._cache_set(cache_key, section, ttl=120)
                    except Exception as e:
                        logger.debug(f"查词失败 {word}: {e}")

        # 2. 获取用户学习概况
        if user_id:
            cache_key = f"profile:{user_id}"
            cached = self._cache_get(cache_key)
            if cached:
                parts.append(cached)
            else:
                try:
                    profile = await self._get_user_profile(user_id)
                    if profile:
                        section = f"## 用户学习概况\n{profile}"
                        parts.append(section)
                        self._cache_set(cache_key, section)
                except Exception as e:
                    logger.debug(f"获取用户概况失败: {e}")

        context = "\n\n".join(parts)
        logger.debug(f"RAG 检索到的上下文长度: {len(context)} 字符")
        return context

    async def _get_user_profile(self, user_id: int) -> str:
        """获取用户个性化学习概况"""
        lines: list[str] = []

        # 积分余额
        try:
            balance = await asyncio.to_thread(self.api.get_points_balance)
            if balance and isinstance(balance, dict):
                lines.append(f"- 积分余额: {balance.get('balance', '?')}")
        except Exception:
            pass

        # 用户信息
        try:
            info = await asyncio.to_thread(self.api.get_user_info, user_id)
            if info and isinstance(info, dict):
                nickname = info.get("nickname") or info.get("username", "")
                if nickname:
                    lines.append(f"- 用户名: {nickname}")
        except Exception:
            pass

        # 单词本列表 + 单词数
        try:
            books = await asyncio.to_thread(self.api.get_book_list, user_id)
            if books and isinstance(books, list):
                book_names = [b.get("bookName", "?") for b in books[:3]]
                lines.append(f"- 单词本: {', '.join(book_names)}")

                # 第一个单词本的单词数
                if books:
                    first_book = books[0]
                    book_id = first_book.get("id")
                    book_name = first_book.get("bookName", "")
                    if book_id:
                        try:
                            words = await asyncio.to_thread(
                                self.api.get_words_by_book, book_id
                            )
                            if words and isinstance(words, list):
                                lines.append(f"- 当前学习: {book_name} 共 {len(words)} 词")
                        except Exception:
                            pass
        except Exception:
            pass

        if not lines:
            lines.append(f"- 用户ID: {user_id}")

        return "\n".join(lines)

    # ---- 低层工具 ----

    def _extract_words(self, text: str) -> list[str]:
        """从文本中提取可能的英文单词"""
        import re
        candidates = re.findall(r"\b[a-zA-Z]{2,20}\b", text)
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
