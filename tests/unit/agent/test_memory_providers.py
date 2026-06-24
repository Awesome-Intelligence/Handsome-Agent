#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Memory Providers - 用于开发测试的记忆 Provider

这些 Provider 不跨会话持久化，仅用于单元测试和开发调试。
正式代码应使用 BuiltinMemoryProvider。

Usage:
    from tests.unit.agent.test_memory_providers import InMemoryProvider, FileMemoryProvider
"""

import json
import os
import time
import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from agent.memory.memory_provider import MemoryProvider
from agent.memory.streaming_scrubber import build_memory_context_block


@dataclass
class MemoryItem:
    """代表单个记忆条目 - 测试用简化版本"""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    relevance_score: float = 0.0


class InMemoryProvider(MemoryProvider):
    """
    内存记忆 Provider - 用于开发和测试。
    不跨会话持久化。

    WARNING: 仅用于测试环境，正式代码应使用 BuiltinMemoryProvider。
    """

    _warning_issued = False  # 类级别警告标记

    def __init__(self):
        if not InMemoryProvider._warning_issued:
            warnings.warn(
                "InMemoryProvider is for testing only. "
                "Use BuiltinMemoryProvider in production code.",
                UserWarning,
                stacklevel=2
            )
            InMemoryProvider._warning_issued = True

        self.memories: Dict[str, List[MemoryItem]] = {}
        self.counter = 0
        self._turn_cache: Dict[str, List] = {}

    @property
    def name(self) -> str:
        return "memory"

    def is_available(self) -> bool:
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        self._session_id = session_id
        if session_id not in self.memories:
            self.memories[session_id] = []
        self._turn_cache[session_id] = []

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return []

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """检索相关记忆"""
        items = self.memories.get(session_id or self._session_id, [])
        query_lower = query.lower()

        relevant = [m for m in items if query_lower in m.content.lower()]
        if not relevant:
            return ""

        context = "\n".join(f"- {m.content}" for m in relevant[:5])
        return build_memory_context_block(context)

    def sync_turn(self, user_content: str, assistant_content: str, *, session_id: str = "") -> None:
        """缓存轮次以供可能的信息提取"""
        sid = session_id or self._session_id
        if sid in self._turn_cache:
            self._turn_cache[sid].append({
                "user": user_content,
                "assistant": assistant_content,
                "timestamp": time.time()
            })

    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        """从即将被压缩的消息中提取关键点"""
        if not messages:
            return ""

        insights = []
        for msg in messages[-10:]:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user" and len(content) < 200:
                # 使用启发式方法（与 BuiltinMemoryProvider 保持一致）
                is_question = content.strip().endswith("?")
                is_too_short = len(content.strip()) < 10
                is_punctuation_only = all(c in "，。！？、；：" for c in content.strip())

                if not is_question and not is_too_short and not is_punctuation_only:
                    word_count = len(content.split())
                    if word_count >= 3:
                        insights.append(content[:100])

        if not insights:
            return ""

        return f"<memory_insights>\n- " + "\n- ".join(insights[:3]) + "\n</memory_insights>"

    async def store(self, session_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """存储记忆条目到内存"""
        sid = session_id or self._session_id
        if sid not in self.memories:
            self.memories[sid] = []

        memory_id = f"mem_{self.counter}"
        self.counter += 1

        memory = MemoryItem(
            id=memory_id,
            content=content,
            metadata=metadata or {},
            timestamp=time.time()
        )

        self.memories[sid].append(memory)
        return memory_id

    async def retrieve(self, session_id: str, query: str, limit: int = 5) -> List[MemoryItem]:
        """通过简单关键词匹配检索记忆"""
        sid = session_id or self._session_id
        if sid not in self.memories:
            return []

        query_lower = query.lower()
        results = []

        for memory in self.memories[sid]:
            if query_lower in memory.content.lower():
                pos = memory.content.lower().index(query_lower)
                relevance = 1.0 - (pos / len(memory.content))
                memory.relevance_score = relevance
                results.append(memory)

        results.sort(key=lambda x: -x.relevance_score)
        return results[:limit]

    async def get_all(self, session_id: str) -> List[MemoryItem]:
        """获取会话的所有记忆"""
        sid = session_id or self._session_id
        return self.memories.get(sid, [])

    async def delete(self, session_id: str, memory_id: str) -> bool:
        """删除特定记忆"""
        sid = session_id or self._session_id
        if sid not in self.memories:
            return False

        original_count = len(self.memories[sid])
        self.memories[sid] = [
            m for m in self.memories[sid] if m.id != memory_id
        ]

        return len(self.memories[sid]) < original_count

    async def clear(self, session_id: str):
        """清除会话的所有记忆"""
        sid = session_id or self._session_id
        if sid in self.memories:
            del self.memories[sid]


class FileMemoryProvider(MemoryProvider):
    """
    文件记忆 Provider - 使用 JSON 存储。
    跨 Agent 重启持久化。

    WARNING: 仅用于测试环境，正式代码应使用 BuiltinMemoryProvider。
    """

    _warning_issued = False  # 类级别警告标记

    def __init__(self, base_path: str = "./memories"):
        if not FileMemoryProvider._warning_issued:
            warnings.warn(
                "FileMemoryProvider is for testing only. "
                "Use BuiltinMemoryProvider in production code.",
                UserWarning,
                stacklevel=2
            )
            FileMemoryProvider._warning_issued = True

        self.base_path = base_path
        self._session_id = ""
        os.makedirs(base_path, exist_ok=True)

    @property
    def name(self) -> str:
        return "file"

    def is_available(self) -> bool:
        return os.path.exists(self.base_path) or os.access(os.path.dirname(self.base_path), os.W_OK)

    def initialize(self, session_id: str, **kwargs) -> None:
        self._session_id = session_id
        os.makedirs(self.base_path, exist_ok=True)

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return []

    def _get_session_path(self, session_id: str) -> str:
        """获取会话记忆的文件路径"""
        return os.path.join(self.base_path, f"{session_id}.json")

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """从文件检索相关记忆"""
        sid = session_id or self._session_id
        if not sid:
            return ""

        file_path = self._get_session_path(sid)
        if not os.path.exists(file_path):
            return ""

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            query_lower = query.lower()
            relevant = []

            for mem in data.get("memories", []):
                content = mem.get("content", "")
                if query_lower in content.lower():
                    relevant.append(content)

            if not relevant:
                return ""

            context = "\n".join(f"- {e}" for e in relevant[:5])
            return build_memory_context_block(context)
        except Exception:
            return ""

    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        """压缩前提取关键点"""
        if not messages:
            return ""

        insights = []
        for msg in messages[-10:]:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user" and len(content) < 200:
                # 使用启发式方法（与 BuiltinMemoryProvider 保持一致）
                is_question = content.strip().endswith("?")
                is_too_short = len(content.strip()) < 10
                is_punctuation_only = all(c in "，。！？、；：" for c in content.strip())

                if not is_question and not is_too_short and not is_punctuation_only:
                    word_count = len(content.split())
                    if word_count >= 3:
                        insights.append(content[:100])

        if not insights:
            return ""

        return f"<memory_insights>\n- " + "\n- ".join(insights[:3]) + "\n</memory_insights>"

    async def store(self, session_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """存储记忆条目到文件"""
        sid = session_id or self._session_id
        file_path = self._get_session_path(sid)

        # 加载现有记忆
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {"memories": [], "counter": 0}

        # 创建新记忆
        memory_id = f"mem_{data['counter']}"
        data["counter"] += 1

        memory = {
            "id": memory_id,
            "content": content,
            "metadata": metadata or {},
            "timestamp": time.time()
        }

        data["memories"].append(memory)

        # 保存回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return memory_id

    async def retrieve(self, session_id: str, query: str, limit: int = 5) -> List[MemoryItem]:
        """通过关键词匹配检索记忆"""
        sid = session_id or self._session_id
        file_path = self._get_session_path(sid)

        if not os.path.exists(file_path):
            return []

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        query_lower = query.lower()
        results = []

        for mem_dict in data.get("memories", []):
            if query_lower in mem_dict["content"].lower():
                pos = mem_dict["content"].lower().index(query_lower)
                relevance = 1.0 - (pos / len(mem_dict["content"]))

                memory = MemoryItem(
                    id=mem_dict["id"],
                    content=mem_dict["content"],
                    metadata=mem_dict.get("metadata", {}),
                    timestamp=mem_dict.get("timestamp", 0.0),
                    relevance_score=relevance
                )
                results.append(memory)

        results.sort(key=lambda x: -x.relevance_score)
        return results[:limit]

    async def get_all(self, session_id: str) -> List[MemoryItem]:
        """获取会话的所有记忆"""
        sid = session_id or self._session_id
        file_path = self._get_session_path(sid)

        if not os.path.exists(file_path):
            return []

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return [
            MemoryItem(
                id=mem["id"],
                content=mem["content"],
                metadata=mem.get("metadata", {}),
                timestamp=mem.get("timestamp", 0.0)
            )
            for mem in data.get("memories", [])
        ]

    async def delete(self, session_id: str, memory_id: str) -> bool:
        """删除特定记忆"""
        sid = session_id or self._session_id
        file_path = self._get_session_path(sid)

        if not os.path.exists(file_path):
            return False

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        original_count = len(data.get("memories", []))
        data["memories"] = [
            mem for mem in data["memories"] if mem["id"] != memory_id
        ]

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return len(data["memories"]) < original_count

    async def clear(self, session_id: str):
        """清除会话的所有记忆"""
        sid = session_id or self._session_id
        file_path = self._get_session_path(sid)
        if os.path.exists(file_path):
            os.remove(file_path)


__all__ = ['InMemoryProvider', 'FileMemoryProvider']
