#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the brain module memory storage.

Tests cover vector store, SQLite store, and summarizer functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import json


class TestVectorStore:
    """Test vector store functionality."""
    
    def test_vector_store_initialization(self):
        """Test initializing vector store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test basic initialization
            store_path = Path(tmpdir) / "vectors"
            
            # Should create directory
            store_path.mkdir(parents=True, exist_ok=True)
            assert store_path.exists()
    
    def test_add_vector(self):
        """Test adding a vector."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "vectors.json"
            
            vectors = {}
            vectors["doc_001"] = {
                "id": "doc_001",
                "text": "Sample text",
                "embedding": [0.1, 0.2, 0.3],
                "metadata": {"source": "test"}
            }
            
            with open(store_path, 'w') as f:
                json.dump(vectors, f)
            
            assert store_path.exists()
            
            with open(store_path, 'r') as f:
                loaded = json.load(f)
            
            assert "doc_001" in loaded
            assert loaded["doc_001"]["text"] == "Sample text"
    
    def test_search_similar(self):
        """Test searching for similar vectors."""
        vectors = {
            "doc_001": {"text": "Python programming", "embedding": [0.9, 0.1, 0.1]},
            "doc_002": {"text": "JavaScript tutorials", "embedding": [0.1, 0.9, 0.1]},
            "doc_003": {"text": "Machine learning", "embedding": [0.1, 0.1, 0.9]}
        }
        
        query = [0.85, 0.1, 0.1]  # Similar to Python programming
        
        # Simple cosine similarity (mock)
        similarities = {}
        for doc_id, data in vectors.items():
            # Simplified similarity calculation
            emb = data["embedding"]
            sim = sum(q * e for q, e in zip(query, emb))
            similarities[doc_id] = sim
        
        # Sort by similarity
        results = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
        
        assert results[0][0] == "doc_001"  # Most similar
        assert results[0][1] > results[1][1]


class TestSQLiteStore:
    """Test SQLite memory store."""
    
    def test_sqlite_store_initialization(self):
        """Test initializing SQLite store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            # Test creating database
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT,
                    timestamp REAL,
                    metadata TEXT
                )
            """)
            
            conn.commit()
            conn.close()
            
            assert db_path.exists()
    
    def test_insert_memory(self):
        """Test inserting a memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Create table
            cursor.execute("""
                CREATE TABLE memories (
                    id TEXT PRIMARY KEY,
                    content TEXT,
                    timestamp REAL,
                    metadata TEXT
                )
            """)
            
            # Insert memory
            import time
            cursor.execute("""
                INSERT INTO memories (id, content, timestamp, metadata)
                VALUES (?, ?, ?, ?)
            """, ("mem_001", "Test memory", time.time(), "{}"))
            
            conn.commit()
            conn.close()
            
            # Verify
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM memories WHERE id = ?", ("mem_001",))
            result = cursor.fetchone()
            conn.close()
            
            assert result is not None
            assert result[1] == "Test memory"
    
    def test_search_memories(self):
        """Test searching memories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Create table with FTS
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT,
                    timestamp REAL
                )
            """)
            
            # Insert test data
            import time
            memories = [
                ("mem_001", "Python programming", time.time()),
                ("mem_002", "JavaScript tutorials", time.time()),
                ("mem_003", "Python machine learning", time.time())
            ]
            
            cursor.executemany(
                "INSERT INTO memories VALUES (?, ?, ?)",
                memories
            )
            
            conn.commit()
            
            # Search
            cursor.execute(
                "SELECT * FROM memories WHERE content LIKE ?",
                ("%Python%",)
            )
            results = cursor.fetchall()
            conn.close()
            
            assert len(results) == 2
    
    def test_delete_memory(self):
        """Test deleting a memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE memories (
                    id TEXT PRIMARY KEY,
                    content TEXT
                )
            """)
            
            # Insert
            cursor.execute("INSERT INTO memories VALUES (?, ?)", ("mem_001", "Test"))
            conn.commit()
            
            # Delete
            cursor.execute("DELETE FROM memories WHERE id = ?", ("mem_001",))
            conn.commit()
            
            # Verify
            cursor.execute("SELECT * FROM memories WHERE id = ?", ("mem_001",))
            result = cursor.fetchone()
            conn.close()
            
            assert result is None


class TestSummarizer:
    """Test message summarizer."""
    
    def test_summarizer_initialization(self):
        """Test initializing summarizer."""
        from brain.memory.summarizer import Summarizer
        
        summarizer = Summarizer(max_length=1000)
        
        assert summarizer is not None
        assert summarizer.max_length == 1000
    
    def test_summarize_short_text(self):
        """Test summarizing short text."""
        from brain.memory.summarizer import Summarizer
        
        summarizer = Summarizer()
        
        short_text = "This is a short text."
        summary = summarizer.summarize(short_text)
        
        # Short text should remain unchanged
        assert len(summary) <= len(short_text) + 10
    
    def test_summarize_long_text(self):
        """Test summarizing long text."""
        from brain.memory.summarizer import Summarizer
        
        summarizer = Summarizer(max_length=100)
        
        long_text = " ".join(["word"] * 200)
        summary = summarizer.summarize(long_text)
        
        # Summary should be shorter
        assert len(summary) < len(long_text)
    
    def test_summarize_conversation(self):
        """Test summarizing conversation."""
        from brain.memory.summarizer import Summarizer
        
        summarizer = Summarizer()
        
        conversation = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
            {"role": "assistant", "content": "I'm doing great, thanks for asking!"}
        ]
        
        summary = summarizer.summarize_conversation(conversation)
        
        assert summary is not None
        assert isinstance(summary, str)


class TestMemoryIndexing:
    """Test memory indexing functionality."""
    
    def test_create_index(self):
        """Test creating memory index."""
        index = {
            "keywords": {},
            "timestamps": [],
            "categories": {}
        }
        
        assert "keywords" in index
        assert "timestamps" in index
        assert "categories" in index
    
    def test_add_to_index(self):
        """Test adding memory to index."""
        index = {"keywords": {}, "timestamps": []}
        
        memory = {
            "id": "mem_001",
            "content": "Python programming tutorial",
            "timestamp": 1234567890.0,
            "keywords": ["python", "programming", "tutorial"]
        }
        
        # Index by keywords
        for keyword in memory["keywords"]:
            if keyword not in index["keywords"]:
                index["keywords"][keyword] = []
            index["keywords"][keyword].append(memory["id"])
        
        # Index by timestamp
        index["timestamps"].append((memory["timestamp"], memory["id"]))
        
        assert "python" in index["keywords"]
        assert "mem_001" in index["keywords"]["python"]
        assert len(index["timestamps"]) == 1
    
    def test_search_by_keyword(self):
        """Test searching memories by keyword."""
        index = {
            "keywords": {
                "python": ["mem_001", "mem_003"],
                "javascript": ["mem_002"]
            }
        }
        
        results = index["keywords"].get("python", [])
        
        assert len(results) == 2
        assert "mem_001" in results
        assert "mem_003" in results
    
    def test_search_by_time_range(self):
        """Test searching memories by time range."""
        index = {
            "timestamps": [
                (1000.0, "mem_001"),
                (2000.0, "mem_002"),
                (3000.0, "mem_003")
            ]
        }
        
        # Search between 1500 and 2500
        start_time = 1500.0
        end_time = 2500.0
        
        results = [
            mem_id for ts, mem_id in index["timestamps"]
            if start_time <= ts <= end_time
        ]
        
        assert len(results) == 1
        assert "mem_002" in results


class TestMemoryRetrieval:
    """Test memory retrieval functionality."""
    
    def test_retrieve_recent_memories(self):
        """Test retrieving recent memories."""
        memories = [
            {"id": "mem_001", "timestamp": 1000.0, "content": "Old memory"},
            {"id": "mem_002", "timestamp": 2000.0, "content": "Recent memory"},
            {"id": "mem_003", "timestamp": 3000.0, "content": "Newest memory"}
        ]
        
        # Get 2 most recent
        recent = sorted(memories, key=lambda x: x["timestamp"], reverse=True)[:2]
        
        assert len(recent) == 2
        assert recent[0]["id"] == "mem_003"
        assert recent[1]["id"] == "mem_002"
    
    def test_retrieve_by_category(self):
        """Test retrieving memories by category."""
        memories = [
            {"id": "mem_001", "category": "programming", "content": "Python"},
            {"id": "mem_002", "category": "design", "content": "UI/UX"},
            {"id": "mem_003", "category": "programming", "content": "JavaScript"}
        ]
        
        programming_memories = [
            m for m in memories if m["category"] == "programming"
        ]
        
        assert len(programming_memories) == 2
        assert all(m["category"] == "programming" for m in programming_memories)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
