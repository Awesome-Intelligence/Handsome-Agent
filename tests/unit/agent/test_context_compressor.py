#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for enhanced _summarize_tool_result function

Tests all tool types to ensure meaningful summaries are generated.
"""

import pytest
from agent.context.context_compressor import _summarize_tool_result


class TestSummarizeToolResult:
    """Test suite for _summarize_tool_result function."""

    # ═══════════════════════════════════════════════════════════════
    # 📁 File Operations
    # ═══════════════════════════════════════════════════════════════
    
    def test_read_file(self):
        """Test read_file summary generation."""
        args = '{"path": "/home/user/test.py", "offset": 1, "limit": 100}'
        content = "a" * 5000
        result = _summarize_tool_result("read_file", args, content)
        
        assert "[read_file]" in result
        assert "/home/user/test.py" in result
        assert "line" in result
        assert "5,000 chars" in result

    def test_write_file(self):
        """Test write_file summary generation."""
        # Note: JSON strings need double-escaped newlines in Python
        args = '{"path": "/test.py", "content": "a\\nb\\nc"}'
        content = "File written successfully"
        result = _summarize_tool_result("write_file", args, content)
        
        assert "[write_file]" in result
        assert "/test.py" in result
        assert "3 lines" in result

    def test_patch(self):
        """Test patch summary generation."""
        args = '{"path": "/test.py", "mode": "replace", "old_string": "foo", "new_string": "bar"}'
        content = "Patched 1 location"
        result = _summarize_tool_result("patch", args, content)
        
        assert "[patch]" in result
        assert "/test.py" in result
        assert "replace" in result

    def test_list_directory(self):
        """Test list_directory summary generation."""
        args = '{"path": "/home", "all": false}'
        content = "file1.txt\nfile2.txt"
        result = _summarize_tool_result("list_directory", args, content)
        
        assert "[list_directory]" in result
        assert "/home" in result
        # content.count("\n") = 1, so "1 entries" or "2 entries"
        assert "entries" in result

    def test_list_directory_with_hidden(self):
        """Test list_directory with hidden files."""
        args = '{"path": "/home", "all": true}'
        content = "file1.txt\n.filehidden"
        result = _summarize_tool_result("list_directory", args, content)
        
        assert "incl. hidden" in result

    # ═══════════════════════════════════════════════════════════════
    # 🔍 Search Operations
    # ═══════════════════════════════════════════════════════════════
    
    def test_search_files(self):
        """Test search_files summary generation."""
        args = '{"pattern": "function", "path": "/src", "target": "content"}'
        content = '{"total_count": 15, "matches": [...]}'
        result = _summarize_tool_result("search_files", args, content)
        
        assert "[search_files]" in result
        assert "function" in result
        assert "15 matches" in result

    def test_grep(self):
        """Test grep summary generation."""
        args = '{"pattern": "TODO", "path": "."}'
        # Grep uses the same logic as search_files, try with standard format
        content = '{"total_count": 5}'
        result = _summarize_tool_result("grep", args, content)
        
        assert "[grep]" in result
        assert "TODO" in result
        assert "5" in result

    # ═══════════════════════════════════════════════════════════════
    # 🖥️ Terminal Operations
    # ═══════════════════════════════════════════════════════════════
    
    def test_terminal_success(self):
        """Test terminal success case."""
        args = '{"command": "python test.py"}'
        content = '{"exit_code": 0, "output": "Tests passed"}'
        result = _summarize_tool_result("terminal", args, content)
        
        assert "[terminal]" in result
        assert "exit 0" in result
        assert "test.py" in result

    def test_terminal_failure(self):
        """Test terminal failure case."""
        args = '{"command": "npm build"}'
        content = '{"exit_code": 1, "error": "Build failed"}'
        result = _summarize_tool_result("terminal", args, content)
        
        assert "[terminal]" in result
        assert "exit 1" in result

    def test_terminal_long_command(self):
        """Test terminal with command in result."""
        args = '{"command": "git commit"}'
        content = '{"exit_code": 0}'
        result = _summarize_tool_result("terminal", args, content)
        
        assert "[terminal]" in result
        assert "commit" in result

    def test_bash(self):
        """Test bash summary generation."""
        args = '{"command": "ls -la"}'
        content = '{"exit_code": 0}'
        result = _summarize_tool_result("bash", args, content)
        
        assert "[bash]" in result
        assert "exit 0" in result

    # ═══════════════════════════════════════════════════════════════
    # 🐳 Code Execution
    # ═══════════════════════════════════════════════════════════════
    
    def test_execute_code(self):
        """Test execute_code summary generation."""
        args = '{"language": "python", "code": "print(sum(range(100)))"}'
        content = "4950"
        result = _summarize_tool_result("execute_code", args, content)
        
        assert "[execute_code]" in result
        assert "python" in result

    # ═══════════════════════════════════════════════════════════════
    # 🌐 Web Operations
    # ═══════════════════════════════════════════════════════════════
    
    def test_web_search(self):
        """Test web_search summary generation."""
        args = '{"query": "python tutorial", "limit": 10}'
        content = '{"results": [...]}'
        result = _summarize_tool_result("web_search", args, content)
        
        assert "[web_search]" in result
        assert "python tutorial" in result
        assert "limit=10" in result

    def test_web_extract(self):
        """Test web_extract summary generation."""
        args = '{"urls": ["https://example.com", "https://example2.com"]}'
        content = "Extracted content..."
        result = _summarize_tool_result("web_extract", args, content)
        
        assert "[web_extract]" in result
        assert "example.com" in result
        assert "+1 more" in result

    # ═══════════════════════════════════════════════════════════════
    # 🌐 Browser Operations
    # ═══════════════════════════════════════════════════════════════
    
    def test_browser_navigate(self):
        """Test browser_navigate summary generation."""
        args = '{"url": "https://google.com"}'
        content = ""
        result = _summarize_tool_result("browser_navigate", args, content)
        
        assert "[browser_navigate]" in result
        assert "google.com" in result

    def test_browser_vision(self):
        """Test browser_vision summary generation."""
        args = '{"question": "What is on this page?"}'
        content = "The page shows..."
        result = _summarize_tool_result("browser_vision", args, content)
        
        assert "[browser_vision]" in result
        assert "What is on this page?" in result

    def test_browser_snapshot(self):
        """Test browser_snapshot summary generation."""
        args = '{"url": "https://example.com"}'
        content = "Page content..."
        result = _summarize_tool_result("browser_snapshot", args, content)
        
        assert "[browser_snapshot]" in result

    # ═══════════════════════════════════════════════════════════════
    # 🖼️ Vision/Image Operations
    # ═══════════════════════════════════════════════════════════════
    
    def test_analyze_image(self):
        """Test analyze_image summary generation."""
        args = '{"question": "What colors are in this image?"}'
        content = "The image contains..."
        result = _summarize_tool_result("analyze_image", args, content)
        
        assert "[analyze_image]" in result

    def test_image_generate(self):
        """Test image_generate summary generation."""
        args = '{"prompt": "A beautiful sunset", "model": "dall-e-3"}'
        content = '{"image_url": "..."}'
        result = _summarize_tool_result("image_generate", args, content)
        
        assert "[image_generate]" in result
        assert "dall-e-3" in result
        assert "beautiful sunset" in result

    # ═══════════════════════════════════════════════════════════════
    # 🧠 Memory Operations
    # ═══════════════════════════════════════════════════════════════
    
    def test_memory_add(self):
        """Test memory add summary generation."""
        args = '{"action": "add", "target": "memory", "content": "User prefers dark mode"}'
        content = '{"success": true, "entry_count": 5}'
        result = _summarize_tool_result("memory", args, content)
        
        assert "[memory]" in result
        assert "add" in result
        assert "5 entries" in result

    def test_session_search(self):
        """Test session_search summary generation."""
        args = '{"query": "python", "limit": 5}'
        content = '{"result_count": 3}'
        result = _summarize_tool_result("session_search", args, content)
        
        assert "[session_search]" in result
        assert "python" in result
        assert "3 results" in result

    # ═══════════════════════════════════════════════════════════════
    # 📋 Task Management
    # ═══════════════════════════════════════════════════════════════
    
    def test_todo(self):
        """Test todo summary generation."""
        args = '{"action": "list"}'
        content = ""
        result = _summarize_tool_result("todo", args, content)
        
        assert "[todo]" in result
        assert "list" in result

    def test_todo_create(self):
        """Test todo_create summary generation."""
        args = '{"title": "Complete the project report"}'
        content = ""
        result = _summarize_tool_result("todo_create", args, content)
        
        assert "[todo_create]" in result
        assert "project report" in result

    def test_todo_complete(self):
        """Test todo_complete summary generation."""
        args = '{"task_id": "task-123"}'
        content = ""
        result = _summarize_tool_result("todo_complete", args, content)
        
        assert "[todo_complete]" in result
        assert "task-123" in result

    # ═══════════════════════════════════════════════════════════════
    # 🛠️ Skills Operations
    # ═══════════════════════════════════════════════════════════════
    
    def test_skill_view(self):
        """Test skill_view summary generation."""
        args = '{"name": "web_scraper"}'
        content = ""
        result = _summarize_tool_result("skill_view", args, content)
        
        assert "[skill_view]" in result
        assert "web_scraper" in result

    def test_skills_list(self):
        """Test skills_list summary generation."""
        args = '{"action": "list"}'
        content = ""
        result = _summarize_tool_result("skills_list", args, content)
        
        assert "[skills_list]" in result

    # ═══════════════════════════════════════════════════════════════
    # 📢 Communication Operations
    # ═══════════════════════════════════════════════════════════════
    
    def test_text_to_speech(self):
        """Test text_to_speech summary generation."""
        args = '{"text": "Hello, how are you?", "voice": "alloy"}'
        content = ""
        result = _summarize_tool_result("text_to_speech", args, content)
        
        assert "[text_to_speech]" in result
        assert "alloy" in result
        assert "Hello" in result

    def test_clarify(self):
        """Test clarify summary generation."""
        args = '{}'
        content = ""
        result = _summarize_tool_result("clarify", args, content)
        
        assert "[clarify]" in result

    # ═══════════════════════════════════════════════════════════════
    # ⏰ Scheduler Operations
    # ═══════════════════════════════════════════════════════════════
    
    def test_cronjob(self):
        """Test cronjob summary generation."""
        args = '{"action": "create", "schedule": "0 * * * *"}'
        content = ""
        result = _summarize_tool_result("cronjob", args, content)
        
        assert "[cronjob]" in result
        assert "create" in result

    # ═══════════════════════════════════════════════════════════════
    # 🔧 System Operations
    # ═══════════════════════════════════════════════════════════════
    
    def test_delegate_task(self):
        """Test delegate_task summary generation."""
        args = '{"goal": "Research and summarize the latest AI developments"}'
        content = "Task result..."
        result = _summarize_tool_result("delegate_task", args, content)
        
        assert "[delegate_task]" in result
        assert "Research" in result

    def test_checkpoint(self):
        """Test checkpoint summary generation."""
        args = '{"action": "save", "name": "checkpoint-001"}'
        content = ""
        result = _summarize_tool_result("checkpoint", args, content)
        
        assert "[checkpoint]" in result
        assert "save" in result

    # ═══════════════════════════════════════════════════════════════
    # 🏠 Home Automation
    # ═══════════════════════════════════════════════════════════════
    
    def test_ha_list_entities(self):
        """Test ha_list_entities summary generation."""
        args = '{"entity_id": "light.living_room"}'
        content = ""
        result = _summarize_tool_result("ha_list_entities", args, content)
        
        assert "[ha_list_entities]" in result
        assert "living_room" in result

    # ═══════════════════════════════════════════════════════════════
    # 🔄 Generic Fallback
    # ═══════════════════════════════════════════════════════════════
    
    def test_unknown_tool(self):
        """Test unknown tool falls back to generic format."""
        args = '{"custom_param": "value", "another": "data"}'
        content = "x" * 1000
        result = _summarize_tool_result("some_unknown_tool", args, content)
        
        assert "[some_unknown_tool]" in result
        assert "custom_param" in result
        assert "1,000 chars" in result

    def test_empty_args(self):
        """Test with empty args - should use generic fallback."""
        args = ''
        content = "some result content"
        result = _summarize_tool_result("terminal", args, content)
        
        # With empty args, falls back to generic format showing chars count
        assert "[terminal]" in result

    def test_invalid_json_args(self):
        """Test with invalid JSON args."""
        args = "not valid json"
        content = "result"
        result = _summarize_tool_result("terminal", args, content)
        
        assert "[terminal]" in result

    def test_empty_content(self):
        """Test with empty content."""
        args = '{"command": "ls"}'
        content = ""
        result = _summarize_tool_result("terminal", args, content)
        
        assert "[terminal]" in result
        assert "ls" in result


class TestSummarizeToolResultContextSavings:
    """Test that summaries actually save context space."""

    def test_read_file_large_content(self):
        """Large file read should be summarized to short string."""
        args = '{"path": "/large/file.py", "offset": 1, "limit": 10000}'
        # Simulate a very large file content (10000 lines)
        content = "line\n" * 10000
        result = _summarize_tool_result("read_file", args, content)
        
        # Result should be much shorter than original content
        assert len(result) < 200
        assert "[read_file]" in result

    def test_terminal_large_output(self):
        """Large terminal output should be summarized."""
        args = '{"command": "npm run build"}'
        # Simulate large build output
        content = "Building...\n" + "compiled successfully\n" * 1000
        result = _summarize_tool_result("terminal", args, content)
        
        # Result should be concise
        assert len(result) < 100
        assert "exit" in result

    def test_web_search_large_results(self):
        """Large web search results should be summarized."""
        args = '{"query": "python documentation", "limit": 10}'
        # Simulate large search results
        content = '{"results": [' + '{"title": "Python Docs", "url": "..."},' * 100 + ']}'
        result = _summarize_tool_result("web_search", args, content)
        
        # Result should be concise
        assert len(result) < 80


if __name__ == "__main__":
    pytest.main([__file__, "-v"])