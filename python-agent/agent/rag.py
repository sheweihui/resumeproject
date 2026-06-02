"""RAG 检索模块：从后端拉取用户数据作为上下文"""

import asyncio
import re
import time
from collections import OrderedDict
from typing import Optional
from loguru import logger

from api.endpoints import Endpoints

# 知识库（可选注入，由 server.py 传入）
try:
    from agent.knowledge_base import KnowledgeBase
    HAS_KB = True
except ImportError:
    HAS_KB = False
    KnowledgeBase = None

# 英语停用词（模块级常量）
_STOPWORDS: set[str] = {
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

# RAG 缓存配置
_RAG_CACHE_MAX = 128  # 最大缓存条目数
_RAG_CACHE_TTL = 60   # 默认过期时间（秒）


class _LRUCache:
    """带 TTL 和 LRU 淘汰的内存缓存"""

    def __init__(self, maxsize: int = _RAG_CACHE_MAX, default_ttl: int = _RAG_CACHE_TTL):
        self._maxsize = maxsize
        self._default_ttl = default_ttl
        self._data: OrderedDict[str, tuple[str, float]] = OrderedDict()

    def get(self, key: str) -> Optional[str]:
        entry = self._data.get(key)
        if entry is None:
            return None
        value, expiry = entry
        if expiry < time.time():
            del self._data[key]
            return None
        # LRU: 移到末尾
        self._data.move_to_end(key)
        return value

    def set(self, key: str, value: str, ttl: Optional[int] = None):
        expiry = time.time() + (ttl if ttl is not None else self._default_ttl)
        self._data[key] = (value, expiry)
        self._data.move_to_end(key)
        # LRU 淘汰
        while len(self._data) > self._maxsize:
            self._data.popitem(last=False)

    def clear(self, key: Optional[str] = None):
        if key:
            self._data.pop(key, None)
        else:
            self._data.clear()

    @property
    def size(self) -> int:
        return len(self._data)


class RAGRetriever:
    """从后端检索与用户问题相关的上下文"""

    def __init__(self, api: Endpoints, kb: 'KnowledgeBase | None' = None):
        self.api = api
        self.kb = kb if HAS_KB else None
        self._cache = _LRUCache()

    def clear_cache(self, key: Optional[str] = None):
        self._cache.clear(key)

    # ---- 主入口 ----

    async def retrieve_context(self, user_id: Optional[int], message: str) -> str:
        """
        根据用户问题和身份检索相关上下文。

        并发执行所有独立查询：公共查词、个人查词、用户概况。
        返回拼装后的 Markdown 文本。
        """
        words = self._extract_words(message)
        tasks: list[asyncio.Task] = []

        if words:
            for word in words[:3]:
                tasks.append(asyncio.create_task(self._search_public_word(word)))
                if user_id:
                    tasks.append(asyncio.create_task(self._search_my_word(user_id, word)))

        if user_id:
            tasks.append(asyncio.create_task(self._get_user_profile(user_id)))
            if self.kb:
                tasks.append(asyncio.create_task(self._search_knowledge_base(user_id, message)))

        if not tasks:
            return ""

        results = await asyncio.gather(*tasks, return_exceptions=True)

        parts: list[str] = []
        for r in results:
            if isinstance(r, Exception):
                logger.debug(f"RAG 子任务异常: {r}")
                continue
            if r and isinstance(r, str) and r.strip():
                parts.append(r)

        # 按标题去重
        seen: set[str] = set()
        deduped: list[str] = []
        for p in parts:
            key = next(
                (line for line in p.split("\n") if line.startswith("## ")),
                p[:60],
            )
            if key not in seen:
                seen.add(key)
                deduped.append(p)

        context = "\n\n".join(deduped)
        logger.debug(f"RAG 上下文: {len(context)} 字符, {len(deduped)} 个片段")
        return context

    # ---- 子任务 ----

    async def _search_public_word(self, word: str) -> Optional[str]:
        cache_key = f"word:{word}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        try:
            result = await asyncio.to_thread(self.api.search_word, word)
            word_info = self._format_word_context(result)
            if word_info:
                section = f"## 单词查询\n{word_info}"
                self._cache.set(cache_key, section, ttl=120)
                return section
        except Exception as e:
            logger.debug(f"查词失败 {word}: {e}")

        return None

    async def _search_my_word(self, user_id: int, word: str) -> Optional[str]:
        cache_key = f"myword:{user_id}:{word}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        try:
            result = await asyncio.to_thread(self.api.search_my_word, word)
            if result and isinstance(result, list) and result:
                my_info = self._format_my_word_context(result)
                if my_info:
                    section = f"## 我的单词本\n{my_info}"
                    self._cache.set(cache_key, section, ttl=120)
                    return section
        except Exception as e:
            logger.debug(f"搜索个人单词失败 {word}: {e}")

        return None

    async def _get_user_profile(self, user_id: int) -> Optional[str]:
        cache_key = f"profile:{user_id}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        balance_task = asyncio.to_thread(self.api.get_points_balance)
        info_task = asyncio.to_thread(self.api.get_user_info, user_id)
        books_task = asyncio.to_thread(self.api.get_book_list, user_id)

        balance, info, books = await asyncio.gather(
            balance_task, info_task, books_task,
            return_exceptions=True,
        )

        lines: list[str] = []

        if isinstance(balance, dict) and balance.get("balance") is not None:
            lines.append(f"- 积分余额: {balance['balance']}")

        if isinstance(info, dict):
            nickname = info.get("nickname") or info.get("username", "")
            if nickname:
                lines.append(f"- 用户名: {nickname}")

        if isinstance(books, list) and books:
            lines.append(f"- 单词本数量: {len(books)}")

            preview_tasks = []
            valid_books = []
            for book in books[:5]:
                book_id = book.get("id")
                word_count = book.get("wordCount", 0)
                if book_id and word_count and word_count > 0:
                    preview_tasks.append(
                        asyncio.to_thread(self.api.get_words_by_book, book_id)
                    )
                    valid_books.append(book)
                else:
                    valid_books.append(book)
                    preview_tasks.append(None)

            if preview_tasks:
                word_results = await asyncio.gather(
                    *[t for t in preview_tasks if t is not None],
                    return_exceptions=True,
                )
            else:
                word_results = []

            word_idx = 0
            for i, book in enumerate(valid_books):
                book_name = book.get("bookName", "?")
                word_count = book.get("wordCount", 0)
                source = "购买" if book.get("sourceType") == 2 else "自建"
                lines.append(f"  - [{book.get('id')}] 《{book_name}》({source}) — {word_count} 词")

                if preview_tasks[i] is not None and word_idx < len(word_results):
                    r = word_results[word_idx]
                    word_idx += 1
                    if isinstance(r, list) and r:
                        previews = [w.get("wordText", "?") for w in r[:5]]
                        lines.append(f"    包含: {', '.join(previews)}{'...' if len(r) > 5 else ''}")

        if not lines:
            lines.append(f"- 用户ID: {user_id}")

        section = f"## 用户学习概况\n" + "\n".join(lines)
        self._cache.set(cache_key, section)
        return section

    # ---- 知识库搜索（向量语义检索） ----

    async def _search_knowledge_base(self, user_id: int, message: str) -> Optional[str]:
        """从用户的知识库中搜索与问题相关的文档片段"""
        if not self.kb:
            return None

        try:
            results = self.kb.search(message, top_k=3, user_id=user_id)
            if results:
                items = []
                for r in results:
                    preview = r["content"][:150].replace("\n", " ")
                    items.append(f"- [{r['title']}](相似度: {r['score']:.2f}) {preview}...")
                section = "## 知识库匹配\n" + "\n".join(items)
                logger.debug(f"知识库命中 {len(results)} 条")
                return section
        except Exception as e:
            logger.debug(f"知识库搜索异常: {e}")

        return None

    # ---- 格式化 ----

    def _format_my_word_context(self, results: list) -> str:
        lines = []
        for w in results[:5]:
            text = w.get("wordText", "?")
            definition = w.get("definition", "")
            tags = w.get("tags", "")
            note = w.get("note", "")
            parts = [f"- {text}"]
            if definition:
                parts.append(f"释义: {definition}")
            if tags:
                parts.append(f"标签: {tags}")
            if note:
                parts.append(f"笔记: {note}")
            lines.append(" | ".join(parts))
        return "\n".join(lines) if lines else ""

    def _format_word_context(self, result) -> str:
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

    @staticmethod
    def _extract_words(text: str) -> list[str]:
        candidates = re.findall(r"\b[a-zA-Z]{2,20}\b", text)
        return [w for w in candidates if w.lower() not in _STOPWORDS]
