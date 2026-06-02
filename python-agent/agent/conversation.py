"""对话历史管理"""

import json
import time
import uuid
from pathlib import Path
from typing import Optional

CONV_DIR = Path(__file__).resolve().parent.parent / "data" / "conversations"

# 超过此条数时触发摘要
SUMMARY_THRESHOLD = 15
# 保留最近多少条不摘要
KEEP_LATEST = 10


class ConversationManager:
    """管理多轮对话历史，持久化到 JSON 文件"""

    def __init__(self, max_history: int = 20):
        self.max_history = max_history
        CONV_DIR.mkdir(parents=True, exist_ok=True)

    def create_conversation(self, user_id: Optional[int] = None) -> str:
        """创建新对话，返回 conversation_id"""
        conv_id = uuid.uuid4().hex[:12]
        self._save(conv_id, {
            "id": conv_id,
            "user_id": user_id,
            "created_at": time.time(),
            "last_active": time.time(),
            "message_count": 0,
            "topic": "",
            "summary": "",
            "messages": [],
        })
        return conv_id

    def find_by_user(self, user_id: int) -> Optional[str]:
        """找到该用户最近活跃的对话 ID，没有则返回 None"""
        latest_id = None
        latest_time = 0.0
        for path in CONV_DIR.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("user_id") == user_id and data.get("last_active", 0) > latest_time:
                    latest_time = data["last_active"]
                    latest_id = data["id"]
            except Exception:
                continue
        return latest_id

    def add_message(self, conv_id: str, role: str, content: str) -> None:
        """添加一条消息到对话历史"""
        conv = self._load(conv_id)
        if not conv:
            conv = {
                "id": conv_id, "user_id": None, "created_at": time.time(),
                "last_active": time.time(), "message_count": 0, "topic": "",
                "summary": "", "messages": [],
            }

        conv["messages"].append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
        })
        conv["last_active"] = time.time()
        conv["message_count"] = conv.get("message_count", 0) + 1

        # 超出阈值时做抽取式摘要
        if conv["message_count"] >= SUMMARY_THRESHOLD and not conv.get("summary"):
            if len(conv["messages"]) > KEEP_LATEST:
                old = conv["messages"][:-KEEP_LATEST]
                summary_lines = []
                for m in old:
                    label = "用户" if m["role"] == "user" else "AI"
                    text = m["content"][:120].replace("\n", " ")
                    summary_lines.append(f"{label}: {text}")
                conv["summary"] = "\n".join(summary_lines[-8:])
                conv["messages"] = conv["messages"][-KEEP_LATEST:]

        # 截断旧消息
        if len(conv["messages"]) > self.max_history:
            conv["messages"] = conv["messages"][-self.max_history:]

        self._save(conv_id, conv)

    def get_history(self, conv_id: str, limit: int = 10) -> list[dict]:
        """获取最近 N 轮对话（用于 LLM 上下文）"""
        conv = self._load(conv_id)
        if not conv:
            return []

        messages = conv["messages"][-limit:]

        # 如果有摘要，作为 system 消息前置
        if conv.get("summary"):
            messages.insert(0, {
                "role": "system",
                "content": f"以下是对话早期的摘要（供参考）:\n{conv['summary']}",
            })

        return messages

    def update_metadata(self, conv_id: str, **kwargs) -> None:
        """更新对话元数据（user_id, topic 等）"""
        conv = self._load(conv_id)
        if conv:
            for key in ("user_id", "topic"):
                if key in kwargs:
                    conv[key] = kwargs[key]
            conv["last_active"] = time.time()
            self._save(conv_id, conv)

    def clean_expired(self, max_age_days: int = 7) -> int:
        """清理超过 N 天未活跃的对话，返回清理数量"""
        now = time.time()
        cutoff = now - max_age_days * 86400
        cleaned = 0
        for path in CONV_DIR.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("last_active", 0) < cutoff:
                    path.unlink()
                    cleaned += 1
            except Exception:
                path.unlink()
                cleaned += 1
        if cleaned:
            logger = __import__("loguru").logger
            logger.info(f"清理了 {cleaned} 个过期对话")
        return cleaned

    def clear(self, conv_id: str) -> None:
        """清空对话历史"""
        path = CONV_DIR / f"{conv_id}.json"
        if path.exists():
            path.unlink()

    def _load(self, conv_id: str) -> Optional[dict]:
        path = CONV_DIR / f"{conv_id}.json"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return None
        return None

    def _save(self, conv_id: str, data: dict) -> None:
        path = CONV_DIR / f"{conv_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
