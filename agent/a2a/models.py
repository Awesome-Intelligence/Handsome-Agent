#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A Protocol Data Models.

Implements the core data types for the A2A (Agent-to-Agent) protocol.
"""

# 🧠 Decision - 💾 Memory - A2A Models

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

# 统一状态枚举 - 从 agent.state 导入
# 不要在此文件重复定义状态，请使用 agent.state.TaskStatus
from agent.state import TaskStatus


class MessageRole(str, Enum):
    """Message role enumeration."""
    USER = "user"
    AGENT = "agent"


# ---------------------------------------------------------------------------
# Agent Card
# ---------------------------------------------------------------------------


@dataclass
class AgentSkill:
    """Skill exposed by an agent."""
    id: str
    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentAuthentication:
    """Authentication configuration for an agent."""
    schemes: List[str] = field(default_factory=list)  # e.g., ["Bearer", "Basic"]
    credentials: Optional[str] = None  # For basic auth


@dataclass
class AgentCapabilities:
    """Capabilities supported by an agent."""
    streaming: bool = True
    push_notifications: bool = False
    state_transition_rules: bool = False
    arm_agents: bool = False
    streaming_timeout_seconds: Optional[int] = 30


@dataclass
class AgentCard:
    """
    Agent Card - capability discovery document.

    This is the core mechanism for agents to advertise their capabilities
    to other agents. It's hosted at /.well-known/agent.json.

    Example:
        {
            "name": "Agent-Z",
            "description": "A versatile AI agent",
            "url": "http://localhost:8003",
            "version": "1.0.0",
            "capabilities": {...},
            "skills": [...]
        }
    """
    name: str
    description: str
    url: str
    version: str = "1.0.0"
    provider: Optional[str] = None
    documentation_url: Optional[str] = None
    capabilities: AgentCapabilities = field(default_factory=AgentCapabilities)
    authentication: Optional[AgentAuthentication] = None
    skills: List[AgentSkill] = field(default_factory=list)
    default_input_modes: List[str] = field(default_factory=lambda: ["text"])
    default_output_modes: List[str] = field(default_factory=lambda: ["text"])

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "provider": self.provider,
            "documentationUrl": self.documentation_url,
            "capabilities": {
                "streaming": self.capabilities.streaming,
                "pushNotifications": self.capabilities.push_notifications,
                "stateTransitionRules": self.capabilities.state_transition_rules,
                "armAgents": self.capabilities.arm_agents,
                "streamingTimeoutSeconds": self.capabilities.streaming_timeout_seconds,
            },
            "authentication": {
                "schemes": self.authentication.schemes if self.authentication else [],
            } if self.authentication else None,
            "skills": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "inputSchema": s.input_schema,
                    "outputSchema": s.output_schema,
                }
                for s in self.skills
            ],
            "defaultInputModes": self.default_input_modes,
            "defaultOutputModes": self.default_output_modes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentCard":
        """Create from dictionary."""
        caps_data = data.get("capabilities", {})
        caps = AgentCapabilities(
            streaming=caps_data.get("streaming", True),
            push_notifications=caps_data.get("pushNotifications", False),
            state_transition_rules=caps_data.get("stateTransitionRules", False),
            arm_agents=caps_data.get("armAgents", False),
            streaming_timeout_seconds=caps_data.get("streamingTimeoutSeconds", 30),
        )

        auth_data = data.get("authentication")
        auth = None
        if auth_data:
            auth = AgentAuthentication(
                schemes=auth_data.get("schemes", []),
                credentials=auth_data.get("credentials"),
            )

        skills = [
            AgentSkill(
                id=s.get("id", ""),
                name=s.get("name", ""),
                description=s.get("description", ""),
                input_schema=s.get("inputSchema", {}),
                output_schema=s.get("outputSchema", {}),
            )
            for s in data.get("skills", [])
        ]

        return cls(
            name=data["name"],
            description=data["description"],
            url=data["url"],
            version=data.get("version", "1.0.0"),
            provider=data.get("provider"),
            documentation_url=data.get("documentationUrl"),
            capabilities=caps,
            authentication=auth,
            skills=skills,
            default_input_modes=data.get("defaultInputModes", ["text"]),
            default_output_modes=data.get("defaultOutputModes", ["text"]),
        )


# ---------------------------------------------------------------------------
# Parts (Content Blocks)
# ---------------------------------------------------------------------------


@dataclass
class Part:
    """Base class for content parts."""
    type: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {"type": self.type}


@dataclass
class TextPart(Part):
    """Text content part."""
    text: str = ""

    def __init__(self, text: str = ""):
        super().__init__(type="text")
        self.text = text

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, "text": self.text}


@dataclass
class DataPart(Part):
    """Structured data content part."""
    data: Dict[str, Any] = field(default_factory=dict)
    mime_type: str = "application/json"

    def __init__(self, data: Dict[str, Any], mime_type: str = "application/json"):
        super().__init__(type="data")
        self.data = data
        self.mime_type = mime_type

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, "data": self.data, "mimeType": self.mime_type}


@dataclass
class FilePart(Part):
    """File reference content part."""
    name: str = ""
    mime_type: str = "application/octet-stream"
    uri: str = ""
    bytes: Optional[int] = None

    def __init__(
        self,
        name: str = "",
        mime_type: str = "application/octet-stream",
        uri: str = "",
        bytes: Optional[int] = None,
    ):
        super().__init__(type="file")
        self.name = name
        self.mime_type = mime_type
        self.uri = uri
        self.bytes = bytes

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": self.type,
            "name": self.name,
            "mimeType": self.mime_type,
            "uri": self.uri,
        }
        if self.bytes is not None:
            result["bytes"] = self.bytes
        return result


@dataclass
class ImagePart(Part):
    """Image content part."""
    url: str = ""
    detail: str = "low"  # "low", "high", "auto"

    def __init__(self, url: str = "", detail: str = "low"):
        super().__init__(type="image")
        self.url = url
        self.detail = detail

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, "url": self.url, "detail": self.detail}


def part_from_dict(data: Dict[str, Any]) -> Part:
    """Create Part from dictionary."""
    part_type = data.get("type", "text")

    if part_type == "text":
        return TextPart(text=data.get("text", ""))
    elif part_type == "data":
        return DataPart(
            data=data.get("data", {}),
            mime_type=data.get("mimeType", "application/json"),
        )
    elif part_type == "file":
        return FilePart(
            name=data.get("name", ""),
            mime_type=data.get("mimeType", "application/octet-stream"),
            uri=data.get("uri", ""),
            bytes=data.get("bytes"),
        )
    elif part_type == "image":
        return ImagePart(
            url=data.get("url", ""),
            detail=data.get("detail", "low"),
        )
    else:
        # Default to text part
        return TextPart(text=str(data))


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------


@dataclass
class Message:
    """
    Message sent between agents.

    Contains role (who sent it) and a list of Parts (the content).
    """
    role: MessageRole
    parts: List[Part] = field(default_factory=list)
    message_id: Optional[str] = None
    parent_id: Optional[str] = None  # For threading

    def __init__(
        self,
        role: Union[str, MessageRole],
        parts: Optional[List[Part]] = None,
        message_id: Optional[str] = None,
        parent_id: Optional[str] = None,
    ):
        if isinstance(role, str):
            role = MessageRole(role)
        self.role = role
        self.parts = parts or []
        self.message_id = message_id or f"msg_{uuid.uuid4().hex[:16]}"
        self.parent_id = parent_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role.value,
            "parts": [p.to_dict() for p in self.parts],
            "messageId": self.message_id,
            "parentId": self.parent_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        role = MessageRole(data.get("role", "user"))
        parts = [part_from_dict(p) for p in data.get("parts", [])]
        return cls(
            role=role,
            parts=parts,
            message_id=data.get("messageId"),
            parent_id=data.get("parentId"),
        )

    @classmethod
    def create_text(cls, text: str, role: Union[str, MessageRole] = MessageRole.USER) -> "Message":
        """Create a simple text message."""
        if isinstance(role, str):
            role = MessageRole(role)
        return cls(role=role, parts=[TextPart(text=text)])


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


@dataclass
class TaskStatusUpdate:
    """Task status update event."""
    timestamp: float = field(default_factory=time.time)
    status: TaskStatus = TaskStatus.SUBMITTED
    message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "timestamp": self.timestamp,
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
        }
        if self.message:
            result["message"] = self.message
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class Task:
    """
    Task - the core unit of work in A2A.

    A task has a lifecycle with status transitions:
    submitted → working → completed/failed/canceled

    Or for tasks requiring more input:
    submitted → working → input-required → working → completed
    """
    task_id: str
    session_id: Optional[str] = None
    status: TaskStatus = TaskStatus.SUBMITTED
    messages: List[Message] = field(default_factory=list)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)  # Generated files/data
    status_history: List[TaskStatusUpdate] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def __init__(
        self,
        task_id: Optional[str] = None,
        session_id: Optional[str] = None,
        status: TaskStatus = TaskStatus.SUBMITTED,
        messages: Optional[List[Message]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.task_id = task_id or f"task_{uuid.uuid4().hex[:16]}"
        self.session_id = session_id
        self.status = status
        self.messages = messages or []
        self.artifacts = []
        self.status_history = [
            TaskStatusUpdate(status=status, timestamp=time.time())
        ]
        self.metadata = metadata or {}
        self.created_at = time.time()
        self.updated_at = time.time()

    def update_status(self, new_status: TaskStatus, message: Optional[str] = None) -> None:
        """Update task status."""
        self.status = new_status
        self.updated_at = time.time()
        self.status_history.append(
            TaskStatusUpdate(status=new_status, message=message)
        )

    def add_message(self, message: Message) -> None:
        """Add a message to the task."""
        self.messages.append(message)
        self.updated_at = time.time()

    def add_artifact(self, artifact: Dict[str, Any]) -> None:
        """Add an artifact to the task."""
        self.artifacts.append(artifact)
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "taskId": self.task_id,
            "sessionId": self.session_id,
            "status": {
                "status": self.status.value,
                "timestamp": self.status_history[-1].timestamp if self.status_history else time.time(),
            },
            "messages": [m.to_dict() for m in self.messages],
            "artifacts": self.artifacts,
            "metadata": self.metadata,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create Task from dictionary."""
        status_data = data.get("status", {})
        status_str = status_data.get("status", "submitted")
        try:
            status = TaskStatus(status_str)
        except ValueError:
            status = TaskStatus.SUBMITTED

        messages = [
            Message.from_dict(m) for m in data.get("messages", [])
        ]

        task = cls(
            task_id=data.get("taskId"),
            session_id=data.get("sessionId"),
            status=status,
            messages=messages,
            metadata=data.get("metadata", {}),
        )
        task.artifacts = data.get("artifacts", [])
        task.created_at = data.get("createdAt", time.time())
        task.updated_at = data.get("updatedAt", time.time())
        return task


# ---------------------------------------------------------------------------
# JSON-RPC Types
# ---------------------------------------------------------------------------


@dataclass
class JSONRPCRequest:
    """JSON-RPC 2.0 request."""
    method: str
    params: Dict[str, Any] = field(default_factory=dict)
    id: Optional[Union[str, int]] = None
    jsonrpc: str = "2.0"

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
            "params": self.params,
        }
        if self.id is not None:
            result["id"] = self.id
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JSONRPCRequest":
        return cls(
            method=data["method"],
            params=data.get("params", {}),
            id=data.get("id"),
            jsonrpc=data.get("jsonrpc", "2.0"),
        )


@dataclass
class JSONRPCResponse:
    """JSON-RPC 2.0 response."""
    id: Optional[Union[str, int]] = None
    result: Optional[Dict[str, Any]] = None
    error_data: Optional[Dict[str, Any]] = None
    jsonrpc: str = "2.0"

    def to_dict(self) -> Dict[str, Any]:
        result = {"jsonrpc": self.jsonrpc}
        if self.id is not None:
            result["id"] = self.id
        if self.error_data:
            result["error"] = self.error_data
        else:
            result["result"] = self.result
        return result

    @classmethod
    def success(cls, id: Optional[Union[str, int]], result: Dict[str, Any]) -> "JSONRPCResponse":
        return cls(id=id, result=result)

    @classmethod
    def error(cls, id: Optional[Union[str, int]], code: int, message: str) -> "JSONRPCResponse":
        return cls(
            id=id,
            error_data={"code": code, "message": message},
        )
