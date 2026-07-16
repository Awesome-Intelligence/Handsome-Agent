#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Store Module - 持久化记忆存储

提供跨会话保存的 Agent 记忆管理功能：
- 记忆条目管理 (add/replace/remove/read)
- 磁盘持久化 (MEMORY.md, USER.md)
- 安全扫描 (注入检测)
- 原子化写入

架构说明：
- MemoryStore: 核心存储类，负责记忆条目管理和磁盘持久化
- BuiltinMemoryProvider: 使用 MemoryStore 的 Provider 实现

职责边界（与 Session 的区分）：
┌─────────────────────────────────────────────────────────────────────┐
│                         用户可见记忆                                   │
├─────────────────────────────────────────────────────────────────────┤
│  MemoryStore (本模块)                                                 │
│  - 用途: 用户显式添加/管理的长期记忆                                   │
│  - 存储: ~/.agent_z/memories/MEMORY.md                       │
│  - 管理: 通过 memory_tool (add/replace/remove)                        │
│  - 特点: 跨会话持久，用户完全控制                                      │
├─────────────────────────────────────────────────────────────────────┤
│  Session (agent/session.py)                                          │
│  - 用途: 自动生成的会话摘要，用于跨会话上下文                          │
│  - 存储: ~/.agent_z/sessions/daily_summary.md                │
│  - 管理: sync_to_daily_summary() 自动生成                            │
│  - 特点: 自动摘要，Agent 可读取但不直接修改                            │
└─────────────────────────────────────────────────────────────────────┘

基于 Hermes Agent 的 memory_tool.py 实现。

日志子层：💾 Memory
"""

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Callable

from common.logging_manager import get_execution_logger
from common.config import MemoryConfig
from agent.memory.file_lock import file_lock

logger = get_execution_logger("MemoryStore")

# 记忆目录路径
def get_memory_dir() -> Path:
    """获取记忆存储目录"""
    base_dir = Path.home() / ".agent_z"
    memory_dir = base_dir / "memories"
    memory_dir.mkdir(parents=True, exist_ok=True)
    return memory_dir

ENTRY_DELIMITER = "\n§\n"

# 威胁检测模式 - 预编译正则表达式以提升性能
# 格式: (编译后的Pattern对象, 威胁ID)
_MEMORY_THREAT_PATTERNS: List[tuple[re.Pattern, str]] = [
    (re.compile(r'ignore\s+(previous|all|above|prior)\s+instructions', re.IGNORECASE), 'prompt_injection'),
    (re.compile(r'you\s+are\s+now\s+', re.IGNORECASE), 'role_hijack'),
    (re.compile(r'do\s+not\s+tell\s+the\s+user', re.IGNORECASE), 'deception_hide'),
    (re.compile(r'system\s+prompt\s+override', re.IGNORECASE), 'sys_prompt_override'),
    (re.compile(r'disregard\s+(your|all|any)\s+(instructions|rules|guidelines)', re.IGNORECASE), 'disregard_rules'),
    (re.compile(r'act\s+as\s+(if|though)\s+you\s+(have\s+no|don\'t\s+have)\s+(restrictions|limits|rules)', re.IGNORECASE), 'bypass_restrictions'),
    (re.compile(r'curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)', re.IGNORECASE), 'exfil_curl'),
    (re.compile(r'wget\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)', re.IGNORECASE), 'exfil_wget'),
    (re.compile(r'cat\s+[^\n]*(\.env|credentials|\.netrc|\.pgpass|\.npmrc|\.pypirc)', re.IGNORECASE), 'read_secrets'),
    (re.compile(r'authorized_keys', re.IGNORECASE), 'ssh_backdoor'),
    (re.compile(r'\$HOME/\.ssh|\~/\.ssh', re.IGNORECASE), 'ssh_access'),
    (re.compile(r'\$HOME/\.agent_z/\.env|\~/\.agent_z/\.env', re.IGNORECASE), 'agentz_env'),
]

# 不可见字符检测
_INVISIBLE_CHARS = {
    '\u200b', '\u200c', '\u200d', '\u2060', '\ufeff',
    '\u202a', '\u202b', '\u202c', '\u202d', '\u202e',
}


# ============================================================================
# 矛盾检测模式 (参考 Hermes Holographic 插件)
# ============================================================================

# 相反概念对（用于检测可能矛盾的记忆条目）
# 格式: (primary, opposite1, opposite2, ...)
# primary 和 any opposite 同时出现在两个条目中时认为是可能的矛盾
_CONTRADICTION_PAIRS = [
    # 频率/习惯
    ("always", "never"),
    ("usually", "rarely", "seldom"),
    ("often", "rarely", "seldom", "never"),
    ("sometimes", "never", "rarely"),
    # 偏好
    ("prefer", "avoid", "dislike"),
    ("prefers", "avoids", "dislikes"),
    ("like", "dislike", "hate"),
    ("likes", "dislikes", "hates"),
    ("love", "hate"),
    ("loves", "hates"),
    # 使用
    ("use", "don't use", "do not use", "never use", "avoid"),
    ("uses", "doesn't use", "does not use", "never uses", "avoids"),
    ("using", "not using", "avoiding"),
    # 能力
    ("can", "can't", "cannot", "unable"),
    ("could", "couldn't", "cannot"),
    ("will", "won't", "will not", "refuse"),
    ("would", "wouldn't", "would not"),
    # 必要性
    ("need", "don't need", "do not need"),
    ("needs", "doesn't need", "does not need"),
    ("must", "mustn't", "must not"),
    ("should", "shouldn't", "should not"),
    # 意愿
    ("want", "don't want", "do not want"),
    ("wants", "doesn't want", "does not want"),
    # 状态
    ("is", "isn't", "is not"),
    ("am", "am not"),
    ("are", "aren't", "are not"),
    ("have", "don't have", "do not have"),
    ("has", "doesn't have", "does not have"),
    # 行为
    ("do", "don't", "do not"),
    ("does", "doesn't", "does not"),
    ("did", "didn't", "did not"),
]

# 矛盾检测阈值配置
_CONTRADICTION_CONFIG = {
    "min_overlap": 0.3,  # 最小实体重叠度（Jaccard）
    "min_length": 20,   # 最小条目长度
    "max_pairs": 10,     # 最大返回的矛盾对数量
    "threshold": 0.4,    # 矛盾分数阈值
}


def _extract_entities(text: str) -> set:
    """
    从文本中提取实体/关键词。

    参考 Hermes Holographic 的实体提取逻辑：
    - 转换为小写
    - 提取长度>=3的单词
    - 移除停用词

    Args:
        text: 输入文本

    Returns:
        提取的实体集合
    """
    # 停用词列表
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "were",
        "been", "be", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "must", "shall",
        "i", "you", "he", "she", "it", "we", "they", "my", "your",
        "this", "that", "these", "those", "here", "there", "when", "where",
        "why", "how", "what", "which", "who", "whom", "whose",
    }

    # 简单分词：按空白字符和标点分割
    import re
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())

    # 过滤停用词和短词
    entities = {w for w in words if w not in stop_words and len(w) >= 3}
    return entities


def _has_contradiction_keywords(entry1: str, entry2: str) -> tuple[bool, list]:
    """
    检查两个条目是否包含矛盾关键词。

    如果两个条目都包含同一"相反概念对"中的词，则可能是矛盾的。

    Args:
        entry1: 第一个条目
        entry2: 第二个条目

    Returns:
        (是否有矛盾关键词, 涉及的相反对列表)
    """
    entry1_lower = entry1.lower()
    entry2_lower = entry2.lower()

    contradictions = []
    for pair in _CONTRADICTION_PAIRS:
        # pair 中第一个词和其他词的含义相反
        primary = pair[0]
        opposites = pair[1:]

        # 检查 entry1 是否包含 primary，entry2 是否包含 opposite
        entry1_has_primary = primary in entry1_lower
        entry2_has_opposite = any(opp in entry2_lower for opp in opposites)

        # 或者反过来
        entry2_has_primary = primary in entry2_lower
        entry1_has_opposite = any(opp in entry1_lower for opp in opposites)

        if (entry1_has_primary and entry2_has_opposite) or \
           (entry2_has_primary and entry1_has_opposite):
            contradictions.append(pair)

    return len(contradictions) > 0, contradictions


def _jaccard_similarity(set_a: set, set_b: set) -> float:
    """
    计算两个集合的 Jaccard 相似度。

    Args:
        set_a: 集合 A
        set_b: 集合 B

    Returns:
        Jaccard 相似度 (0.0 - 1.0)
    """
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def _calculate_contradiction_score(entry1: str, entry2: str) -> float:
    """
    计算两个条目的矛盾分数。

    参考 Hermes Holographic 的矛盾检测算法：
    - 实体重叠度（Jaccard）
    - 矛盾关键词存在性
    - 内容相似度（简化为基于实体重叠）

    Args:
        entry1: 第一个条目
        entry2: 第二个条目

    Returns:
        矛盾分数 (0.0 - 1.0)
    """
    entities1 = _extract_entities(entry1)
    entities2 = _extract_entities(entry2)

    # 计算实体重叠度
    overlap = _jaccard_similarity(entities1, entities2)

    # 检查矛盾关键词
    has_contradiction, contradiction_pairs = _has_contradiction_keywords(entry1, entry2)

    # 矛盾分数计算策略：
    # 1. 有矛盾关键词时：基础分 = 重叠度 + 关键词加分（关键词越多加分越高）
    # 2. 无矛盾关键词时：仅依赖重叠度
    # 3. 如果有矛盾关键词但重叠度太低，可以降低阈值考虑（min_overlap_ignored = 0.1）

    contradiction_boost = 0.0
    if has_contradiction:
        # 每个矛盾对提供额外加分
        contradiction_boost = min(0.4, len(contradiction_pairs) * 0.2)
        # 如果重叠度太低但有矛盾关键词，给一个最小基础分
        if overlap < 0.15:
            overlap = 0.15

    # 矛盾分数 = 重叠度 + 矛盾关键词加分
    score = min(1.0, overlap + contradiction_boost)

    return score


def _scan_memory_content(content: str) -> Optional[str]:
    """扫描记忆内容是否存在威胁模式"""
    # 检测不可见字符
    for char in _INVISIBLE_CHARS:
        if char in content:
            return f"Blocked: content contains invisible unicode character U+{ord(char):04X} (possible injection)."

    # 检测威胁模式 - 使用预编译的正则表达式
    for compiled_pattern, threat_id in _MEMORY_THREAT_PATTERNS:
        if compiled_pattern.search(content):
            return f"Blocked: content matches threat pattern '{threat_id}'. Memory entries are injected into the system prompt and must not contain injection or exfiltration payloads."

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
    纯存储类：持久化记忆存储，支持跨会话保存。

    仅负责存储层逻辑：
    - 记忆条目管理 (add/replace/remove/read)
    - 磁盘持久化
    - 快照功能（用于 BuiltinMemoryProvider 的冻结提示）
    - max_entries 限制支持

    支持两种初始化方式：
    1. 直接指定参数：MemoryStore(memory_char_limit=2200, user_char_limit=1375, max_entries=1000)
    2. 通过 MemoryConfig：MemoryStore.from_config(config)

    注意：系统提示构建由 BuiltinMemoryProvider.system_prompt_block() 负责。
    """

    def __init__(
        self,
        memory_char_limit: int = 2200,
        user_char_limit: int = 1375,
        max_entries: int = 1000,
    ):
        """
        初始化 MemoryStore。

        Args:
            memory_char_limit: Agent 记忆（MEMORY.md）的字符限制
            user_char_limit: 用户画像（USER.md）的字符限制
            max_entries: 最大条目数限制（0 表示不限制）
        """
        self.memory_entries: List[str] = []
        self.user_entries: List[str] = []

        # 字符限制
        self.memory_char_limit = memory_char_limit
        self.user_char_limit = user_char_limit

        # 条目数限制
        self.max_entries = max_entries  # 0 表示不限制

        # 快照相关（与 Hermes 一致的设计）
        # 在 load_from_disk() 时初始化，freeze_snapshot() 更新
        # 用于系统提示注入，保持会话期间稳定
        self._system_prompt_snapshot: Dict[str, str] = {"memory": "", "user": ""}

        # 观察者模式：用于通知外部缓存失效
        # 当记忆内容改变时，会通知所有注册的观察者
        self._observers: List[Callable[[str, str, str], None]] = []

    def add_observer(self, callback: Callable[[str, str, str], None]) -> None:
        """
        注册观察者回调。

        当记忆内容改变时，所有注册的观察者都会被通知。
        回调签名: callback(action: str, target: str, content: str)
            - action: 'add', 'replace', 'remove'
            - target: 'memory' 或 'user'
            - content: 变化的条目内容（remove时是被删除的内容）

        Args:
            callback: 观察者回调函数
        """
        if callback not in self._observers:
            self._observers.append(callback)
            logger.debug(f"Observer registered: {callback.__name__ if hasattr(callback, '__name__') else callback}")

    def remove_observer(self, callback: Callable[[str, str, str], None]) -> None:
        """
        移除观察者回调。

        Args:
            callback: 要移除的观察者回调
        """
        if callback in self._observers:
            self._observers.remove(callback)
            logger.debug(f"Observer removed: {callback.__name__ if hasattr(callback, '__name__') else callback}")

    def _notify_observers(self, action: str, target: str, content: str) -> None:
        """
        通知所有观察者记忆内容已改变。

        Args:
            action: 操作类型 ('add', 'replace', 'remove')
            target: 目标类型 ('memory' 或 'user')
            content: 变化的条目内容
        """
        if not self._observers:
            return

        for observer in self._observers:
            try:
                observer(action, target, content)
            except Exception as e:
                logger.warning(f"Observer callback failed: {e}")

    @classmethod
    def from_config(cls, config: MemoryConfig) -> "MemoryStore":
        """
        从 MemoryConfig 创建 MemoryStore 实例。

        Args:
            config: MemoryConfig 配置对象

        Returns:
            MemoryStore 实例
        """
        return cls(
            memory_char_limit=config.memory_char_limit,
            user_char_limit=config.user_char_limit,
            max_entries=config.max_entries,
        )

    def update_config(self, config: MemoryConfig) -> None:
        """
        使用 MemoryConfig 更新配置。

        Args:
            config: MemoryConfig 配置对象
        """
        self.memory_char_limit = config.memory_char_limit
        self.user_char_limit = config.user_char_limit
        self.max_entries = config.max_entries

    def _check_entry_limit(self, target: str) -> Optional[str]:
        """
        检查是否达到条目数限制。

        Args:
            target: 'memory' 或 'user'

        Returns:
            如果超过限制返回错误信息，否则返回 None
        """
        if self.max_entries <= 0:
            return None  # 0 表示不限制

        entries = self._entries_for(target)
        if len(entries) >= self.max_entries:
            return (
                f"Entry limit reached: {len(entries)}/{self.max_entries} entries. "
                f"Remove existing entries before adding new ones."
            )
        return None

    def get_stats(self) -> Dict[str, Any]:
        """
        获取记忆存储统计信息。

        Returns:
            统计信息字典
        """
        return {
            "memory_entries": len(self.memory_entries),
            "user_entries": len(self.user_entries),
            "memory_char_count": self._char_count("memory"),
            "user_char_count": self._char_count("user"),
            "memory_char_limit": self.memory_char_limit,
            "user_char_limit": self.user_char_limit,
            "max_entries": self.max_entries,
        }

    def detect_contradictions(
        self,
        target: str = "all",
        threshold: float = None,
        limit: int = None,
    ) -> List[Dict[str, Any]]:
        """
        检测记忆中的可能矛盾条目。

        参考 Hermes Holographic 的 contradict 方法实现。

        算法说明：
        1. 获取所有记忆条目（支持 target 过滤）
        2. 两两比较条目对，计算矛盾分数
        3. 矛盾分数 = 实体重叠度(Jaccard) + 矛盾关键词加分
        4. 返回分数 >= threshold 的矛盾对

        Args:
            target: 检测目标 ('memory', 'user', 'all')
            threshold: 矛盾分数阈值（默认从配置读取）
            limit: 最大返回数量（默认从配置读取）

        Returns:
            矛盾对列表，每项包含:
            - entry_a: 第一个条目
            - entry_b: 第二个条目
            - entity_overlap: 实体重叠度
            - has_contradiction_keywords: 是否包含矛盾关键词
            - contradiction_keywords: 涉及的矛盾关键词对
            - score: 矛盾分数

        示例:
            store.detect_contradictions()
            # 返回: [{"entry_a": "User prefers Python", "entry_b": "User never uses Python", ...}]
        """
        config = _CONTRADICTION_CONFIG
        threshold = threshold or config["threshold"]
        limit = limit or config["max_pairs"]
        min_overlap = config["min_overlap"]
        min_length = config["min_length"]

        # 获取要检测的条目
        if target == "memory":
            entries = list(self.memory_entries)
        elif target == "user":
            entries = list(self.user_entries)
        else:  # "all"
            entries = list(self.memory_entries) + list(self.user_entries)

        # 过滤过短的条目
        entries = [e for e in entries if len(e) >= min_length]

        if len(entries) < 2:
            return []

        # 限制比较数量，避免 O(n²) 爆炸
        max_entries = 500
        if len(entries) > max_entries:
            logger.warning(
                f"Too many entries ({len(entries)}), checking only the latest {max_entries}"
            )
            entries = entries[-max_entries:]

        contradictions = []

        # 两两比较
        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                entry_a = entries[i]
                entry_b = entries[j]

                # 检查矛盾关键词
                has_contradiction, keywords = _has_contradiction_keywords(entry_a, entry_b)

                # 如果没有矛盾关键词且重叠度太低，跳过
                # 但如果有关键词，可以放宽重叠度限制
                if not has_contradiction:
                    entities_a = _extract_entities(entry_a)
                    entities_b = _extract_entities(entry_b)
                    entity_overlap = _jaccard_similarity(entities_a, entities_b)
                    if entity_overlap < min_overlap:
                        continue
                else:
                    # 有关键词时，使用更低的重叠度阈值
                    entities_a = _extract_entities(entry_a)
                    entities_b = _extract_entities(entry_b)
                    entity_overlap = _jaccard_similarity(entities_a, entities_b)

                # 计算矛盾分数
                score = _calculate_contradiction_score(entry_a, entry_b)

                # 检查阈值
                if score >= threshold:
                    contradictions.append({
                        "entry_a": entry_a,
                        "entry_b": entry_b,
                        "entity_overlap": round(entity_overlap, 3),
                        "has_contradiction_keywords": has_contradiction,
                        "contradiction_keywords": [list(k) for k in keywords] if keywords else [],
                        "score": round(score, 3),
                    })

        # 按分数排序，限制返回数量
        contradictions.sort(key=lambda x: x["score"], reverse=True)
        return contradictions[:limit]

    # ============================================================================
    # Snapshot / System Prompt (与 Hermes 一致的设计)
    # ============================================================================

    def _render_block(self, target: str) -> str:
        """
        渲染单个记忆块为系统提示格式（Hermes 风格）。

        Args:
            target: 'memory' 或 'user'

        Returns:
            格式化的块文本
        """
        entries = self._entries_for(target)
        if not entries:
            return ""

        limit = self._char_limit(target)
        content = ENTRY_DELIMITER.join(entries)
        current = len(content)
        pct = min(100, int((current / limit) * 100)) if limit > 0 else 0

        if target == "user":
            header = f"USER PROFILE (who the user is) [{pct}% — {current:,}/{limit:,} chars]"
        else:
            header = f"MEMORY (your personal notes) [{pct}% — {current:,}/{limit:,} chars]"

        separator = "═" * 46
        return f"{separator}\n{header}\n{separator}\n{content}"

    def freeze_snapshot(self) -> str:
        """
        冻结当前状态的快照（与 Hermes 一致）。

        调用此方法后，系统提示快照会被更新为当前记忆内容。
        用于 BuiltinMemoryProvider 在会话开始时冻结系统提示。

        Returns:
            合并的冻结快照文本
        """
        # 更新内部快照缓存
        self._system_prompt_snapshot = {
            "memory": self._render_block("memory"),
            "user": self._render_block("user"),
        }
        return self.get_snapshot()

    def get_snapshot(self) -> str:
        """
        获取冻结的系统提示快照（与 Hermes format_for_system_prompt 等价）。

        Returns:
            合并的快照文本（USER + MEMORY）
        """
        blocks = []
        user_block = self._system_prompt_snapshot.get("user", "")
        memory_block = self._system_prompt_snapshot.get("memory", "")

        if user_block:
            blocks.append(user_block)
        if memory_block:
            blocks.append(memory_block)

        return "\n\n".join(blocks)

    def format_for_system_prompt(self, target: str) -> Optional[str]:
        """
        返回指定目标（memory/user）的冻结快照（Hermes 风格）。

        用于 BuiltinMemoryProvider.system_prompt_block() 获取格式化后的记忆块。

        Args:
            target: 'memory' 或 'user'

        Returns:
            格式化后的块文本，如果为空返回 None
        """
        block = self._system_prompt_snapshot.get(target, "")
        return block if block else None

    def load_from_disk(self):
        """
        从磁盘加载记忆条目并初始化系统提示快照。

        与 Hermes 一致的设计：在加载时设置冻结快照。
        """
        mem_dir = get_memory_dir()
        mem_dir.mkdir(parents=True, exist_ok=True)

        self.memory_entries = self._read_file(mem_dir / "MEMORY.md")
        self.user_entries = self._read_file(mem_dir / "USER.md")

        # 去重
        self.memory_entries = list(dict.fromkeys(self.memory_entries))
        self.user_entries = list(dict.fromkeys(self.user_entries))

        # 初始化系统提示快照（与 Hermes 一致）
        self._system_prompt_snapshot = {
            "memory": self._render_block("memory"),
            "user": self._render_block("user"),
        }

    @staticmethod
    def _path_for(target: str) -> Path:
        mem_dir = get_memory_dir()
        if target == "user":
            return mem_dir / "USER.md"
        return mem_dir / "MEMORY.md"

    def _reload_target(self, target: str, force: bool = False) -> Optional[str]:
        """
        重新从磁盘加载目标。

        Args:
            target: 目标类型 ('memory' 或 'user')
            force: 是否强制重新加载（即使没有外部漂移）

        Returns:
            备份路径（如果检测到外部漂移）
        """
        bak = self._detect_external_drift(target)

        # 只有在检测到外部漂移或强制重新加载时才覆盖内存
        if bak or force:
            path = self._path_for(target)
            fresh = self._read_file(path)
            fresh = list(dict.fromkeys(fresh))  # 去重
            self._set_entries(target, fresh)

        return bak

    def save_to_disk(self, target: str):
        """保存条目到对应文件"""
        get_memory_dir().mkdir(parents=True, exist_ok=True)
        self._write_file(self._path_for(target), self._entries_for(target))

    def flush_to_disk(self) -> None:
        """批量写入所有待定修改到磁盘"""
        get_memory_dir().mkdir(parents=True, exist_ok=True)

        with file_lock(get_memory_dir() / "MEMORY.md"):
            self._write_file(get_memory_dir() / "MEMORY.md", self.memory_entries)
        with file_lock(get_memory_dir() / "USER.md"):
            self._write_file(get_memory_dir() / "USER.md", self.user_entries)

    def _entries_for(self, target: str) -> List[str]:
        """获取条目列表（返回副本以防止意外修改）"""
        if target == "user":
            return list(self.user_entries)
        return list(self.memory_entries)

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
        """添加新条目，返回错误如果超出字符限制或条目数限制"""
        content = content.strip()
        if not content:
            return {"success": False, "error": "Content cannot be empty."}

        # 扫描威胁
        scan_error = _scan_memory_content(content)
        if scan_error:
            return {"success": False, "error": scan_error}

        with file_lock(self._path_for(target)):
            # 重新从磁盘加载以获取其他会话的写入
            bak = self._reload_target(target)
            if bak:
                return _drift_error(self._path_for(target), bak)

            # 获取当前条目列表
            entries = self._entries_for(target)
            limit = self._char_limit(target)

            # 检查是否已存在
            if content in entries:
                return self._success_response(target, "Entry already exists (no duplicate added).")

            # 检查条目数限制
            entry_limit_error = self._check_entry_limit(target)
            if entry_limit_error:
                return {
                    "success": False,
                    "error": entry_limit_error,
                    "entry_count": len(entries),
                    "max_entries": self.max_entries,
                }

            # 计算新的总大小
            new_entries = list(entries) + [content]
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

            # 添加到副本并同步回原列表
            entries.append(content)
            self._set_entries(target, entries)

        # 通知观察者（无论是否写磁盘，只要内容改变了就通知）
        self._notify_observers("add", target, content)

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

        with file_lock(self._path_for(target)):
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
            self._set_entries(target, entries)  # 同步副本回原列表

        # 通知观察者
        self._notify_observers("replace", target, new_content)

        return self._success_response(target, "Entry replaced.")

    def remove(self, target: str, old_text: str) -> Dict[str, Any]:
        """移除包含 old_text 的条目"""
        old_text = old_text.strip()
        if not old_text:
            return {"success": False, "error": "old_text cannot be empty."}

        with file_lock(self._path_for(target)):
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
            removed_content = entries[idx]  # 保存被删除的内容用于通知
            entries.pop(idx)
            self._set_entries(target, entries)  # 同步副本回原列表

        # 通知观察者（在锁外执行）
        self._notify_observers("remove", target, removed_content)

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
            "max_entries": self.max_entries if self.max_entries > 0 else None,  # None 表示无限制
        }

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
            "max_entries": self.max_entries if self.max_entries > 0 else None,  # None 表示无限制
        }
        if message:
            resp["message"] = message
        return resp

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


def tool_error(message: str, success: bool = False) -> str:
    """Simple tool error response function"""
    return json.dumps({
        "success": success,
        "error": message
    }, ensure_ascii=False)


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
        "AUTO-SUMMARY: The MemoryCurator automatically summarizes user preferences and environment "
        "information at session end. Explicit saves are still valuable for:\n"
        "- User corrections and explicit 'remember this' requests\n"
        "- Real-time learning during complex tasks\n"
        "- Facts discovered mid-session that should persist immediately\n\n"
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


def check_memory_requirements() -> bool:
    """记忆工具无外部依赖，始终可用"""
    return True


__all__ = [
    'MemoryStore',
    'memory_tool',
    'tool_error',
    'MEMORY_SCHEMA',
    'check_memory_requirements',
    'get_memory_dir',
]
