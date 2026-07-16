#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACP Server - Main entry point for ACP communication.

Provides the ACP protocol implementation for Agent-Z.
"""

# 🧠 Decision - 💾 Memory - ACP Server

import argparse
import asyncio
import json
import logging
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from common.logging_manager import get_decision_logger
from agent.acp.session import SessionManager, SessionState, SessionStatus

logger = get_decision_logger(__name__)

PROTOCOL_VERSION = "1.0"


class ACPError(Exception):
    """ACP protocol error."""
    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


class ACPServer:
    """
    ACP Server implementation.

    Handles ACP protocol requests and manages sessions.
    """

    def __init__(
        self,
        agent=None,
        session_manager: Optional[SessionManager] = None,
    ):
        self._agent = agent
        self._session_manager = session_manager or SessionManager()
        self._transport = None
        self._running = False

    @property
    def agent(self):
        """Get the agent."""
        return self._agent

    @agent.setter
    def agent(self, value):
        """Set the agent."""
        self._agent = value

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a JSON-RPC request.

        Args:
            request: JSON-RPC request object

        Returns:
            JSON-RPC response object
        """
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")

        logger.debug(f"Handling request: method={method}, id={request_id}")

        try:
            # Route to handler
            if method == "initialize":
                result = await self._handle_initialize(params)
            elif method == "ping":
                result = await self._handle_ping(params)
            elif method == "session/new":
                result = await self._handle_session_new(params)
            elif method == "session/load":
                result = await self._handle_session_load(params)
            elif method == "session/prompt":
                result = await self._handle_session_prompt(params)
            elif method == "session/cancel":
                result = await self._handle_session_cancel(params)
            elif method == "session/list":
                result = await self._handle_session_list(params)
            elif method == "session/delete":
                result = await self._handle_session_delete(params)
            elif method == "tools/list":
                result = await self._handle_tools_list(params)
            elif method == "fs/read_text_file":
                result = await self._handle_fs_read_text_file(params)
            elif method == "fs/write_text_file":
                result = await self._handle_fs_write_text_file(params)
            else:
                raise ACPError(-32601, f"Method not found: {method}")

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result,
            }
        except ACPError as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "data": e.data,
                },
            }
        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": str(e),
                },
            }

    # Initialize
    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {
                "session": {
                    "supported": True,
                    "resumable": True,
                    "list": True,
                },
                "tools": {
                    "supported": True,
                    "list": True,
                },
                "fs": {
                    "supported": True,
                    "read": True,
                    "write": True,
                },
            },
            "agentInfo": {
                "name": "Agent-Z",
                "version": "1.0.0",
            },
        }

    # Ping
    async def _handle_ping(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ping request."""
        return {"pong": True}

    # Session management
    async def _handle_session_new(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle session/new request."""
        cwd = params.get("cwd")
        model = params.get("model")
        toolsets = params.get("toolsets")
        title = params.get("title")

        session = self._session_manager.create_session(
            cwd=cwd,
            model=model,
            toolsets=toolsets,
            title=title,
        )

        return {
            "sessionId": session.session_id,
            "title": session.title,
        }

    async def _handle_session_load(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle session/load request."""
        session_id = params.get("sessionId")
        if not session_id:
            raise ACPError(-32602, "sessionId is required")

        session = self._session_manager.get_session(session_id)
        if not session:
            raise ACPError(-32602, f"Session not found: {session_id}")

        return {
            "sessionId": session.session_id,
            "history": session.history,
            "title": session.title,
        }

    async def _handle_session_prompt(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle session/prompt request."""
        session_id = params.get("sessionId")
        message = params.get("message", "")
        messages = params.get("messages", [])

        if not session_id:
            raise ACPError(-32602, "sessionId is required")

        session = self._session_manager.get_session(session_id)
        if not session:
            raise ACPError(-32602, f"Session not found: {session_id}")

        # Build full context from messages
        context = {
            "session_id": session_id,
            "cwd": session.cwd,
            "model": session.model,
            "toolsets": session.toolsets,
        }

        # Add messages to history
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            self._session_manager.add_message(session_id, role, content)

        # Add current message
        self._session_manager.add_message(session_id, "user", message)

        # Run agent via chat() interface
        # ponytail: sync-to-async bridge, Agent.chat is async
        response_content = ""
        if self._agent:
            try:
                loop = asyncio.get_event_loop()
                response = loop.run_until_complete(
                    self._agent.chat(message, conversation_history=session.history.copy())
                )
                response_content = getattr(response, "content", str(response))
            except Exception as e:
                logger.error(f"Error running agent: {e}", exc_info=True)
                response_content = f"Error: {e}"

        # Add response to history
        self._session_manager.add_message(session_id, "assistant", response_content)

        return {
            "message": {
                "role": "assistant",
                "content": response_content,
            },
        }

    async def _handle_session_cancel(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle session/cancel request."""
        session_id = params.get("sessionId")

        if session_id:
            self._session_manager.update_session(
                session_id,
                status=SessionStatus.CANCELLED,
            )

        return {"cancelled": True}

    async def _handle_session_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle session/list request."""
        limit = params.get("limit", 50)
        cursor = params.get("cursor")

        sessions = self._session_manager.list_sessions(
            limit=limit,
            cursor=cursor,
        )

        return {
            "sessions": [
                {
                    "sessionId": s.session_id,
                    "title": s.title,
                    "createdAt": s.created_at,
                    "updatedAt": s.updated_at,
                    "cwd": s.cwd,
                }
                for s in sessions
            ],
        }

    async def _handle_session_delete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle session/delete request."""
        session_id = params.get("sessionId")
        if not session_id:
            raise ACPError(-32602, "sessionId is required")

        deleted = self._session_manager.delete_session(session_id)
        return {"deleted": deleted}

    # Tools
    async def _handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request."""
        tools = []

        if self._agent and hasattr(self._agent, "tool_dispatcher"):
            for name, tool in self._agent.tool_dispatcher.tools.items():
                tools.append({
                    "name": name,
                    "description": getattr(tool, "description", ""),
                })

        return {"tools": tools}

    # File system
    async def _handle_fs_read_text_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle fs/read_text_file request."""
        path = params.get("path")
        if not path:
            raise ACPError(-32602, "path is required")

        try:
            file_path = Path(path).expanduser()
            content = file_path.read_text(encoding="utf-8")
            return {"content": content}
        except Exception as e:
            raise ACPError(-32603, f"Failed to read file: {e}")

    async def _handle_fs_write_text_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle fs/write_text_file request."""
        path = params.get("path")
        content = params.get("content", "")

        if not path:
            raise ACPError(-32602, "path is required")

        try:
            file_path = Path(path).expanduser()
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return {"written": True}
        except Exception as e:
            raise ACPError(-32603, f"Failed to write file: {e}")


async def run_stdio_server(agent=None) -> None:
    """Run ACP server with stdio transport."""
    server = ACPServer(agent)

    async def read_loop():
        """Read and process requests from stdin."""
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        writer = asyncio.StreamWriter(asyncio.get_event_loop(), None, None, None)

        while True:
            try:
                line = await asyncio.wait_for(reader.readline(), timeout=1.0)
                if not line:
                    break

                request = json.loads(line.decode("utf-8"))
                response = await server.handle_request(request)
                response_line = json.dumps(response) + "\n"
                sys.stdout.write(response_line)
                sys.stdout.flush()
            except asyncio.TimeoutError:
                continue
            except json.JSONDecodeError as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {e}"},
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()
            except Exception as e:
                logger.error(f"Error in stdio server: {e}", exc_info=True)

    await read_loop()


async def run_http_server(agent=None, host: str = "127.0.0.1", port: int = 8002) -> None:
    """Run ACP server with HTTP transport."""
    try:
        from aiohttp import web
    except ImportError:
        logger.error("aiohttp is required for HTTP transport")
        return

    server = ACPServer(agent)

    async def handle_acp(request):
        """Handle ACP HTTP endpoint."""
        try:
            body = await request.json()
            response = await server.handle_request(body)
            return web.json_response(response)
        except Exception as e:
            logger.error(f"Request handling error: {e}")
            return web.json_response(
                {"error": {"code": -32603, "message": str(e)}},
                status=500,
            )

    app = web.Application()
    app.router.add_post("/acp", handle_acp)
    app.router.add_get("/health", lambda r: web.json_response({"status": "ok"}))

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()

    print(f"ACP HTTP server started on {host}:{port}")

    stop_event = asyncio.Event()

    def signal_handler(sig, frame):
        stop_event.set()

    import signal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await stop_event.wait()
    finally:
        await runner.cleanup()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Agent-Z ACP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport type",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for HTTP transport")
    parser.add_argument("--port", type=int, default=8002, help="Port for HTTP transport")
    args = parser.parse_args()

    if args.transport == "stdio":
        asyncio.run(run_stdio_server())
    else:
        asyncio.run(run_http_server(None, host=args.host, port=args.port))


if __name__ == "__main__":
    main()
