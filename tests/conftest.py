"""
pytest configuration file for the Agent-Z.

This file contains shared fixtures and configuration for all tests.
"""

import pytest
import asyncio
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Mock problematic modules before any imports
mock_modules = {
    'skills': MagicMock(),
    'skills.telemetry': MagicMock(),
}

for mod_name, mock_mod in mock_modules.items():
    if mod_name not in sys.modules:
        sys.modules[mod_name] = mock_mod

from agent.agent import Agent, AgentResponse


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def basic_agent():
    """Create a basic Agent instance for testing."""
    return Agent(llm_provider=None)


@pytest.fixture
def test_config():
    """Create a test configuration."""
    return {"timeout_seconds": 1.0}


# ============================================================================
# TUI Test Fixtures
# ============================================================================

@pytest.fixture
def sealed_workspace():
    """
    Create a sealed workspace with isolated config directories.
    This prevents tests from accessing real user config.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir) / "workspace"
        home = Path(tmpdir) / "home"
        config = home / ".agent_z"
        cache = home / ".cache" / "agentz"
        
        workspace.mkdir()
        home.mkdir()
        config.mkdir(parents=True)
        cache.mkdir(parents=True)
        
        yield {
            "workspace": workspace,
            "home": home,
            "config": config,
            "cache": cache,
            "env": {
                "HOME": str(home),
                "USERPROFILE": str(home),
                "XDG_CONFIG_HOME": str(home / ".config"),
                "XDG_DATA_HOME": str(home / ".local" / "share"),
                "XDG_CACHE_HOME": str(home / ".cache"),
                "AGENTZ_CONFIG_PATH": str(config / "config.toml"),
            }
        }


@pytest.fixture
def mock_llm_server():
    """
    Create a mock LLM server for testing.
    Returns mock response handlers.
    """
    class MockLLMResponse:
        def __init__(self, content: str = "", tool_calls: list = None):
            self.content = content
            self.tool_calls = tool_calls or []
            self.usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    
    def create_response(content: str = "", tool_calls: list = None) -> MockLLMResponse:
        return MockLLMResponse(content=content, tool_calls=tool_calls)
    
    def create_tool_call_response(tool_name: str, tool_input: dict) -> MockLLMResponse:
        return MockLLMResponse(
            content="",
            tool_calls=[{
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": tool_input
                }
            }]
        )
    
    return {
        "response": create_response,
        "tool_call": create_tool_call_response,
    }


@pytest.fixture
def mock_llm_stream():
    """
    Create a mock streaming LLM response generator.
    Yields chunks of text for testing streaming behavior.
    """
    async def stream_response(text: str, chunk_size: int = 1):
        """Yield text in chunks."""
        for i in range(0, len(text), chunk_size):
            yield text[i:i + chunk_size]
            await asyncio.sleep(0)  # Allow other coroutines to run
    
    return stream_response


@pytest.fixture
def mock_textual_app():
    """
    Create a mock Textual app for testing without actual app creation.
    """
    from unittest.mock import MagicMock, PropertyMock
    
    app = MagicMock()
    app.dark = PropertyMock(return_value=False)
    app.compose = MagicMock(return_value=[])
    app.screen = MagicMock()
    app.refresh = MagicMock()
    
    return app


@pytest.fixture
def mock_session_store():
    """
    Create a mock session store for testing.
    """
    sessions = {}
    session_counter = 0
    
    class MockSessionStore:
        def create_session(self, title: str = "New Session") -> dict:
            nonlocal session_counter
            session_counter += 1
            session_id = f"session_{session_counter}"
            sessions[session_id] = {
                "id": session_id,
                "title": title,
                "messages": [],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
            return sessions[session_id]
        
        def get_session(self, session_id: str) -> dict:
            return sessions.get(session_id)
        
        def list_sessions(self) -> list:
            return list(sessions.values())
        
        def save_message(self, session_id: str, message: dict):
            if session_id in sessions:
                sessions[session_id]["messages"].append(message)
                sessions[session_id]["updated_at"] = "2024-01-01T00:00:00Z"
        
        def delete_session(self, session_id: str) -> bool:
            if session_id in sessions:
                del sessions[session_id]
                return True
            return False
    
    return MockSessionStore()


@pytest.fixture
def sample_markdown_content():
    """Sample markdown content for testing rendering."""
    return """# Heading 1
## Heading 2

This is **bold** and *italic* text.

- List item 1
- List item 2

```python
def hello():
    print("Hello, World!")
```

[Link](https://example.com)
"""


@pytest.fixture
def sample_message_history():
    """Sample message history for testing."""
    return [
        {
            "role": "user",
            "content": "Hello, how are you?",
            "timestamp": "2024-01-01T00:00:00Z",
        },
        {
            "role": "assistant",
            "content": "I'm doing well! How can I help you?",
            "timestamp": "2024-01-01T00:00:01Z",
        },
        {
            "role": "user",
            "content": "Can you list files?",
            "timestamp": "2024-01-01T00:00:02Z",
        },
    ]


@pytest.fixture
def sample_tool_result():
    """Sample tool result for testing."""
    return {
        "tool_call_id": "call_123",
        "tool_name": "list_dir",
        "status": "success",
        "output": [
            {"name": "README.md", "is_dir": False, "size": 1024},
            {"name": "src", "is_dir": True, "size": 0},
            {"name": "tests", "is_dir": True, "size": 0},
        ],
        "timestamp": "2024-01-01T00:00:03Z",
    }
