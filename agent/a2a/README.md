# A2A (Agent-to-Agent) Protocol Module

This module provides A2A protocol implementation for multi-agent collaboration.

## Overview

The A2A (Agent-to-Agent) Protocol, developed by Google and 50+ partners, enables
AI agents to communicate with each other regardless of their underlying frameworks.

## Features

- **Agent Card** - Capability discovery mechanism
- **Task Management** - Long-running task coordination
- **Message/Part System** - Rich multi-modal content exchange
- **SSE Streaming** - Real-time task status updates
- **Enterprise Security** - OAuth 2.0 / JWT authentication

## Usage

```python
from agent.a2a import A2AServer, AgentCard

# Create Agent Card
card = AgentCard(
    name="Handsome Agent",
    description="A versatile AI agent",
    url="http://localhost:8003",
)

# Create A2A Server
server = A2AServer(agent, card)
await server.start()

# Or via CLI
python -m agent.a2a.server --port 8003
```

## Protocol Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /.well-known/agent.json` | GET | Agent Card |
| `POST /tasks/send` | POST | Send task |
| `GET /tasks/{taskId}` | GET | Get task status |
| `POST /tasks/{taskId}/cancel` | POST | Cancel task |
| `GET /tasks/{taskId}/events` | GET | SSE task events |

## Core Concepts

1. **AgentCard**: JSON document describing agent capabilities
2. **Task**: Work unit with lifecycle states (submitted → working → completed)
3. **Message**: Conversation unit with role and Parts
4. **Part**: Content block (text, image, file, etc.)
