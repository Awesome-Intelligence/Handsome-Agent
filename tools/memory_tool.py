#!/usr/bin/env python3
"""
Memory Tool Module - 记忆工具

提供 Agent 记忆管理功能，包括：
- 记忆存储和检索
- 会话历史管理
- 知识库查询

参考 Hermes Agent 的 memory_tool.py 实现。

Usage:
    from tools.memory_tool import memory_tool, MemoryStore
"""

import json
import logging
import os
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Any, List, Optional

from tools.registry import registry


def tool_error(message: str, success: bool = False) -> str:
    """简单的工具错误响应函数"""
    return json.dumps({
        "success": success,
        "error": message
    }, ensure_ascii=False)

logger = logging.getLogger(__name__)

# 记忆目录路径
def get_memory_dir() -> Path:
    """获取记忆存储目录"""
    base_dir = Path.home() / ".handsome_agent"
    memory_dir = base_dir / "memories"
    memory_dir.mkdir(parents=True, exist_ok=True)
    return memory_dir

ENTRY_DELIMITER = "\n§\n"

# 威胁检测模式
_MEMORY_THREAT_PATTERNS = [
    (r'ignore\s+(previous|all|above|prior)\s+instructions', 'prompt_injection'),
    (r'you\s+are\s+now\s+', 'role_hijack'),
    (r'do\s+not\s+tell\s+the\s+user', 'deception_hide'),
    (r'system\s+prompt\s+override', 'sys_prompt_override'),
    (r'disregard\s+(your|all|any)\s+(instructions|rules|guidelines)', 'disregard_rules'),
    (r'act\s+as\s+(if|though)\s+you\s+(have\s+no|don\'t\s+have)\s+(restrictions|limits|rules)', 'bypass_restrictions'),
    (r'curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)', 'exfil_curl'),
    (r'wget\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)', 'exfil_wget'),
    (r'cat\s+[^\n]*(\.env|credentials|\.netrc|\.pgpass|\.npmrc|\.pypirc)', 'read_secrets'),
    (r'authorized_keys', 'ssh_backdoor'),
    (r'\$HOME/\.ssh|\~/\.ssh', 'ssh_access'),
    (r'\$HOME/\.handsome_agent/\.env|\~/\.handsome_agent/\.env', 'handsome_env'),
]

# 不可见字符检测
_INVISIBLE_CHARS = {
    '\u200b', '\u200c', '\u200d', '\u2060', '\ufeff',
    '\u202a', '\u202b', '\u202c', '\u202d', '\u202e',
}


def _scan_memory_content(content: str) -> Optional[str]:
    """扫描记忆内容是否存在威胁模式"""
    # 检测不可见字符
    for char in _INVISIBLE_CHARS:
        if char in content:
            return f"Blocked: content contains invisible unicode character U+{ord(char):04X} (possible injection)."
    
    # 检测威胁模式
    for pattern, pid in _MEMORY_THREAT_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            return f"Blocked: content matches threat pattern '{pid}'. Memory entries are injected into the system prompt and must not contain injection or exfiltration payloads."
    
    return None


def atomic_replace(tmp_path: Path, target_path: Path) -> None:
    """原子化替换文件"""
    try:
        # Windows 使用 os.replace
        if os.name == 'nt':
            os.replace(str(tmp_path), str(target_path))
        else:
            os.rename(str(tmp_path), str(target_path))
    except Exception as e:
        logger.error(f"Atomic replace failed: {e}")
        raise


class MemoryStore:
    """
    持久化记忆存储，支持跨会话保存。

    维护两个平行状态：
      - _system_prompt_snapshot: 加载时的快照，用于系统提示注入，会话期间不变
      - memory_entries / user_entries: 实时状态，通过工具调用修改，持久化到磁盘
    """

    def __init__(self, memory_char_limit: int = 2200, user_char_limit: int = 1375):
        self.memory_entries: List[str] = []
        self.user_entries: List[str] = []
        self.memory_char_limit = memory_char_limit
        self.user_char_limit = user_char_limit
        # 系统提示用的快照
        self._system_prompt_snapshot: Dict[str, str] = {"memory": "", "user": ""}

    def load_from_disk(self):
        """从磁盘加载记忆条目，捕获系统提示快照"""
        mem_dir = get_memory_dir()
        mem_dir.mkdir(parents=True, exist_ok=True)

        self.memory_entries = self._read_file(mem_dir / "MEMORY.md")
        self.user_entries = self._read_file(mem_dir / "USER.md")

        # 去重
        self.memory_entries = list(dict.fromkeys(self.memory_entries))
        self.user_entries = list(dict.fromkeys(self.user_entries))

        # 捕获快照用于系统提示
        self._system_prompt_snapshot = {
            "memory": self._render_block("memory", self.memory_entries),
            "user": self._render_block("user", self.user_entries),
        }

    @staticmethod
    @contextmanager
    def _file_lock(path: Path):
        """获取文件锁用于读写安全"""
        lock_path = path.with_suffix(path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        # 简化的锁机制，不依赖 fcntl
        lock_file = None
        try:
            # 创建锁文件
            lock_file = open(lock_path, 'a+', encoding='utf-8')
            yield
        finally:
            if lock_file:
                lock_file.close()
            # 清理锁文件
            if lock_path.exists():
                try:
                    lock_path.unlink()
                except Exception:
                    pass

    @staticmethod
    def _path_for(target: str) -> Path:
        mem_dir = get_memory_dir()
        if target == "user":
            return mem_dir / "USER.md"
        return mem_dir / "MEMORY.md"

    def _reload_target(self, target: str) -> Optional[str]:
        """重新从磁盘加载目标，返回备份路径（如果检测到外部漂移）"""
        path = self._path_for(target)
        bak = self._detect_external_drift(target)
        fresh = self._read_file(path)
        fresh = list(dict.fromkeys(fresh))  # 去重
        self._set_entries(target, fresh)
        return bak

    def save_to_disk(self, target: str):
        """保存条目到对应文件"""
        get_memory_dir().mkdir(parents=True, exist_ok=True)
        self._write_file(self._path_for(target), self._entries_for(target))

    def _entries_for(self, target: str) -> List[str]:
        if target == "user":
            return self.user_entries
        return self.memory_entries

    def _set_entries(self, target: str, entries: List[str]):
        if target == "user":
            self.user_entries = entries
        else:
            self.memory_entries = entries

    def _char_count(self, target: str) -> int:
        entries = self._entries_for(target)
        if not entries:
            return 0
        return len(ENTRY_DELIMITER.join(entries))

    def _char_limit(self, target: str) -> int:
        if target == "user":
            return self.user_char_limit
        return self.memory_char_limit

    def add(self, target: str, content: str) -> Dict[str, Any]:
        """添加新条目，返回错误如果超出字符限制"""
        content = content.strip()
        if not content:
            return {"success": False, "error": "Content cannot be empty."}

        # 扫描威胁
        scan_error = _scan_memory_content(content)
        if scan_error:
            return {"success": False, "error": scan_error}

        with self._file_lock(self._path_for(target)):
            # 重新从磁盘加载以获取其他会话的写入
            bak = self._reload_target(target)
            if bak:
                return _drift_error(self._path_for(target), bak)

            entries = self._entries_for(target)
            limit = self._char_limit(target)

            # 检查是否已存在
            if content in entries:
                return self._success_response(target, "Entry already exists (no duplicate added).")

            # 计算新的总大小
            new_entries = entries + [content]
            new_total = len(ENTRY_DELIMITER.join(new_entries))

            if new_total > limit:
                current = self._char_count(target)
                return {
                    "success": False,
                    "error": (
                        f"Memory at {current:,}/{limit:,} chars. "
                        f"Adding this entry ({len(content)} chars) would exceed the limit. "
                        f"Replace or remove existing entries first."
                    ),
                    "current_entries": entries,
                    "usage": f"{current:,}/{limit:,}",
                }

            entries.append(content)
            self._set_entries(target, entries)
            self.save_to_disk(target)

        return self._success_response(target, "Entry added.")

    def replace(self, target: str, old_text: str, new_content: str) -> Dict[str, Any]:
        """查找包含 old_text 的条目，替换为 new_content"""
        old_text = old_text.strip()
        new_content = new_content.strip()
        if not old_text:
            return {"success": False, "error": "old_text cannot be empty."}
        if not new_content:
            return {"success": False, "error": "new_content cannot be empty. Use 'remove' to delete entries."}

        # 扫描替换内容的威胁
        scan_error = _scan_memory_content(new_content)
        if scan_error:
            return {"success": False, "error": scan_error}

        with self._file_lock(self._path_for(target)):
            bak = self._reload_target(target)
            if bak:
                return _drift_error(self._path_for(target), bak)

            entries = self._entries_for(target)
            matches = [(i, e) for i, e in enumerate(entries) if old_text in e]

            if not matches:
                return {"success": False, "error": f"No entry matched '{old_text}'."}

            if len(matches) > 1:
                unique_texts = {e for _, e in matches}
                if len(unique_texts) > 1:
                    previews = [e[:80] + ("..." if len(e) > 80 else "") for _, e in matches]
                    return {
                        "success": False,
                        "error": f"Multiple entries matched '{old_text}'. Be more specific.",
                        "matches": previews,
                    }

            idx = matches[0][0]
            limit = self._char_limit(target)

            # 检查替换后是否超出限制
            test_entries = entries.copy()
            test_entries[idx] = new_content
            new_total = len(ENTRY_DELIMITER.join(test_entries))

            if new_total > limit:
                return {
                    "success": False,
                    "error": (
                        f"Replacement would put memory at {new_total:,}/{limit:,} chars. "
                        f"Shorten the new content or remove other entries first."
                    ),
                }

            entries[idx] = new_content
            self._set_entries(target, entries)
            self.save_to_disk(target)

        return self._success_response(target, "Entry replaced.")

    def remove(self, target: str, old_text: str) -> Dict[str, Any]:
        """移除包含 old_text 的条目"""
        old_text = old_text.strip()
        if not old_text:
            return {"success": False, "error": "old_text cannot be empty."}

        with self._file_lock(self._path_for(target)):
            bak = self._reload_target(target)
            if bak:
                return _drift_error(self._path_for(target), bak)

            entries = self._entries_for(target)
            matches = [(i, e) for i, e in enumerate(entries) if old_text in e]

            if not matches:
                return {"success": False, "error": f"No entry matched '{old_text}'."}

            if len(matches) > 1:
                unique_texts = {e for _, e in matches}
                if len(unique_texts) > 1:
                    previews = [e[:80] + ("..." if len(e) > 80 else "") for _, e in matches]
                    return {
                        "success": False,
                        "error": f"Multiple entries matched '{old_text}'. Be more specific.",
                        "matches": previews,
                    }

            idx = matches[0][0]
            entries.pop(idx)
            self._set_entries(target, entries)
            self.save_to_disk(target)

        return self._success_response(target, "Entry removed.")

    def read(self, target: str = "memory") -> Dict[str, Any]:
        """读取当前记忆内容"""
        entries = self._entries_for(target)
        current = self._char_count(target)
        limit = self._char_limit(target)
        return {
            "success": True,
            "target": target,
            "entries": entries,
            "usage": f"{min(100, int((current / limit) * 100) if limit > 0 else 0)}% — {current:,}/{limit:,}",
            "entry_count": len(entries),
        }

    def format_for_system_prompt(self, target: str) -> Optional[str]:
        """
        返回系统提示用的快照。

        返回加载时的快照，而不是实时状态。会话中的写入不会影响这个。
        """
        block = self._system_prompt_snapshot.get(target, "")
        return block if block else None

    def _success_response(self, target: str, message: str = None) -> Dict[str, Any]:
        entries = self._entries_for(target)
        current = self._char_count(target)
        limit = self._char_limit(target)
        pct = min(100, int((current / limit) * 100) if limit > 0 else 0)

        resp = {
            "success": True,
            "target": target,
            "entries": entries,
            "usage": f"{pct}% — {current:,}/{limit:,}",
            "entry_count": len(entries),
        }
        if message:
            resp["message"] = message
        return resp

    def _render_block(self, target: str, entries: List[str]) -> str:
        """渲染系统提示块"""
        if not entries:
            return ""

        limit = self._char_limit(target)
        content = ENTRY_DELIMITER.join(entries)
        current = len(content)
        pct = min(100, int((current / limit) * 100) if limit > 0 else 0)

        if target == "user":
            header = f"USER PROFILE (who the user is) [{pct}% — {current:,}/{limit:,} chars]"
        else:
            header = f"MEMORY (your personal notes) [{pct}% — {current:,}/{limit:,} chars]"

        separator = "═" * 46
        return f"{separator}\n{header}\n{separator}\n{content}"

    @staticmethod
    def _read_file(path: Path) -> List[str]:
        """读取记忆文件并拆分为条目"""
        if not path.exists():
            return []
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, IOError):
            return []

        if not raw.strip():
            return []

        entries = [e.strip() for e in raw.split(ENTRY_DELIMITER)]
        return [e for e in entries if e]

    def _detect_external_drift(self, target: str) -> Optional[str]:
        """检测是否存在外部漂移，返回备份路径"""
        path = self._path_for(target)
        if not path.exists():
            return None
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, IOError):
            return None
        if not raw.strip():
            return None

        parsed = [e.strip() for e in raw.split(ENTRY_DELIMITER) if e.strip()]
        roundtrip = ENTRY_DELIMITER.join(parsed)

        char_limit = self._char_limit(target)
        max_entry_len = max((len(e) for e in parsed), default=0)

        drift_detected = (raw.strip() != roundtrip) or (max_entry_len > char_limit)
        if not drift_detected:
            return None

        # 备份文件
        import time
        ts = int(time.time())
        bak_path = path.with_suffix(path.suffix + f".bak.{ts}")
        try:
            bak_path.write_text(raw, encoding="utf-8")
        except (OSError, IOError):
            return str(bak_path) + " (BACKUP FAILED — file unchanged on disk)"
        return str(bak_path)

    @staticmethod
    def _write_file(path: Path, entries: List[str]):
        """原子化写入条目到文件"""
        content = ENTRY_DELIMITER.join(entries) if entries else ""
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(path.parent), suffix=".tmp", prefix=".mem_"
            )
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                atomic_replace(Path(tmp_path), path)
            except BaseException:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
                raise
        except (OSError, IOError) as e:
            raise RuntimeError(f"Failed to write memory file {path}: {e}")


def _drift_error(path: Path, bak_path: str) -> Dict[str, Any]:
    """构建外部漂移错误响应"""
    return {
        "success": False,
        "error": (
            f"Refusing to write {path.name}: file on disk has content that "
            f"wouldn't round-trip through the memory tool (likely added by "
            f"the patch tool, a shell append, a manual edit, or a "
            f"concurrent session). A snapshot was saved to {bak_path}. "
            f"Resolve the drift first — either rewrite the file as a clean "
            f"§-delimited list of entries, or move the extra content out — "
            f"then retry. This guard exists to prevent silent data loss."
        ),
        "drift_backup": bak_path,
        "remediation": (
            "Open the .bak file, integrate the missing entries into the "
            "memory tool one at a time via memory(action=add, content=...), "
            "then remove or rewrite the original file to a clean state."
        ),
    }


def memory_tool(
    action: str,
    target: str = "memory",
    content: str = None,
    old_text: str = None,
    store: Optional[MemoryStore] = None,
) -> str:
    """
    记忆工具入口函数。

    Args:
        action: 操作类型 - add, replace, remove, read
        target: 目标记忆 - memory 或 user
        content: 内容，用于 add 和 replace
        old_text: 旧文本，用于 replace 和 remove
        store: MemoryStore 实例

    Returns:
        JSON 格式的结果字符串
    """
    if store is None:
        # 创建默认的 MemoryStore
        store = MemoryStore()
        store.load_from_disk()

    if target not in {"memory", "user"}:
        return tool_error(f"Invalid target '{target}'. Use 'memory' or 'user'.", success=False)

    if action == "add":
        if not content:
            return tool_error("Content is required for 'add' action.", success=False)
        result = store.add(target, content)
    elif action == "replace":
        if not old_text:
            return tool_error("old_text is required for 'replace' action.", success=False)
        if not content:
            return tool_error("content is required for 'replace' action.", success=False)
        result = store.replace(target, old_text, content)
    elif action == "remove":
        if not old_text:
            return tool_error("old_text is required for 'remove' action.", success=False)
        result = store.remove(target, old_text)
    elif action == "read":
        result = store.read(target)
    else:
        return tool_error(f"Unknown action '{action}'. Use: add, replace, remove, read", success=False)

    return json.dumps(result, ensure_ascii=False)


def check_memory_requirements() -> bool:
    """记忆工具无外部依赖，始终可用"""
    return True


# 工具定义
MEMORY_SCHEMA = {
    "name": "memory",
    "description": (
        "Save durable information to persistent memory that survives across sessions. "
        "Memory is injected into future turns, so keep it compact and focused on facts "
        "that will still matter later.\n\n"
        "WHEN TO SAVE (do this proactively, don't wait to be asked):\n"
        "- User corrects you or says 'remember this' / 'don't do that again'\n"
        "- User shares a preference, habit, or personal detail (name, role, timezone, coding style)\n"
        "- You discover something about the environment (OS, installed tools, project structure)\n"
        "- You learn a convention, API quirk, or workflow specific to this user's setup\n"
        "- You identify a stable fact that will be useful again in future sessions\n\n"
        "PRIORITY: User preferences and corrections > environment facts > procedural knowledge. "
        "The most valuable memory prevents the user from having to repeat themselves.\n\n"
        "Do NOT save task progress, session outcomes, completed-work logs, or temporary TODO "
        "state to memory; use session_search to recall those from past transcripts.\n\n"
        "TWO TARGETS:\n"
        "- 'user': who the user is — name, role, preferences, communication style, pet peeves\n"
        "- 'memory': your notes — environment facts, project conventions, tool quirks, lessons learned\n\n"
        "ACTIONS: add (new entry), replace (update existing — old_text identifies it), "
        "remove (delete — old_text identifies it), read (view current entries).\n\n"
        "SKIP: trivial/obvious info, things easily rediscovered, raw data dumps, and temporary task state."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "replace", "remove", "read"],
                "description": "The action to perform."
            },
            "target": {
                "type": "string",
                "enum": ["memory", "user"],
                "description": "Which memory store: 'memory' for personal notes, 'user' for user profile."
            },
            "content": {
                "type": "string",
                "description": "The entry content. Required for 'add' and 'replace'."
            },
            "old_text": {
                "type": "string",
                "description": "Short unique substring identifying the entry to replace or remove."
            },
        },
        "required": ["action", "target"],
    },
}


# 注册工具
registry.register(
    name="memory",
    toolset="memory",
    schema=MEMORY_SCHEMA,
    handler=lambda args, **kw: memory_tool(
        action=args.get("action", ""),
        target=args.get("target", "memory"),
        content=args.get("content"),
        old_text=args.get("old_text"),
        store=kw.get("store"),
    ),
    check_fn=check_memory_requirements,
    emoji="🧠",
)
