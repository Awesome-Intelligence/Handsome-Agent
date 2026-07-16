#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A Server Implementation.

Provides HTTP server for A2A protocol communication.
"""

# 🧠 Decision - 💾 Memory - A2A Server

import asyncio
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from common.logging_manager import get_decision_logger
from agent.a2a.models import (
    AgentCard,
    JSONRPCRequest,
    JSONRPCResponse,
    Message,
    Part,
    Task,
    TaskStatus,
    TextPart,
    part_from_dict,
)

logger = get_decision_logger("a2a")

PROTOCOL_VERSION = "1.0.0"


class TaskStore:
    """In-memory task store with LRU eviction."""

    def __init__(self, max_tasks: int = 1000):
        self._tasks: Dict[str, Task] = {}
        self._max_tasks = max_tasks
        self._access_order: List[str] = []

    def create(self, task: Task) -> Task:
        """Create a new task."""
        self._tasks[task.task_id] = task
        self._access_order.append(task.task_id)
        self._evict_oldest()
        return task

    def get(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        task = self._tasks.get(task_id)
        if task:
            self._mark_accessed(task_id)
        return task

    def update(self, task: Task) -> None:
        """Update a task."""
        if task.task_id in self._tasks:
            self._tasks[task.task_id] = task
            self._mark_accessed(task.task_id)

    def delete(self, task_id: str) -> bool:
        """Delete a task."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            if task_id in self._access_order:
                self._access_order.remove(task_id)
            return True
        return False

    def list_tasks(self, limit: int = 50) -> List[Task]:
        """List all tasks."""
        return list(self._tasks.values())[:limit]

    def _mark_accessed(self, task_id: str) -> None:
        """Mark a task as accessed (move to end of LRU list)."""
        if task_id in self._access_order:
            self._access_order.remove(task_id)
        self._access_order.append(task_id)

    def _evict_oldest(self) -> None:
        """Evict oldest tasks if over capacity."""
        while len(self._tasks) > self._max_tasks:
            oldest = self._access_order.pop(0) if self._access_order else None
            if oldest and oldest in self._tasks:
                del self._tasks[oldest]


class A2AServer:
    """
    A2A Server implementation.

    Provides HTTP endpoints for the A2A protocol:
    - GET /.well-known/agent.json - Agent Card
    - POST /tasks/send - Send a task
    - GET /tasks/{taskId} - Get task status
    - POST /tasks/{taskId}/cancel - Cancel a task
    - GET /tasks/{taskId}/events - SSE task events
    """

    def __init__(
        self,
        agent=None,
        agent_card: Optional[AgentCard] = None,
        port: int = 8003,
    ):
        self._agent = agent
        self._agent_card = agent_card
        self._port = port
        self._host = "127.0.0.1"
        self._task_store = TaskStore()
        self._running = False
        self._task_events: Dict[str, asyncio.Queue] = {}

    @property
    def agent_card(self) -> Optional[AgentCard]:
        """Get the agent card."""
        return self._agent_card

    @agent_card.setter
    def agent_card(self, value: AgentCard) -> None:
        """Set the agent card."""
        self._agent_card = value

    def set_agent_card(
        self,
        name: str,
        description: str,
        url: str,
        version: str = "1.0.0",
        **kwargs,
    ) -> None:
        """Create and set agent card."""
        self._agent_card = AgentCard(
            name=name,
            description=description,
            url=url,
            version=version,
            **kwargs,
        )

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a JSON-RPC request.

        Args:
            request: JSON-RPC request object

        Returns:
            JSON-RPC response object
        """
        try:
            req = JSONRPCRequest.from_dict(request)
            method = req.method
            params = req.params
            request_id = req.id

            logger.debug(f"A2A request: method={method}, id={request_id}")

            # Route to handler
            if method == "tasks/send":
                result = await self._handle_tasks_send(params)
            elif method == "tasks/get":
                result = await self._handle_tasks_get(params)
            elif method == "tasks/cancel":
                result = await self._handle_tasks_cancel(params)
            elif method == "tasks/sendSubscribe":
                result = await self._handle_tasks_send_subscribe(params)
            else:
                return JSONRPCResponse.error(
                    id=request_id,
                    code=-32601,
                    message=f"Method not found: {method}",
                ).to_dict()

            return JSONRPCResponse.success(id=request_id, result=result).to_dict()

        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)
            return JSONRPCResponse.error(
                id=request.get("id"),
                code=-32603,
                message=str(e),
            ).to_dict()

    async def _handle_tasks_send(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tasks/send request."""
        session_id = params.get("sessionId")
        message_data = params.get("message", {})
        task_id = params.get("taskId")

        # Build message from request
        parts = []
        for p in message_data.get("parts", []):
            parts.append(part_from_dict(p))

        role_str = message_data.get("role", "user")
        message = Message(role=role_str, parts=parts)

        # Get or create task
        if task_id:
            task = self._task_store.get(task_id)
            if not task:
                task = Task(task_id=task_id, session_id=session_id)
        else:
            task = Task(session_id=session_id)

        # Add user message
        task.add_message(message)
        task.update_status(TaskStatus.WORKING)

        # Run agent if available
        response_text = ""
        if self._agent:
            try:
                # Extract text from first user message
                user_text = ""
                for part in parts:
                    if isinstance(part, TextPart):
                        user_text = part.text
                        break

                if hasattr(self._agent, "respond"):
                    response = await self._agent.respond(user_text, {"session_id": session_id})
                    response_text = getattr(response, "content", str(response))
                elif hasattr(self._agent, "run"):
                    response = await self._agent.run(user_text)
                    response_text = getattr(response, "content", str(response))
            except Exception as e:
                logger.error(f"Error running agent: {e}")
                task.update_status(TaskStatus.FAILED, message=str(e))
                response_text = f"Error: {e}"
        else:
            response_text = "Agent not configured. Send tasks to a configured A2A server."

        # Add agent response
        task.add_message(Message(role="agent", parts=[TextPart(response_text)]))
        task.update_status(TaskStatus.COMPLETED)

        # Store task (create if new, update if existing)
        if task.task_id in self._task_store._tasks:
            self._task_store.update(task)
        else:
            self._task_store.create(task)

        return {
            "task": task.to_dict(),
        }

    async def _handle_tasks_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tasks/get request."""
        task_id = params.get("taskId")
        if not task_id:
            raise ValueError("taskId is required")

        task = self._task_store.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        return {
            "task": task.to_dict(),
        }

    async def _handle_tasks_cancel(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tasks/cancel request."""
        task_id = params.get("taskId")
        if not task_id:
            raise ValueError("taskId is required")

        task = self._task_store.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        task.update_status(TaskStatus.CANCELED)
        self._task_store.update(task)

        return {
            "task": task.to_dict(),
        }

    async def _handle_tasks_send_subscribe(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tasks/sendSubscribe request (streaming)."""
        # For streaming, we just return the initial response
        # The actual streaming is done via /tasks/{taskId}/events SSE endpoint
        return await self._handle_tasks_send(params)

    async def get_agent_card_json(self) -> str:
        """Get agent card as JSON string."""
        if self._agent_card:
            return json.dumps(self._agent_card.to_dict(), indent=2)
        else:
            return json.dumps({
                "name": "Agent-Z",
                "description": "A2A compatible agent",
                "url": f"http://{self._host}:{self._port}",
                "version": "1.0.0",
            }, indent=2)

    async def start(self) -> None:
        """Start the A2A HTTP server."""
        try:
            from aiohttp import web
        except ImportError:
            logger.error("aiohttp is required for A2A server")
            return

        app = web.Application()
        app["a2a_server"] = self

        # Agent Card endpoint
        app.router.add_get("/.well-known/agent.json", self._handle_agent_card)
        app.router.add_get("/.well-known/agent.json", self._handle_agent_card)

        # Task endpoints
        app.router.add_post("/tasks/send", self._handle_tasks_send_http)
        app.router.add_post("/tasks/sendSubscribe", self._handle_tasks_send_http)
        app.router.add_get(r"/tasks/{task_id}", self._handle_tasks_get_http)
        app.router.add_post(r"/tasks/{task_id}/cancel", self._handle_tasks_cancel_http)
        app.router.add_get(r"/tasks/{task_id}/events", self._handle_task_events)

        # JSON-RPC endpoint
        app.router.add_post("/", self._handle_jsonrpc)

        self._runner = web.AppRunner(app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self._host, self._port)
        await self._site.start()
        self._running = True

        logger.info(f"A2A server started on {self._host}:{self._port}")

    async def stop(self) -> None:
        """Stop the A2A HTTP server."""
        self._running = False
        if hasattr(self, "_site"):
            await self._site.stop()
        if hasattr(self, "_runner"):
            await self._runner.cleanup()
        logger.info("A2A server stopped")

    # HTTP Handlers

    async def _handle_agent_card(self, request) -> "web.Response":
        """Handle Agent Card request."""
        from aiohttp import web

        json_str = await self.get_agent_card_json()
        return web.Response(
            text=json_str,
            content_type="application/json",
            headers={"Cache-Control": "no-cache"},
        )

    async def _handle_tasks_send_http(self, request) -> "web.Response":
        """Handle tasks/send HTTP request."""
        from aiohttp import web

        try:
            body = await request.json()
            result = await self._handle_tasks_send(body)
            return web.json_response(result)
        except Exception as e:
            logger.error(f"Error in tasks/send: {e}")
            return web.json_response(
                {"error": {"code": -32603, "message": str(e)}},
                status=500,
            )

    async def _handle_tasks_get_http(self, request) -> "web.Response":
        """Handle tasks/get HTTP request."""
        from aiohttp import web

        task_id = request.match_info["task_id"]
        try:
            result = await self._handle_tasks_get({"taskId": task_id})
            return web.json_response(result)
        except ValueError as e:
            return web.json_response(
                {"error": {"code": -32602, "message": str(e)}},
                status=404,
            )
        except Exception as e:
            return web.json_response(
                {"error": {"code": -32603, "message": str(e)}},
                status=500,
            )

    async def _handle_tasks_cancel_http(self, request) -> "web.Response":
        """Handle tasks/cancel HTTP request."""
        from aiohttp import web

        task_id = request.match_info["task_id"]
        try:
            result = await self._handle_tasks_cancel({"taskId": task_id})
            return web.json_response(result)
        except ValueError as e:
            return web.json_response(
                {"error": {"code": -32602, "message": str(e)}},
                status=404,
            )
        except Exception as e:
            return web.json_response(
                {"error": {"code": -32603, "message": str(e)}},
                status=500,
            )

    async def _handle_task_events(self, request) -> "web.StreamResponse":
        """Handle SSE task events."""
        from aiohttp import web

        task_id = request.match_info["task_id"]
        task = self._task_store.get(task_id)

        if not task:
            return web.json_response(
                {"error": {"code": -32602, "message": f"Task not found: {task_id}"}},
                status=404,
            )

        response = web.StreamResponse(
            status=200,
            reason="OK",
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
        await response.prepare(request)

        try:
            # Send current status
            await response.write(f"data: {json.dumps(task.to_dict())}\n\n".encode("utf-8"))

            # For demo, send a completion event after a short delay
            await asyncio.sleep(0.5)
            await response.write(b"data: [DONE]\n\n")

        except asyncio.CancelledError:
            pass
        finally:
            await response.write_eof()

        return response

    async def _handle_jsonrpc(self, request) -> "web.Response":
        """Handle JSON-RPC requests."""
        from aiohttp import web

        try:
            body = await request.json()
            response_dict = await self.handle_request(body)
            return web.json_response(response_dict)
        except Exception as e:
            logger.error(f"Error in JSON-RPC: {e}")
            return web.json_response(
                {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}},
                status=500,
            )


async def run_a2a_server(
    agent=None,
    name: str = "Agent-Z",
    description: str = "A2A compatible agent",
    host: str = "127.0.0.1",
    port: int = 8003,
) -> None:
    """Run A2A server with the given configuration."""
    server = A2AServer(agent=agent, port=port)
    server.set_agent_card(
        name=name,
        description=description,
        url=f"http://{host}:{port}",
        version="1.0.0",
    )

    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║                    Agent-Z A2A Server                    ║
║              Agent-to-Agent Protocol (Google)                  ║
╠══════════════════════════════════════════════════════════════════╣
║  URL: http://{host}:{port}                                      ║
╠══════════════════════════════════════════════════════════════════╣
║  Endpoints:                                                    
║    Agent Card:                                               
║      GET  /.well-known/agent.json                             
║                                                            
║    Tasks:                                                    
║      POST /tasks/send           - Send a task               
║      POST /tasks/sendSubscribe  - Send with streaming         
║      GET  /tasks/{{id}}         - Get task status            
║      POST /tasks/{{id}}/cancel   - Cancel task                
║      GET  /tasks/{{id}}/events   - SSE task events            
║                                                            
║    JSON-RPC:                                                 
║      POST /                   - General JSON-RPC endpoint     
║                                                            
╠══════════════════════════════════════════════════════════════════╣
║  Examples:                                                    
║    curl http://{host}:{port}/.well-known/agent.json            
║    curl -X POST http://{host}:{port}/tasks/send \\             
║      -H "Content-Type: application/json" \\                    
║      -d '{{"message":{{"parts":[{{"type":"text","text":"hi"}}]}}}}'
╚══════════════════════════════════════════════════════════════════╝
🛑 Press Ctrl+C to stop...
""")

    await server.start()

    stop_event = asyncio.Event()

    def signal_handler(sig, frame):
        stop_event.set()

    import signal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await stop_event.wait()
    finally:
        await server.stop()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Agent-Z A2A Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8003, help="Port to listen on")
    parser.add_argument("--name", default="Agent-Z", help="Agent name")
    parser.add_argument(
        "--description",
        default="A2A compatible agent",
        help="Agent description",
    )
    args = parser.parse_args()

    try:
        asyncio.run(run_a2a_server(
            name=args.name,
            description=args.description,
            host=args.host,
            port=args.port,
        ))
    except KeyboardInterrupt:
        print("\n👋 Shutdown complete.")


if __name__ == "__main__":
    main()
