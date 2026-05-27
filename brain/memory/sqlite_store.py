"""
SQLite + FTS5 存储
支持全文搜索的历史对话存储
"""

import sqlite3
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path


class SQLiteStore:
    """SQLite 存储（支持 FTS5）"""
    
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()
    
    def _init_db(self) -> None:
        """初始化数据库"""
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        
        # 创建消息表
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建 FTS5 全文搜索表
        self._conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts 
            USING fts5(content, content=messages, content_rowid=rowid)
        """)
        
        # 创建会话表
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self._conn.commit()
    
    async def add_message(
        self, 
        message_id: str, 
        session_id: str, 
        role: str, 
        content: str, 
        metadata: Dict[str, Any] = None
    ) -> None:
        """添加消息"""
        metadata_json = json.dumps(metadata or {})
        
        self._conn.execute(
            """INSERT INTO messages (id, session_id, role, content, metadata)
               VALUES (?, ?, ?, ?, ?)""",
            (message_id, session_id, role, content, metadata_json)
        )
        self._conn.commit()
    
    async def search_messages(self, query: str, session_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索消息"""
        if session_id:
            sql = """
                SELECT m.* FROM messages m
                JOIN messages_fts fts ON m.rowid = fts.rowid
                WHERE messages_fts MATCH ? AND m.session_id = ?
                ORDER BY m.created_at DESC
                LIMIT ?
            """
            cursor = self._conn.execute(sql, (query, session_id, limit))
        else:
            sql = """
                SELECT m.* FROM messages m
                JOIN messages_fts fts ON m.rowid = fts.rowid
                WHERE messages_fts MATCH ?
                ORDER BY m.created_at DESC
                LIMIT ?
            """
            cursor = self._conn.execute(sql, (query, limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row["id"],
                "session_id": row["session_id"],
                "role": row["role"],
                "content": row["content"],
                "metadata": json.loads(row["metadata"] or "{}"),
                "created_at": row["created_at"],
            })
        
        return results
    
    async def get_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取会话历史"""
        cursor = self._conn.execute(
            """SELECT * FROM messages 
               WHERE session_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (session_id, limit)
        )
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row["id"],
                "role": row["role"],
                "content": row["content"],
                "metadata": json.loads(row["metadata"] or "{}"),
                "created_at": row["created_at"],
            })
        
        return list(reversed(results))
    
    async def create_session(self, session_id: str, user_id: str, metadata: Dict[str, Any] = None) -> None:
        """创建会话"""
        metadata_json = json.dumps(metadata or {})
        self._conn.execute(
            """INSERT INTO sessions (id, user_id, metadata) VALUES (?, ?, ?)""",
            (session_id, user_id, metadata_json)
        )
        self._conn.commit()
    
    async def update_session(self, session_id: str) -> None:
        """更新会话时间戳"""
        self._conn.execute(
            """UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
            (session_id,)
        )
        self._conn.commit()
    
    def close(self) -> None:
        """关闭连接"""
        if self._conn:
            self._conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()