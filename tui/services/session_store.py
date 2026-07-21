#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session Store Service - SQLite Database for Session Persistence

🚪 Access - 💬 CLI - TUI Services - SessionStore

基于 SQLite 的会话持久化服务，提供：
- 会话创建、读取、更新、删除（CRUD）
- 消息历史存储
- 自动保存和批量写入优化
- 数据库迁移支持
"""

from __future__ import annotations

import gc
import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Generator, Iterator, Optional

# 日志支持
try:
    from common.logging_manager import get_access_logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    def get_access_logger(*args, **kwargs):
        return logging.getLogger("Agent")

# i18n 支持
try:
    from common.i18n import get_i18n, t
except ImportError:
    def get_i18n():
        class SimpleI18n:
            def t(self, key, default=None, **kwargs):
                return default or key
        return SimpleI18n()
    
    def t(key, default=None, **kwargs):
        return default or key


# ============================================================================
# 数据库 Schema
# ============================================================================

SCHEMA_VERSION = 2

INITIAL_SCHEMA = f"""
-- 会话表
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    model TEXT DEFAULT '',
    provider TEXT DEFAULT '',
    context_tokens INTEGER DEFAULT 0,
    message_count INTEGER DEFAULT 0
);

-- 消息表
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    tokens INTEGER,
    thinking_content TEXT,
    metadata TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- 输入历史表（跨会话持久化）
CREATE TABLE IF NOT EXISTS input_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_used_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    use_count INTEGER DEFAULT 1
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_input_history_created ON input_history(created_at DESC);
"""

# 数据库迁移脚本
MIGRATIONS: list[str] = [
    # v1: 初始版本
    "",
    # v2: 添加输入历史表
    """
    CREATE TABLE IF NOT EXISTS input_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_used_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        use_count INTEGER DEFAULT 1
    );
    
    CREATE INDEX IF NOT EXISTS idx_input_history_created ON input_history(created_at DESC);
    """,
]


# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class Session:
    """会话数据模型
    
    Attributes:
        id: 会话唯一标识
        title: 会话标题
        created_at: 创建时间
        updated_at: 更新时间
        model: 使用的模型名称
        provider: 模型提供商
        context_tokens: 上下文 token 数量
        message_count: 消息数量
    """
    id: str
    title: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model: str = ""
    provider: str = ""
    context_tokens: int = 0
    message_count: int = 0
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "model": self.model,
            "provider": self.provider,
            "context_tokens": self.context_tokens,
            "message_count": self.message_count,
        }


@dataclass
class Message:
    """消息数据模型
    
    Attributes:
        id: 消息唯一标识
        session_id: 所属会话 ID
        role: 消息角色 (user/assistant/system/tool)
        content: 消息内容
        created_at: 创建时间
        tokens: token 数量
        thinking_content: 思考过程（可选）
        metadata: 额外元数据（JSON 格式）
    """
    id: str
    session_id: str
    role: str
    content: str
    created_at: Optional[datetime] = None
    tokens: Optional[int] = None
    thinking_content: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "tokens": self.tokens,
            "thinking_content": self.thinking_content,
            "metadata": self.metadata,
        }


# ============================================================================
# SessionStore 类
# ============================================================================

class SessionStore:
    """会话存储服务
    
    基于 SQLite 的会话持久化服务，提供线程安全的数据库操作。
    
    Features:
    - 单例模式确保数据库连接复用
    - 连接池支持
    - 自动保存和批量写入
    - 数据库迁移支持
    
    Example:
        store = SessionStore()
        session_id = store.create_session("gpt-4", "OpenAI")
        store.save_message(session_id, "user", "Hello!")
        sessions = store.list_sessions()
    """
    
    _instance: Optional["SessionStore"] = None
    _lock = threading.Lock()
    
    def __new__(cls, db_path: Optional[Path] = None) -> "SessionStore":
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: Optional[Path] = None):
        """初始化会话存储
        
        Args:
            db_path: 数据库文件路径，默认使用用户数据目录
        """
        if self._initialized:
            return
        
        self._initialized = True
        self._logger = get_access_logger("SessionStore", sublayer="tui")
        self._i18n = get_i18n()
        
        # 数据库路径
        if db_path is None:
            db_path = self._get_default_db_path()
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 连接池（每个线程独立的连接）
        self._local = threading.local()
        
        # 批量写入队列
        self._pending_messages: list[dict[str, Any]] = []
        self._pending_lock = threading.Lock()
        
        # 初始化数据库
        self._init_database()
        
        self._logger.info(f"SessionStore initialized: {self._db_path}")
    
    def _get_default_db_path(self) -> Path:
        """获取默认数据库路径"""
        try:
            from common.config import get_data_dir
            data_dir = get_data_dir()
        except ImportError:
            data_dir = Path.home() / ".agent_z"
        
        return data_dir / "tui_sessions.db"
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取线程独立的数据库连接"""
        if not hasattr(self._local, "connection"):
            self._local.connection = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False,
                isolation_level="DEFERRED",
            )
            # 启用外键约束
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            # 优化性能
            self._local.connection.execute("PRAGMA journal_mode = WAL")
            self._local.connection.execute("PRAGMA synchronous = NORMAL")
        
        return self._local.connection
    
    @contextmanager
    def _transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """事务上下文管理器"""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    def _init_database(self) -> None:
        """初始化数据库 schema"""
        with self._transaction() as conn:
            cursor = conn.cursor()
            
            # 创建版本表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY
                )
            """)
            
            # 获取当前版本
            cursor.execute("SELECT version FROM schema_version LIMIT 1")
            row = cursor.fetchone()
            current_version = row[0] if row else 0
            
            # 执行迁移
            if current_version < SCHEMA_VERSION:
                self._logger.info(f"Running migrations: {current_version} -> {SCHEMA_VERSION}")
                
                # 执行初始 schema
                cursor.executescript(INITIAL_SCHEMA)
                
                # 更新版本
                cursor.execute(
                    "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                    (SCHEMA_VERSION,)
                )
                
                current_version = SCHEMA_VERSION
            
            self._logger.debug(f"Database schema version: {current_version}")
    
    def _run_migrations(self, conn: sqlite3.Connection, from_version: int) -> int:
        """运行数据库迁移
        
        Args:
            conn: 数据库连接
            from_version: 起始版本
            
        Returns:
            迁移后的版本
        """
        cursor = conn.cursor()
        
        for i, migration in enumerate(MIGRATIONS[from_version:], start=from_version + 1):
            if migration.strip():
                self._logger.info(f"Applying migration {i}")
                cursor.executescript(migration)
        
        return SCHEMA_VERSION
    
    # ========================================================================
    # 会话 CRUD 操作
    # ========================================================================
    
    def create_session(
        self,
        model: str = "",
        provider: str = "",
        title: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """创建新会话
        
        Args:
            model: 模型名称
            provider: 模型提供商
            title: 会话标题（可选，默认自动生成）
            session_id: 指定会话 ID（可选，默认自动生成 UUID）
            
        Returns:
            新会话的 ID
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        if title is None:
            title = self._generate_title(session_id)
        
        now = datetime.now()
        
        with self._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sessions (id, title, created_at, updated_at, model, provider)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, title, now, now, model, provider),
            )
        
        self._logger.debug(f"Session created: {session_id}")
        return session_id
    
    def _generate_title(self, session_id: str) -> str:
        """生成会话标题"""
        return self._i18n.t("session.default_title")
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话信息
        
        Args:
            session_id: 会话 ID
            
        Returns:
            Session 对象，如果不存在则返回 None
        """
        with self._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, title, created_at, updated_at, model, provider, context_tokens, message_count "
                "FROM sessions WHERE id = ?",
                (session_id,),
            )
            row = cursor.fetchone()
        
        if row is None:
            return None
        
        return Session(
            id=row[0],
            title=row[1],
            created_at=datetime.fromisoformat(row[2]) if row[2] else None,
            updated_at=datetime.fromisoformat(row[3]) if row[3] else None,
            model=row[4],
            provider=row[5],
            context_tokens=row[6],
            message_count=row[7],
        )
    
    def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
        search_query: Optional[str] = None,
    ) -> list[Session]:
        """列出会话
        
        Args:
            limit: 返回数量限制
            offset: 跳过数量
            search_query: 搜索查询（匹配标题）
            
        Returns:
            Session 对象列表
        """
        with self._transaction() as conn:
            cursor = conn.cursor()
            
            if search_query:
                # 搜索模式
                cursor.execute(
                    """
                    SELECT id, title, created_at, updated_at, model, provider, context_tokens, message_count
                    FROM sessions
                    WHERE title LIKE ?
                    ORDER BY updated_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (f"%{search_query}%", limit, offset),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, title, created_at, updated_at, model, provider, context_tokens, message_count
                    FROM sessions
                    ORDER BY updated_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )
            
            rows = cursor.fetchall()
        
        return [
            Session(
                id=row[0],
                title=row[1],
                created_at=datetime.fromisoformat(row[2]) if row[2] else None,
                updated_at=datetime.fromisoformat(row[3]) if row[3] else None,
                model=row[4],
                provider=row[5],
                context_tokens=row[6],
                message_count=row[7],
            )
            for row in rows
        ]
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话
        
        Args:
            session_id: 会话 ID
            
        Returns:
            True 如果删除成功
        """
        with self._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            deleted = cursor.rowcount > 0
        
        if deleted:
            self._logger.debug(f"Session deleted: {session_id}")
        return deleted
    
    def update_session(
        self,
        session_id: str,
        title: Optional[str] = None,
        context_tokens: Optional[int] = None,
        message_count: Optional[int] = None,
    ) -> bool:
        """更新会话信息
        
        Args:
            session_id: 会话 ID
            title: 新标题
            context_tokens: 新的上下文 token 数
            message_count: 新的消息数量
            
        Returns:
            True 如果更新成功
        """
        updates = []
        params = []
        
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        
        if context_tokens is not None:
            updates.append("context_tokens = ?")
            params.append(context_tokens)
        
        if message_count is not None:
            updates.append("message_count = ?")
            params.append(message_count)
        
        if not updates:
            return False
        
        updates.append("updated_at = ?")
        params.append(datetime.now())
        
        params.append(session_id)
        
        with self._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE sessions SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            updated = cursor.rowcount > 0
        
        if updated:
            self._logger.debug(f"Session updated: {session_id}")
        return updated
    
    # ========================================================================
    # 消息 CRUD 操作
    # ========================================================================
    
    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tokens: Optional[int] = None,
        thinking_content: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        message_id: Optional[str] = None,
        flush: bool = True,
    ) -> str:
        """保存消息
        
        Args:
            session_id: 会话 ID
            role: 消息角色 (user/assistant/system/tool)
            content: 消息内容
            tokens: token 数量
            thinking_content: 思考过程
            metadata: 额外元数据
            message_id: 消息 ID（可选，自动生成）
            flush: 是否立即刷新到数据库
            
        Returns:
            消息 ID
        """
        if message_id is None:
            message_id = str(uuid.uuid4())
        
        now = datetime.now()
        metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
        
        if flush:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO messages (id, session_id, role, content, created_at, tokens, thinking_content, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (message_id, session_id, role, content, now, tokens, thinking_content, metadata_json),
                )
                
                # 更新会话统计
                cursor.execute(
                    """
                    UPDATE sessions 
                    SET message_count = message_count + 1,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (now, session_id),
                )
        else:
            # 加入待写入队列
            with self._pending_lock:
                self._pending_messages.append({
                    "id": message_id,
                    "session_id": session_id,
                    "role": role,
                    "content": content,
                    "created_at": now,
                    "tokens": tokens,
                    "thinking_content": thinking_content,
                    "metadata": metadata_json,
                })
        
        return message_id
    
    def flush_pending_messages(self) -> int:
        """刷新待写入消息到数据库
        
        Returns:
            写入的消息数量
        """
        with self._pending_lock:
            if not self._pending_messages:
                return 0
            
            messages = self._pending_messages.copy()
            self._pending_messages.clear()
        
        if not messages:
            return 0
        
        # ponytail: batch insert — N executemany instead of N execute calls
        msg_rows = [
            (m["id"], m["session_id"], m["role"], m["content"], m["created_at"],
             m["tokens"], m["thinking_content"], m["metadata"])
            for m in messages
        ]

        with self._transaction() as conn:
            cursor = conn.cursor()
            cursor.executemany(
                "INSERT INTO messages (id, session_id, role, content, created_at, tokens, thinking_content, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                msg_rows,
            )
            # 单次 UPDATE 按 session_id 分组，避免 N 次 round-trip
            from collections import defaultdict
            by_session: dict[str, list[datetime]] = defaultdict(list)
            for m in messages:
                by_session[m["session_id"]].append(m["created_at"])
            for sid, timestamps in by_session.items():
                cursor.execute(
                    "UPDATE sessions SET message_count = message_count + ?, updated_at = ? WHERE id = ?",
                    (len(timestamps), max(timestamps), sid),
                )
        
        self._logger.debug(f"Flushed {len(messages)} messages")
        return len(messages)
    
    def get_messages(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Message]:
        """获取会话消息
        
        Args:
            session_id: 会话 ID
            limit: 返回数量限制
            offset: 跳过数量
            
        Returns:
            Message 对象列表
        """
        with self._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, session_id, role, content, created_at, tokens, thinking_content, metadata
                FROM messages
                WHERE session_id = ?
                ORDER BY created_at ASC
                LIMIT ? OFFSET ?
                """,
                (session_id, limit, offset),
            )
            rows = cursor.fetchall()
        
        return [
            Message(
                id=row[0],
                session_id=row[1],
                role=row[2],
                content=row[3],
                created_at=datetime.fromisoformat(row[4]) if row[4] else None,
                tokens=row[5],
                thinking_content=row[6],
                metadata=json.loads(row[7]) if row[7] else None,
            )
            for row in rows
        ]
    
    def get_message_count(self, session_id: str) -> int:
        """获取会话消息数量
        
        Args:
            session_id: 会话 ID
            
        Returns:
            消息数量
        """
        with self._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM messages WHERE session_id = ?",
                (session_id,),
            )
            return cursor.fetchone()[0]
    
    # ========================================================================
    # 输入历史操作（跨会话持久化）
    # ========================================================================
    
    def save_input_history(self, content: str) -> None:
        """保存输入历史（去重，更新使用次数和时间）
        
        Args:
            content: 用户输入内容
        """
        content = content.strip()
        if not content:
            return
        
        now = datetime.now()
        
        with self._transaction() as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id, use_count FROM input_history WHERE content = ?",
                (content,),
            )
            row = cursor.fetchone()
            
            if row:
                cursor.execute(
                    """
                    UPDATE input_history
                    SET use_count = use_count + 1, last_used_at = ?
                    WHERE id = ?
                    """,
                    (now, row[0]),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO input_history (content, created_at, last_used_at)
                    VALUES (?, ?, ?)
                    """,
                    (content, now, now),
                )
    
    def load_input_history(self, limit: int = 100) -> list[str]:
        """加载输入历史
        
        Args:
            limit: 返回数量限制
            
        Returns:
            输入历史内容列表（按最后使用时间倒序）
        """
        with self._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT content
                FROM input_history
                ORDER BY last_used_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
        
        return [row[0] for row in rows]
    
    def delete_input_history(self, content: str) -> bool:
        """删除指定输入历史
        
        Args:
            content: 要删除的输入内容
            
        Returns:
            True 如果删除成功
        """
        with self._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM input_history WHERE content = ?",
                (content,),
            )
            deleted = cursor.rowcount > 0
        
        if deleted:
            self._logger.debug(f"Input history deleted: {content[:50]}...")
        return deleted
    
    def clear_input_history(self) -> int:
        """清空所有输入历史
        
        Returns:
            删除的记录数量
        """
        with self._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM input_history")
            deleted = cursor.rowcount
        
        self._logger.info(f"Cleared {deleted} input history records")
        return deleted
    
    # ========================================================================
    # 工具方法
    # ========================================================================
    
    def get_or_create_session(
        self,
        model: str = "",
        provider: str = "",
        session_id: Optional[str] = None,
    ) -> tuple[str, bool]:
        """获取或创建会话
        
        Args:
            model: 模型名称
            provider: 模型提供商
            session_id: 指定会话 ID（可选）
            
        Returns:
            (session_id, is_new) 元组，is_new 表示是否新建的会话
        """
        if session_id:
            existing = self.get_session(session_id)
            if existing:
                return session_id, False
        
        new_id = self.create_session(model, provider, session_id=session_id)
        return new_id, True
    
    def search_sessions(self, query: str, limit: int = 20) -> list[Session]:
        """搜索会话
        
        Args:
            query: 搜索关键词
            limit: 返回数量限制
            
        Returns:
            匹配的 Session 列表
        """
        return self.list_sessions(limit=limit, search_query=query)
    
    def close(self) -> None:
        """关闭数据库连接"""
        # 先 flush pending（复用已打开的主连接），否则关完连接再 flush 会
        # 重新打开一个新连接且不关闭，导致 Windows 文件句柄泄漏。
        self.flush_pending_messages()

        if hasattr(self._local, "connection"):
            conn = self._local.connection
            try:
                # 在 close 前把 WAL 合并回主库、截断 WAL 文件，
                # 避免 Windows 下 .db-wal / .db-shm 句柄残留。
                try:
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                except sqlite3.Error:
                    conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
                except Exception:
                    pass
                conn.commit()
            except Exception:
                pass
            finally:
                conn.close()
                del self._local.connection

        # CPython 对闭包/局部变量里的 cursor 可能有引用残留，
        # Windows 下会阻止 sqlite3 释放文件锁，强制 gc 一轮。
        gc.collect()

        self._logger.debug("SessionStore closed")

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例（主要用于测试）"""
        if cls._instance is not None:
            cls._instance.close()
            cls._instance = None
        gc.collect()


# ============================================================================
# 模块导出
# ============================================================================

__all__ = [
    "SessionStore",
    "Session",
    "Message",
]
