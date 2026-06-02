"""
知识库管理 — 文档向量化存储 + 语义检索

使用 chromadb (ONNX embedding) 实现向量检索。
无需 torch / GPU，chromadb 内置 all-MiniLM-L6-v2 ONNX 模型。

用户上传文章/笔记 → 分块 → chromadb 自动 embedding → 持久化到磁盘
RAG 检索时自动搜知识库，返回相关片段作为上下文。
"""

import json
import uuid
from pathlib import Path
from typing import Optional

from loguru import logger

import chromadb
from chromadb.utils import embedding_functions

# ---------- 配置 ----------
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CHROMA_DIR = DATA_DIR / "chroma_db"
DOCS_INDEX = DATA_DIR / "knowledge_docs.json"
CHUNK_SIZE = 500      # 每块字符数
CHUNK_OVERLAP = 50    # 块之间重叠字符数

# ---------- 文档注册表 ----------
# 轻量 JSON 文件，记录 doc_id → {title, chunk_count, user_id}
# chromadb 存向量和文本，这个文件管文档元数据


def _load_docs() -> dict[str, dict]:
    if DOCS_INDEX.exists():
        try:
            with open(DOCS_INDEX, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_docs(docs: dict[str, dict]):
    DOCS_INDEX.parent.mkdir(parents=True, exist_ok=True)
    with open(DOCS_INDEX, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)


# ============================================================
# KnowledgeBase 对外 API
# ============================================================


class KnowledgeBase:
    """
    知识库 — 文档管理 + 语义检索

    基于 chromadb（ONNX embedding 模型），纯 Python 运行。
    数据持久化到 data/chroma_db/ 目录。

    用法：
        kb = KnowledgeBase()
        kb.add_document("AI 概述", "人工智能是...", user_id=1)
        results = kb.search("什么是 AI", top_k=3)
        kb.list_documents()
        kb.delete_document("doc_id")
    """

    def __init__(self):
        self._client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self._ef = embedding_functions.DefaultEmbeddingFunction()
        self._collection = self._client.get_or_create_collection(
            name="knowledge_base",
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},  # 余弦相似度
        )

        # 加载文档注册表
        self._docs = _load_docs()

        logger.info(f"📚 知识库已加载: {len(self._docs)} 篇文档, "
                     f"{self._collection.count()} 个向量片段")

    @property
    def available(self) -> bool:
        """知识库始终可用"""
        try:
            self._collection.count()
            return True
        except Exception:
            return False

    @property
    def doc_count(self) -> int:
        return len(self._docs)

    @property
    def chunk_count(self) -> int:
        try:
            return self._collection.count()
        except Exception:
            return 0

    # ---------- 增删查 ----------

    def add_document(self, title: str, content: str, user_id: int = 0) -> dict:
        """
        添加文档：分块 → chromadb 自动 embedding → 持久化

        参数：
            title: 文档标题
            content: 文档正文（纯文本）
            user_id: 用户 ID（用于隔离不同用户的数据）

        返回：
            {"id": "xxx", "title": "xxx", "chunk_count": 5}
        """
        doc_id = uuid.uuid4().hex[:12]
        chunks = self._chunk_text(content)

        ids: list[str] = []
        texts: list[str] = []
        metadatas: list[dict] = []

        for i, text in enumerate(chunks):
            chunk_id = f"{doc_id}_{i}"
            ids.append(chunk_id)
            texts.append(text)
            metadatas.append({
                "doc_id": doc_id,
                "title": title,
                "user_id": user_id,
                "chunk_index": i,
            })

        self._collection.add(
            documents=texts,
            metadatas=metadatas,
            ids=ids,
        )

        # 更新文档注册表
        self._docs[doc_id] = {
            "title": title,
            "chunk_count": len(chunks),
            "user_id": user_id,
        }
        _save_docs(self._docs)

        logger.info(f"📄 文档已添加: {title} ({len(chunks)} 个片段, id={doc_id})")
        return {"id": doc_id, "title": title, "chunk_count": len(chunks)}

    def search(
        self,
        query: str,
        top_k: int = 3,
        user_id: Optional[int] = None,
    ) -> list[dict]:
        """
        语义搜索，返回最相关的文档片段

        参数：
            query: 搜索关键词/问题
            top_k: 返回前 k 条
            user_id: 可选，按用户过滤

        返回：
            [{"content": "...", "title": "...", "doc_id": "...", "score": 0.85}, ...]
        """
        if not query.strip():
            return []

        try:
            # 按用户过滤
            where = None
            if user_id is not None:
                where = {"user_id": user_id}

            results = self._collection.query(
                query_texts=[query],
                n_results=min(top_k, self._collection.count() or 1),
                where=where,
            )

            # chromadb 返回格式:
            # { ids: [[...]], distances: [[...]], documents: [[...]], metadatas: [[...]] }
            formatted = []
            if results and results.get("ids") and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    formatted.append({
                        "content": results["documents"][0][i],
                        "title": results["metadatas"][0][i].get("title", ""),
                        "doc_id": results["metadatas"][0][i].get("doc_id", ""),
                        # chromadb distance 是 L2/余弦距离，转成相似度分数
                        "score": round(1 - results["distances"][0][i], 4),
                    })

            return formatted

        except Exception as e:
            logger.warning(f"知识库搜索异常: {e}")
            return []

    def list_documents(self) -> list[dict]:
        """列出所有文档"""
        return [
            {"id": k, "title": v["title"], "chunk_count": v["chunk_count"]}
            for k, v in self._docs.items()
        ]

    def delete_document(self, doc_id: str) -> bool:
        """删除文档及其所有向量片段"""
        if doc_id not in self._docs:
            return False

        # 找到该文档的所有 chunk ID
        try:
            # chromadb 支持按 metadata 批量删除
            self._collection.delete(where={"doc_id": doc_id})
        except Exception as e:
            logger.warning(f"删除 chromadb 片段失败: {e}")
            return False

        removed = self._docs.pop(doc_id, None)
        if removed:
            _save_docs(self._docs)
            logger.info(f"🗑️ 文档已删除: {doc_id} ({removed['chunk_count']} 个片段)")
            return True
        return False

    # ---------- 分块 ----------

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE,
                    overlap: int = CHUNK_OVERLAP) -> list[str]:
        """
        将长文本分割成重叠的块

        策略：
            - 优先在段落 (\\n\\n) 处切分
            - 其次在句子 (。！？.!?) 处切分
            - 最后按字符数硬切
        """
        if not text:
            return []

        text = text.strip()
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            if start + chunk_size >= len(text):
                chunks.append(text[start:])
                break

            candidate = text[start:start + chunk_size]

            # 优先在段落边界切
            para_break = candidate.rfind("\n\n")
            if para_break > chunk_size // 2:
                end = start + para_break
                chunks.append(text[start:end])
                start = end
                continue

            # 其次在句子边界切
            for sep in ("。", "！", "？", "！", ". ", "! ", "? "):
                last_sep = candidate.rfind(sep)
                if last_sep > chunk_size // 2:
                    end = start + last_sep + len(sep)
                    chunks.append(text[start:end])
                    start = end
                    break
            else:
                chunks.append(candidate)
                start = start + chunk_size

            start = start - overlap

        return chunks
