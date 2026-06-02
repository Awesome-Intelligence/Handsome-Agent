"""Markdown Memory Store - Markdown Format Memory Storage

Based on Hermes Agent's memory storage method, saves memories as editable Markdown files.

Features:
1. Multi-layer memory classification storage
2. Automatic creation and management of Markdown files
3. Support for memory CRUD operations
4. Memory organization and cleanup mechanism
"""

import json
import os
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from abc import ABC, abstractmethod

from common.logging_manager import get_decision_logger


@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    content: str
    category: str = "general"  # general, user_profile, facts, skills, sessions
    importance: float = 0.5  # 0.0 - 1.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


class MarkdownMemoryStore:
    """
    Markdown 格式记忆存储

    将记忆存储为可编辑的 Markdown 文件，分类管理：
    - user_profile.md - 用户配置
    - facts.md - 事实记忆
    - skills.md - 技能记忆
    - sessions/ - 会话历史目录
    """

    def __init__(self, base_path: Optional[str] = None):
        """
        Args:
            base_path: 记忆存储的基础路径，默认 ~/.handsome_agent/memories
        """
        if base_path is None:
            home = os.path.expanduser("~")
            base_path = os.path.join(home, ".handsome_agent", "memories")

        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # 子目录
        self.sessions_path = self.base_path / "sessions"
        self.sessions_path.mkdir(exist_ok=True)

        # 记忆文件
        self.files = {
            'user_profile': self.base_path / "user_profile.md",
            'facts': self.base_path / "facts.md",
            'skills': self.base_path / "skills.md",
            'general': self.base_path / "general.md",
        }

        # Initialize files (if not exist)
        for file_path in self.files.values():
            if not file_path.exists():
                self._create_empty_file(file_path)

        self.logger = get_decision_logger(self.__class__.__name__)

    def _create_empty_file(self, file_path: Path):
        """Create empty Markdown file"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"# {file_path.stem.replace('_', ' ').title()}\n\n")
            f.write(f"_最后更新: {time.strftime('%Y-%m-%d %H:%M:%S')}_\n\n")
            f.write("<!-- 此文件由 Handsome Agent 自动管理，可手动编辑 -->\n\n")

    def _parse_memory_file(self, file_path: Path) -> List[MemoryEntry]:
        """解析 Markdown 记忆文件"""
        entries = []

        if not file_path.exists():
            return entries

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 简单的 Markdown 解析
            # 格式: ## [标题] ([timestamp])
            # 内容...
            current_entry = None
            current_content = []

            for line in content.split('\n'):
                if line.startswith('## '):
                    # 保存前一个条目
                    if current_entry:
                        entries.append(MemoryEntry(
                            id=current_entry['id'],
                            content='\n'.join(current_content).strip(),
                            category=file_path.stem,
                            timestamp=current_entry['timestamp'],
                            importance=current_entry.get('importance', 0.5)
                        ))

                    # 解析新条目
                    header = line[3:].strip()
                    # 提取标题和时间戳
                    if '(' in header and header.endswith(')'):
                        title = header.rsplit('(', 1)[0].strip()
                        timestamp_str = header.rsplit('(', 1)[1][:-1]
                        try:
                            timestamp = time.mktime(
                                time.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                            )
                        except ValueError:
                            timestamp = time.time()
                    else:
                        title = header
                        timestamp = time.time()

                    current_entry = {
                        'id': f"{file_path.stem}_{len(entries)}",
                        'timestamp': timestamp,
                        'importance': 0.5
                    }
                    current_content = [title]

                elif current_entry is not None:
                    current_content.append(line)

            # 保存最后一个条目
            if current_entry:
                entries.append(MemoryEntry(
                    id=current_entry['id'],
                    content='\n'.join(current_content).strip(),
                    category=file_path.stem,
                    timestamp=current_entry['timestamp'],
                    importance=current_entry.get('importance', 0.5)
                ))

        except Exception as e:
            self.logger.error(f"Failed to parse {file_path}: {e}")

        # 尝试从内容中解析 ID（如果有）
        for entry in entries:
            content = entry.content
            if '[ID:' in content:
                try:
                    id_start = content.index('[ID:') + 4
                    id_end = content.index(']', id_start)
                    entry.id = content[id_start:id_end]
                    # 从内容中移除 ID 标记
                    entry.content = content[:content.index('[ID:')].strip()
                except (ValueError, IndexError):
                    pass

        return entries

    def _write_memory_file(self, file_path: Path, entries: List[MemoryEntry]):
        """写入 Markdown 记忆文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# {file_path.stem.replace('_', ' ').title()}\n\n")
                f.write(f"_最后更新: {time.strftime('%Y-%m-%d %H:%M:%S')}_\n\n")
                f.write("<!-- 此文件由 Handsome Agent 自动管理，可手动编辑 -->\n\n")

                for entry in entries:
                    timestamp_str = time.strftime('%Y-%m-%d %H:%M:%S',
                                                   time.localtime(entry.timestamp))
                    # 保留原始 ID 用于追踪
                    header = f"## {entry.content.split(chr(10))[0][:50]} ({timestamp_str})"
                    if hasattr(entry, 'id') and entry.id:
                        header += f" [ID:{entry.id}]"
                    f.write(header + "\n\n")
                    f.write(entry.content)
                    f.write("\n\n")

        except Exception as e:
            self.logger.error(f"Failed to write {file_path}: {e}")

    def store(self, entry: MemoryEntry) -> bool:
        """
        存储记忆

        Args:
            entry: 记忆条目

        Returns:
            是否成功
        """
        category = entry.category if entry.category in self.files else 'general'
        file_path = self.files[category]

        # 读取现有条目
        entries = self._parse_memory_file(file_path)

        # 添加新条目
        entry.id = f"{category}_{int(time.time() * 1000)}"
        entries.append(entry)

        # 写入文件
        self._write_memory_file(file_path, entries)

        self.logger.info(f"Stored memory: {entry.id} in {category}")
        return True

    def retrieve(self, query: str, category: Optional[str] = None,
                 limit: int = 10) -> List[Tuple[MemoryEntry, float]]:
        """
        检索记忆

        Args:
            query: 查询关键词
            category: 可选，限定类别
            limit: 返回数量限制

        Returns:
            (记忆条目, 相关度分数) 列表
        """
        results = []
        query_lower = query.lower()

        # 确定搜索范围
        files_to_search = (
            {category: self.files[category]}
            if category and category in self.files
            else self.files
        )

        for cat, file_path in files_to_search.items():
            entries = self._parse_memory_file(file_path)

            for entry in entries:
                # 简单关键词匹配
                content_lower = entry.content.lower()
                if query_lower in content_lower:
                    # 计算相关度（简单基于出现次数和位置）
                    score = content_lower.count(query_lower)
                    results.append((entry, score))

        # 按相关度排序
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def get_all(self, category: Optional[str] = None) -> List[MemoryEntry]:
        """
        获取所有记忆

        Args:
            category: 可选，限定类别

        Returns:
            记忆条目列表
        """
        if category:
            if category in self.files:
                return self._parse_memory_file(self.files[category])
            return []

        all_entries = []
        for file_path in self.files.values():
            all_entries.extend(self._parse_memory_file(file_path))

        # 按时间排序（最新在前）
        all_entries.sort(key=lambda x: x.timestamp, reverse=True)
        return all_entries

    def update(self, memory_id: str, content: str) -> bool:
        """
        更新记忆

        Args:
            memory_id: 记忆 ID
            content: 新内容

        Returns:
            是否成功
        """
        # 找到记忆所在的文件
        for category, file_path in self.files.items():
            entries = self._parse_memory_file(file_path)

            for entry in entries:
                if entry.id == memory_id:
                    entry.content = content
                    entry.timestamp = time.time()
                    self._write_memory_file(file_path, entries)
                    self.logger.info(f"Updated memory: {memory_id}")
                    return True

        return False

    def delete(self, memory_id: str) -> bool:
        """
        删除记忆

        Args:
            memory_id: 记忆 ID

        Returns:
            是否成功
        """
        for category, file_path in self.files.items():
            entries = self._parse_memory_file(file_path)
            original_count = len(entries)

            entries = [e for e in entries if e.id != memory_id]

            if len(entries) < original_count:
                self._write_memory_file(file_path, entries)
                self.logger.info(f"Deleted memory: {memory_id}")
                return True

        return False

    def save_session(self, session_id: str, messages: List[Dict[str, Any]],
                     metadata: Optional[Dict[str, Any]] = None):
        """
        保存会话历史为 Markdown

        Args:
            session_id: 会话 ID
            messages: 消息列表
            metadata: 可选的会话元数据
        """
        session_file = self.sessions_path / f"{session_id}.md"

        try:
            with open(session_file, 'w', encoding='utf-8') as f:
                f.write(f"# Session: {session_id}\n\n")

                if metadata:
                    f.write("## Session Info\n\n")
                    for key, value in metadata.items():
                        f.write(f"- **{key}**: {value}\n")
                    f.write("\n")

                f.write("## Conversation\n\n")

                for msg in messages:
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')
                    timestamp = msg.get('timestamp')

                    if timestamp:
                        time_str = time.strftime('%Y-%m-%d %H:%M:%S',
                                                  time.localtime(timestamp))
                        f.write(f"### [{time_str}] {role.title()}\n\n")
                    else:
                        f.write(f"### {role.title()}\n\n")

                    f.write(f"{content}\n\n")

            self.logger.info(f"Saved session: {session_id}")

        except Exception as e:
            self.logger.error(f"Failed to save session {session_id}: {e}")

    def list_sessions(self) -> List[str]:
        """列出所有保存的会话"""
        sessions = []
        for file in self.sessions_path.glob("*.md"):
            sessions.append(file.stem)
        return sorted(sessions)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话内容"""
        session_file = self.sessions_path / f"{session_id}.md"

        if not session_file.exists():
            return None

        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                content = f.read()

            return {
                'session_id': session_id,
                'content': content,
                'file_path': str(session_file)
            }

        except Exception as e:
            self.logger.error(f"Failed to read session {session_id}: {e}")
            return None

    def cleanup_old_sessions(self, days: int = 30) -> int:
        """
        清理旧会话

        Args:
            days: 保留天数

        Returns:
            删除的会话数
        """
        deleted = 0
        cutoff_time = time.time() - (days * 24 * 3600)

        for session_file in self.sessions_path.glob("*.md"):
            if session_file.stat().st_mtime < cutoff_time:
                try:
                    session_file.unlink()
                    deleted += 1
                except Exception as e:
                    self.logger.error(f"Failed to delete {session_file}: {e}")

        if deleted > 0:
            self.logger.info(f"Cleaned up {deleted} old sessions")

        return deleted


class MemoryCurator:
    """
    记忆整理器

    自动整理和清理记忆：
    1. 合并相似的记忆
    2. 删除低重要性的记忆
    3. 提取关键信息
    """

    def __init__(self, store: MarkdownMemoryStore,
                 min_importance: float = 0.3,
                 max_entries_per_category: int = 100):
        """
        Args:
            store: 记忆存储
            min_importance: 最低重要性阈值
            max_entries_per_category: 每类最大条目数
        """
        self.store = store
        self.min_importance = min_importance
        self.max_entries_per_category = max_entries_per_category
        self.logger = get_decision_logger(self.__class__.__name__)

    def curate(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Execute memory organization

        Args:
            dry_run: 是否仅预览，不实际执行

        Returns:
            整理结果统计
        """
        stats = {
            'categories_curated': 0,
            'entries_removed': 0,
            'entries_merged': 0,
            'details': []
        }

        for category, file_path in self.store.files.items():
            entries = self.store._parse_memory_file(file_path)

            if not entries:
                continue

            original_count = len(entries)

            # 1. 移除低重要性条目
            important_entries = [
                e for e in entries
                if e.importance >= self.min_importance
            ]
            removed_low_importance = len(entries) - len(important_entries)

            # 2. 限制条目数量（保留最重要的）
            if len(important_entries) > self.max_entries_per_category:
                important_entries.sort(key=lambda x: x.importance, reverse=True)
                important_entries = important_entries[:self.max_entries_per_category]

            # 3. 简单的相似条目合并（基于前50个字符）
            merged = []
            seen_titles = set()

            for entry in important_entries:
                title = entry.content[:50].lower().strip()
                if title not in seen_titles:
                    merged.append(entry)
                    seen_titles.add(title)

            merged_count = len(important_entries) - len(merged)
            removed_total = original_count - len(merged)

            if not dry_run and removed_total > 0:
                self.store._write_memory_file(file_path, merged)

            stats['categories_curated'] += 1
            stats['entries_removed'] += removed_total
            stats['entries_merged'] += merged_count
            stats['details'].append({
                'category': category,
                'original': original_count,
                'after': len(merged),
                'removed': removed_total,
                'merged': merged_count
            })

        if stats['entries_removed'] > 0 or stats['entries_merged'] > 0:
            self.logger.info(
                f"Curated memories: {stats['entries_removed']} removed, "
                f"{stats['entries_merged']} merged"
            )

        return stats
