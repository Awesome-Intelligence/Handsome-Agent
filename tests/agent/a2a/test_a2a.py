#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for A2A protocol module.
"""

# 🧠 Decision - 💾 Memory - A2A Tests

import json
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.a2a.models import (
    AgentCard,
    AgentCapabilities,
    Message,
    MessageRole,
    Part,
    Task,
    TaskStatus,
    TaskStatusUpdate,
    TextPart,
    DataPart,
    FilePart,
    part_from_dict,
    JSONRPCRequest,
    JSONRPCResponse,
)
from agent.a2a.server import A2AServer, TaskStore


class TestAgentCard:
    """Tests for AgentCard."""

    def test_create_agent_card(self):
        """Test creating an AgentCard."""
        card = AgentCard(
            name="Test Agent",
            description="A test agent",
            url="http://localhost:8003",
            version="1.0.0",
        )
        assert card.name == "Test Agent"
        assert card.url == "http://localhost:8003"
        assert card.version == "1.0.0"

    def test_to_dict(self):
        """Test AgentCard serialization."""
        card = AgentCard(
            name="Test Agent",
            description="A test agent",
            url="http://localhost:8003",
        )
        data = card.to_dict()

        assert data["name"] == "Test Agent"
        assert data["url"] == "http://localhost:8003"
        assert "capabilities" in data
        assert "defaultInputModes" in data

    def test_from_dict(self):
        """Test AgentCard deserialization."""
        data = {
            "name": "Test Agent",
            "description": "A test agent",
            "url": "http://localhost:8003",
            "version": "2.0.0",
            "capabilities": {
                "streaming": True,
                "pushNotifications": False,
            },
            "skills": [
                {
                    "id": "skill1",
                    "name": "TestSkill",
                    "description": "A test skill",
                }
            ],
        }
        card = AgentCard.from_dict(data)

        assert card.name == "Test Agent"
        assert card.version == "2.0.0"
        assert card.capabilities.streaming is True
        assert len(card.skills) == 1
        assert card.skills[0].name == "TestSkill"


class TestParts:
    """Tests for Part types."""

    def test_text_part_to_dict(self):
        """Test TextPart serialization."""
        part = TextPart("Hello, World!")
        data = part.to_dict()

        assert data["type"] == "text"
        assert data["text"] == "Hello, World!"

    def test_text_part_from_dict(self):
        """Test TextPart deserialization."""
        data = {"type": "text", "text": "Hello, World!"}
        part = part_from_dict(data)

        assert isinstance(part, TextPart)
        assert part.text == "Hello, World!"

    def test_data_part(self):
        """Test DataPart."""
        data = {"type": "data", "data": {"key": "value"}, "mimeType": "application/json"}
        part = part_from_dict(data)

        assert isinstance(part, DataPart)
        assert part.data == {"key": "value"}
        assert part.mime_type == "application/json"

    def test_file_part(self):
        """Test FilePart."""
        data = {
            "type": "file",
            "name": "test.txt",
            "mimeType": "text/plain",
            "uri": "file:///tmp/test.txt",
            "bytes": 100,
        }
        part = part_from_dict(data)

        assert isinstance(part, FilePart)
        assert part.name == "test.txt"
        assert part.uri == "file:///tmp/test.txt"


class TestMessage:
    """Tests for Message."""

    def test_create_message(self):
        """Test creating a Message."""
        msg = Message(role=MessageRole.USER, parts=[TextPart("Hello")])

        assert msg.role == MessageRole.USER
        assert len(msg.parts) == 1
        assert isinstance(msg.parts[0], TextPart)

    def test_create_text_message(self):
        """Test creating a simple text message."""
        msg = Message.create_text("Hello, World!", role="user")

        assert msg.role == MessageRole.USER
        assert len(msg.parts) == 1
        assert msg.parts[0].text == "Hello, World!"

    def test_message_to_dict(self):
        """Test Message serialization."""
        msg = Message(role="agent", parts=[TextPart("Response")])
        data = msg.to_dict()

        assert data["role"] == "agent"
        assert len(data["parts"]) == 1
        assert data["parts"][0]["type"] == "text"

    def test_message_from_dict(self):
        """Test Message deserialization."""
        data = {
            "role": "user",
            "parts": [{"type": "text", "text": "Hello"}],
        }
        msg = Message.from_dict(data)

        assert msg.role == MessageRole.USER
        assert len(msg.parts) == 1
        assert msg.parts[0].text == "Hello"


class TestTask:
    """Tests for Task."""

    def test_create_task(self):
        """Test creating a Task."""
        task = Task(session_id="sess-123")

        assert task.task_id.startswith("task_")
        assert task.session_id == "sess-123"
        assert task.status == TaskStatus.SUBMITTED
        assert len(task.status_history) == 1

    def test_update_status(self):
        """Test updating task status."""
        task = Task()
        task.update_status(TaskStatus.WORKING)

        assert task.status == TaskStatus.WORKING
        assert len(task.status_history) == 2
        assert task.status_history[-1].status == TaskStatus.WORKING

    def test_add_message(self):
        """Test adding message to task."""
        task = Task()
        msg = Message.create_text("Hello")
        task.add_message(msg)

        assert len(task.messages) == 1
        assert task.messages[0].parts[0].text == "Hello"

    def test_task_to_dict(self):
        """Test Task serialization."""
        task = Task(session_id="sess-456")
        task.add_message(Message.create_text("Hello"))
        data = task.to_dict()

        assert "taskId" in data
        assert data["sessionId"] == "sess-456"
        assert data["status"]["status"] == "submitted"
        assert len(data["messages"]) == 1

    def test_task_from_dict(self):
        """Test Task deserialization."""
        data = {
            "taskId": "task_abc123",
            "sessionId": "sess-789",
            "status": {"status": "completed"},
            "messages": [
                {"role": "user", "parts": [{"type": "text", "text": "Hi"}]}
            ],
        }
        task = Task.from_dict(data)

        assert task.task_id == "task_abc123"
        assert task.session_id == "sess-789"
        assert task.status == TaskStatus.COMPLETED
        assert len(task.messages) == 1


class TestTaskStore:
    """Tests for TaskStore."""

    def test_create_and_get(self):
        """Test creating and getting tasks."""
        store = TaskStore()
        task = Task(session_id="sess-1")
        store.create(task)

        retrieved = store.get(task.task_id)
        assert retrieved is not None
        assert retrieved.task_id == task.task_id

    def test_get_nonexistent(self):
        """Test getting nonexistent task."""
        store = TaskStore()
        task = store.get("nonexistent")
        assert task is None

    def test_update_task(self):
        """Test updating a task."""
        store = TaskStore()
        task = Task(session_id="sess-2")
        store.create(task)

        task.update_status(TaskStatus.WORKING)
        store.update(task)

        retrieved = store.get(task.task_id)
        assert retrieved.status == TaskStatus.WORKING

    def test_delete_task(self):
        """Test deleting a task."""
        store = TaskStore()
        task = Task()
        store.create(task)

        deleted = store.delete(task.task_id)
        assert deleted is True
        assert store.get(task.task_id) is None

    def test_lru_eviction(self):
        """Test LRU eviction when over capacity."""
        store = TaskStore(max_tasks=3)

        for i in range(5):
            task = Task(session_id=f"sess-{i}")
            store.create(task)

        # Only 3 tasks should remain
        assert len(store._tasks) == 3


class TestA2AServer:
    """Tests for A2AServer."""

    @pytest.fixture
    def server(self):
        """Create server instance."""
        server = A2AServer(agent=None, port=8003)
        server.set_agent_card(
            name="Test Agent",
            description="A test agent",
            url="http://localhost:8003",
        )
        return server

    @pytest.mark.asyncio
    async def test_handle_tasks_send(self, server):
        """Test tasks/send handling."""
        request = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tasks/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Hello"}],
                }
            },
        }

        response = await server.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "1"
        assert "result" in response
        assert "task" in response["result"]

    @pytest.mark.asyncio
    async def test_handle_tasks_get(self, server):
        """Test tasks/get handling."""
        # First create a task
        send_request = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tasks/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Hello"}],
                }
            },
        }
        send_response = await server.handle_request(send_request)
        task_id = send_response["result"]["task"]["taskId"]

        # Then get it
        get_request = {
            "jsonrpc": "2.0",
            "id": "2",
            "method": "tasks/get",
            "params": {"taskId": task_id},
        }
        get_response = await server.handle_request(get_request)

        assert get_response["result"]["task"]["taskId"] == task_id

    @pytest.mark.asyncio
    async def test_handle_tasks_cancel(self, server):
        """Test tasks/cancel handling."""
        # Create a task
        send_request = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tasks/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Hello"}],
                }
            },
        }
        send_response = await server.handle_request(send_request)
        task_id = send_response["result"]["task"]["taskId"]

        # Cancel it
        cancel_request = {
            "jsonrpc": "2.0",
            "id": "2",
            "method": "tasks/cancel",
            "params": {"taskId": task_id},
        }
        cancel_response = await server.handle_request(cancel_request)

        assert cancel_response["result"]["task"]["status"]["status"] == "canceled"

    @pytest.mark.asyncio
    async def test_method_not_found(self, server):
        """Test unknown method returns error."""
        request = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "unknown/method",
            "params": {},
        }

        response = await server.handle_request(request)

        assert "error" in response
        assert response["error"]["code"] == -32601

    @pytest.mark.asyncio
    async def test_get_agent_card_json(self, server):
        """Test getting agent card JSON."""
        json_str = await server.get_agent_card_json()
        data = json.loads(json_str)

        assert data["name"] == "Test Agent"
        assert data["url"] == "http://localhost:8003"


class TestJSONRPC:
    """Tests for JSON-RPC types."""

    def test_request_from_dict(self):
        """Test JSONRPCRequest deserialization."""
        data = {
            "jsonrpc": "2.0",
            "id": "123",
            "method": "test.method",
            "params": {"arg": "value"},
        }
        req = JSONRPCRequest.from_dict(data)

        assert req.method == "test.method"
        assert req.id == "123"
        assert req.params == {"arg": "value"}

    def test_response_success(self):
        """Test success response."""
        resp = JSONRPCResponse.success(id="123", result={"data": "test"})

        assert resp.id == "123"
        assert resp.result == {"data": "test"}
        assert resp.error_data is None

        data = resp.to_dict()
        assert data["result"] == {"data": "test"}

    def test_response_error(self):
        """Test error response."""
        resp = JSONRPCResponse.error(id="456", code=-32601, message="Method not found")

        assert resp.error_data is not None
        assert resp.error_data["code"] == -32601

        data = resp.to_dict()
        assert "error" in data
        assert data["error"]["code"] == -32601
