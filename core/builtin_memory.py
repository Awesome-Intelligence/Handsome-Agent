"""BuiltinMemoryProvider — 内置记忆提供者

实现多层记忆架构：
1. 会话记忆 (Episodic Memory) - 当前会话的短期记忆
2. 用户配置文件 (User Profile) - 用户的长期偏好和信息
3. 事实记忆 (Factual Memory) - 存储的事实和知识
4. 技能记忆 (Skill Memory) - 技能使用历史和模式

参考 Hermes 的多层记忆设计。
"""

import json
import os
import time
from typing import Any, Dict, List, Optional

from .memory_provider import MemoryProvider


class BuiltinMemoryProvider(MemoryProvider):
    """内置记忆提供者 - 支持多层记忆"""

    def __init__(self):
        self._session_id: str = ""
        self._hermes_home: str = ""
        self._platform: str = ""
        
        # 多层记忆存储
        self._episodic_memory: List[Dict[str, Any]] = []      # 会话记忆
        self._user_profile: Dict[str, Any] = {}               # 用户配置文件
        self._factual_memory: Dict[str, Any] = {}             # 事实记忆
        self._skill_memory: Dict[str, Any] = {}               # 技能记忆
        
        # 配置
        self._max_episodic_entries: int = 100
        self._initialized: bool = False

    @property
    def name(self) -> str:
        return "builtin"

    def is_available(self) -> bool:
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        self._session_id = session_id
        self._hermes_home = kwargs.get("hermes_home", os.path.expanduser("~/.handsome-agent"))
        self._platform = kwargs.get("platform", "cli")
        
        # 加载持久化数据
        self._load_profile()
        self._load_factual_memory()
        self._load_skill_memory()
        
        self._initialized = True
        self._log(f"Initialized with session_id={session_id}")

    def _log(self, message: str) -> None:
        """内部日志"""
        import logging
        logger = logging.getLogger(f"BuiltinMemoryProvider[{self.name}]")
        logger.info(message)

    def _get_storage_path(self, filename: str) -> str:
        """获取存储路径"""
        storage_dir = os.path.join(self._hermes_home, "memory")
        os.makedirs(storage_dir, exist_ok=True)
        return os.path.join(storage_dir, filename)

    def _load_profile(self) -> None:
        """加载用户配置文件"""
        path = self._get_storage_path("user_profile.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self._user_profile = json.load(f)
            except Exception:
                self._user_profile = {}
        else:
            self._user_profile = {
                "name": "",
                "preferences": {},
                "goals": [],
                "interests": [],
                "bio": "",
                "created_at": time.time(),
            }

    def _save_profile(self) -> None:
        """保存用户配置文件"""
        path = self._get_storage_path("user_profile.json")
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self._user_profile, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self._log(f"Failed to save profile: {e}")

    def _load_factual_memory(self) -> None:
        """加载事实记忆"""
        path = self._get_storage_path("factual_memory.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self._factual_memory = json.load(f)
            except Exception:
                self._factual_memory = {}
        else:
            self._factual_memory = {}

    def _save_factual_memory(self) -> None:
        """保存事实记忆"""
        path = self._get_storage_path("factual_memory.json")
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self._factual_memory, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self._log(f"Failed to save factual memory: {e}")

    def _load_skill_memory(self) -> None:
        """加载技能记忆"""
        path = self._get_storage_path("skill_memory.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self._skill_memory = json.load(f)
            except Exception:
                self._skill_memory = {}
        else:
            self._skill_memory = {}

    def _save_skill_memory(self) -> None:
        """保存技能记忆"""
        path = self._get_storage_path("skill_memory.json")
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self._skill_memory, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self._log(f"Failed to save skill memory: {e}")

    def system_prompt_block(self) -> str:
        """系统提示块"""
        if not self._initialized:
            return ""
        
        profile = self._user_profile
        if profile.get("name") or profile.get("bio"):
            return (
                f"## User Profile\n"
                f"Name: {profile.get('name', 'Unknown')}\n"
                f"Bio: {profile.get('bio', '')}\n"
                f"Goals: {', '.join(profile.get('goals', []))}\n"
                f"Interests: {', '.join(profile.get('interests', []))}"
            )
        return ""

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """预取相关记忆"""
        if not self._initialized:
            return ""
        
        results = []
        
        # 搜索事实记忆
        for key, value in self._factual_memory.items():
            if query.lower() in key.lower() or (isinstance(value, str) and query.lower() in value.lower()):
                results.append(f"FACT: {key} = {value}")
        
        # 搜索用户配置文件
        profile_text = json.dumps(self._user_profile)
        if query.lower() in profile_text.lower():
            results.append(f"USER: {json.dumps(self._user_profile, ensure_ascii=False)}")
        
        # 搜索会话记忆（最近的）
        recent_memory = self._episodic_memory[-20:]
        for entry in reversed(recent_memory):
            content = entry.get("content", "")
            if query.lower() in content.lower():
                results.append(f"CONTEXT: {content}")
        
        return "\n".join(results[:10])  # 限制返回数量

    def sync_turn(self, user_content: str, assistant_content: str, *, session_id: str = "") -> None:
        """同步回合到记忆"""
        if not self._initialized:
            return
        
        # 添加到会话记忆
        entry = {
            "timestamp": time.time(),
            "user": user_content[:500],
            "assistant": assistant_content[:500],
            "session_id": session_id or self._session_id,
        }
        self._episodic_memory.append(entry)
        
        # 限制会话记忆大小
        if len(self._episodic_memory) > self._max_episodic_entries:
            self._episodic_memory = self._episodic_memory[-self._max_episodic_entries:]
        
        # 提取事实
        self._extract_facts(user_content, assistant_content)
        
        # 更新技能使用统计
        self._update_skill_usage(assistant_content)

    def _extract_facts(self, user_content: str, assistant_content: str) -> None:
        """从对话中提取事实"""
        # 简单的事实提取逻辑
        # 可以扩展为更复杂的NLP提取
        pass

    def _update_skill_usage(self, content: str) -> None:
        """更新技能使用统计"""
        # 简单的技能使用追踪
        pass

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """返回工具schema"""
        return [
            {
                "name": "memory_save",
                "description": "保存信息到持久化记忆",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "记忆键名"},
                        "value": {"type": "string", "description": "记忆内容"},
                        "category": {"type": "string", "description": "分类: profile, fact, skill"},
                    },
                    "required": ["key", "value"],
                },
            },
            {
                "name": "memory_retrieve",
                "description": "从记忆中检索信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "要检索的键名"},
                    },
                    "required": ["key"],
                },
            },
            {
                "name": "memory_search",
                "description": "搜索记忆内容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索关键词"},
                        "limit": {"type": "integer", "description": "返回数量", "default": 5},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "memory_list",
                "description": "列出所有记忆键名",
                "parameters": {},
            },
            {
                "name": "memory_delete",
                "description": "删除指定记忆",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "要删除的键名"},
                    },
                    "required": ["key"],
                },
            },
        ]

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        """处理工具调用"""
        try:
            if tool_name == "memory_save":
                return self._handle_save(args)
            elif tool_name == "memory_retrieve":
                return self._handle_retrieve(args)
            elif tool_name == "memory_search":
                return self._handle_search(args)
            elif tool_name == "memory_list":
                return self._handle_list(args)
            elif tool_name == "memory_delete":
                return self._handle_delete(args)
            else:
                return json.dumps({"error": f"Unknown tool: {tool_name}"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _handle_save(self, args: Dict[str, Any]) -> str:
        """保存记忆"""
        key = args.get("key")
        value = args.get("value")
        category = args.get("category", "fact")
        
        if category == "profile":
            self._user_profile[key] = value
            self._save_profile()
        else:
            self._factual_memory[key] = value
            self._save_factual_memory()
        
        return json.dumps({"success": True, "message": f"Saved '{key}'"})

    def _handle_retrieve(self, args: Dict[str, Any]) -> str:
        """检索记忆"""
        key = args.get("key")
        
        # 先搜索事实记忆
        if key in self._factual_memory:
            return json.dumps({
                "success": True,
                "value": self._factual_memory[key],
                "source": "factual"
            })
        
        # 再搜索用户配置文件
        if key in self._user_profile:
            return json.dumps({
                "success": True,
                "value": self._user_profile[key],
                "source": "profile"
            })
        
        return json.dumps({"success": False, "error": "Key not found"})

    def _handle_search(self, args: Dict[str, Any]) -> str:
        """搜索记忆"""
        query = args.get("query", "").lower()
        limit = args.get("limit", 5)
        
        results = []
        
        # 搜索事实记忆
        for key, value in self._factual_memory.items():
            if query in key.lower() or (isinstance(value, str) and query in value.lower()):
                results.append({"key": key, "value": value, "source": "factual"})
        
        # 搜索用户配置文件
        for key, value in self._user_profile.items():
            if query in key.lower() or (isinstance(value, str) and query in value.lower()):
                results.append({"key": key, "value": value, "source": "profile"})
        
        # 搜索会话记忆
        for entry in self._episodic_memory[-20:]:
            content = f"{entry.get('user', '')} {entry.get('assistant', '')}"
            if query in content.lower():
                results.append({"content": content[:100], "source": "episodic"})
        
        return json.dumps({
            "success": True,
            "results": results[:limit],
            "total": len(results)
        })

    def _handle_list(self, args: Dict[str, Any]) -> str:
        """列出所有键"""
        keys = {
            "factual": list(self._factual_memory.keys()),
            "profile": list(self._user_profile.keys()),
            "episodic_count": len(self._episodic_memory)
        }
        return json.dumps({"success": True, "keys": keys})

    def _handle_delete(self, args: Dict[str, Any]) -> str:
        """删除记忆"""
        key = args.get("key")
        
        if key in self._factual_memory:
            del self._factual_memory[key]
            self._save_factual_memory()
            return json.dumps({"success": True, "message": f"Deleted '{key}'"})
        
        if key in self._user_profile:
            del self._user_profile[key]
            self._save_profile()
            return json.dumps({"success": True, "message": f"Deleted '{key}'"})
        
        return json.dumps({"success": False, "error": "Key not found"})

    def shutdown(self) -> None:
        """关闭时保存所有数据"""
        if self._initialized:
            self._save_profile()
            self._save_factual_memory()
            self._save_skill_memory()
            self._log("Shutdown complete")


# 创建单例实例
builtin_memory_provider = BuiltinMemoryProvider()
