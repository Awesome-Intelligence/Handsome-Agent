#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the session_search_tool module.

Tests cover session history search functionality including:
- Session searching
- Query filtering
- Role filtering
"""

import pytest
import json
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestSessionSearch:
    """Test suite for session_search."""

    def test_session_search_returns_json(self):
        """Test that session_search returns valid JSON."""
        from tools.session_search_tool import session_search
        
        result = session_search(query="test")
        assert isinstance(result, str)
        
        data = json.loads(result)
        assert "success" in data
        assert isinstance(data["success"], bool)
        assert "results" in data

    def test_session_search_with_limit(self):
        """Test session_search with limit parameter."""
        from tools.session_search_tool import session_search
        
        result = session_search(query="test", limit=5)
        data = json.loads(result)
        
        # Without database, returns success: False
        # With database, should have count field
        if data["success"]:
            assert "count" in data
            assert data["count"] >= 0

    def test_session_search_with_role_filter(self):
        """Test session_search with role filter."""
        from tools.session_search_tool import session_search
        
        result = session_search(query="test", role_filter="user")
        data = json.loads(result)
        
        assert "results" in data


class TestSessionSearchWithDB:
    """Test session_search with actual database."""

    def test_session_search_with_temp_db(self):
        """Test session_search with a temporary database."""
        from tools.session_search_tool import session_search
        
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            # Create test table and insert data
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TEXT
                )
            """)
            cursor.execute(
                "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                ("test_session", "user", "Hello, this is a test message", "2024-01-01")
            )
            conn.commit()
            conn.close()
            
            # Search with database
            result = session_search(query="test", limit=10, **{"db": db_path})
            data = json.loads(result)
            
            assert data["success"] is True
            assert "results" in data
            
        finally:
            # Cleanup
            Path(db_path).unlink(missing_ok=True)


class TestCheckSessionSearchRequirements:
    """Test session search requirements."""

    def test_check_session_search_requirements(self):
        """Test session search requirements check."""
        from tools.session_search_tool import check_session_search_requirements
        
        result = check_session_search_requirements()
        assert isinstance(result, bool)


class TestGetSessionDBPath:
    """Test session database path detection."""

    def test_get_session_db_path(self):
        """Test getting session database path."""
        from tools.session_search_tool import _get_session_db_path
        
        result = _get_session_db_path()
        # May be None if no database exists
        assert result is None or isinstance(result, Path)


class TestSessionSearchSchema:
    """Test session search schema."""

    def test_schema_structure(self):
        """Test session_search schema structure."""
        from tools.session_search_tool import SESSION_SEARCH_SCHEMA
        
        assert "name" in SESSION_SEARCH_SCHEMA
        assert SESSION_SEARCH_SCHEMA["name"] == "session_search"
        assert "description" in SESSION_SEARCH_SCHEMA
        assert "parameters" in SESSION_SEARCH_SCHEMA
        
        params = SESSION_SEARCH_SCHEMA["parameters"]
        assert "properties" in params
        assert "query" in params["properties"]


class TestSessionSearchRegistry:
    """Test tool registry integration."""

    def test_tools_registered(self):
        """Test that session search tools are registered."""
        from tools.registry import registry
        
        tool = registry.get("session_search")
        assert tool is not None, "Tool session_search should be registered"

    def test_tool_has_handler(self):
        """Test that tool has handler."""
        from tools.registry import registry
        
        tool = registry.get("session_search")
        assert tool.handler is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
