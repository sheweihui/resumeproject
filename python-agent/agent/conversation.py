"""对话历史管理"""

import json
import time
import uuid
from pathlib import Path
from typing import Optional

CONV_DIR = Path(__file__).resolve().parent.parent / "data" / "conversations"


class ConversationManager:
    """管理多轮对话历史，持久化到 JSON 文件"""

    def __init__(self, max_history: int = 20):
        self.max_history = max_history
        CONV_DIR.mkdir(parents=True, exist_ok=True)

    def create_conversation(self) -> str:
        """创建新对话，返回 conversation_id"""
        conv_id = uuid.uuid4().hex[:12]
        self._save(conv_id, {
            "id": conv_id,
            "created_at": time.time(),
            "messages": [],
        })
        return conv_id

    def add_message(self, conv_id: str, role: str, content: str) -> None:
        """添加一条消息到对话历史"""
        conv = self._load(conv_id)
        if not conv:
            conv = {"id": conv_id, "created_at": time.time(), "messages": []}

        conv["messages"].append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
        })

        # 截断旧消息以控制长度
        if len(conv["messages"]) > self.max_history:
            conv["messages"] = conv["messages"][-self.max_history:]

        self._save(conv_id, conv)

    def get_history(self, conv_id: str, limit: int = 10) -> list[dict]:
        """获取最近 N 轮对话（用于 LLM 上下文）"""
        conv = self._load(conv_id)
        if not conv:
            return []
        # 取最近 limit 条
        return conv["messages"][-limit:]

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
