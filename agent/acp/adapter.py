#!/usr/bin/env python3
# 🧠 Decision - ACP 协议实现
# 实现 agent-client-protocol 的 acp.Agent 接口

from __future__ import annotations

import asyncio
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

import acp
from acp.schema import (
    AgentCapabilities,
    AuthenticateResponse,
    ClientCapabilities,
    EmbeddedResourceContentBlock,
    ImageContentBlock,
    Implementation,
    InitializeResponse,
    ListSessionsResponse,
    LoadSessionResponse,
    McpServerHttp,
    McpServerSse,
    McpServerStdio,
    NewSessionResponse,
    PromptCapabilities,
    PromptResponse,
    ResourceContentBlock,
    SessionCapabilities,
    SessionForkCapabilities,
    SessionInfo,
    SessionListCapabilities,
    SessionResumeCapabilities,
    StopReason,
    TextContentBlock,
)

from agent.acp.session import SessionManager, SessionStatus
from agent.rails.edit_approval import EditApprovalRail, set_edit_approval_requester
from agent.rails import get_rail_registry
from common.logging_manager import get_decision_logger, suppress_library_logs

logger = get_decision_logger("adapter")


def _build_slash_commands() -> dict[str, str]:
    return {
        "help": "Show available commands",
        "model": "Show or change current model",
        "tools": "List available tools",
        "context": "Show conversation context info",
        "reset": "Clear conversation history",
        "compact": "Compress conversation context",
        "version": "Show Agent-Z version",
    }


def _build_advertised_commands() -> tuple[dict, ...]:
    return (
        {"name": "help", "description": "List available commands"},
        {"name": "model", "description": "Show current model and provider, or switch models", "input_hint": "model name to switch to"},
        {"name": "tools", "description": "List available tools with descriptions"},
        {"name": "context", "description": "Show conversation message counts by role"},
        {"name": "reset", "description": "Clear conversation history"},
        {"name": "compact", "description": "Compress conversation context"},
        {"name": "version", "description": "Show Agent-Z version"},
    )


class AgentZACPAgent(acp.Agent):
    """ACP Agent implementation wrapping Agent-Z AIAgent."""

    _ADVERTISED_COMMANDS = _build_advertised_commands()
    _MODE_DEFAULT = "default"
    _MODE_ACCEPT_EDITS = "accept_edits"
    _MODE_DONT_ASK = "dont_ask"
    _MODE_TO_EDIT_APPROVAL = {
        _MODE_DEFAULT: "ask",
        _MODE_ACCEPT_EDITS: "workspace_session",
        _MODE_DONT_ASK: "session",
    }

    def __init__(self, agent=None, session_manager: Optional[SessionManager] = None):
        super().__init__()
        self._agent = agent
        self._conn: Optional[acp.Client] = None
        self._sessions = session_manager or SessionManager()
        self._running_sessions: set = set()
        self._session_modes: dict[str, str] = {}
        self._rail_registry = get_rail_registry()

    # ---- Connection lifecycle -----------------------------------------------

    def on_connect(self, conn: acp.Client) -> None:
        self._conn = conn
        set_edit_approval_requester(self._make_approval_requester(conn))
        logger.info("ACP client connected")

    def _make_approval_requester(self, conn: acp.Client):
        """Build the approval callback that sends request_permission to the ACP client."""
        async def request_approval(proposal) -> bool:
            from acp.schema import PermissionOption, PermissionOptionKind, ToolCallUpdate

            tool_call = ToolCallUpdate(
                tool_name=proposal.tool_name,
                input=proposal.arguments,
            )
            options = [
                PermissionOption(option_id="allow_once", kind=PermissionOptionKind.ALLOW_ONCE, name="Allow once"),
                PermissionOption(option_id="allow_session", kind=PermissionOptionKind.ALLOW_ALWAYS, name="Allow for session"),
                PermissionOption(option_id="deny", kind=PermissionOptionKind.REJECT_ONCE, name="Deny"),
            ]
            session_id = next(iter(self._sessions._sessions), "default")
            try:
                resp = await asyncio.wait_for(
                    conn.request_permission(options, session_id, tool_call),
                    timeout=120.0,
                )
                return resp.allowed if resp else False
            except asyncio.TimeoutError:
                return False
            except Exception as exc:
                logger.warning("request_permission failed: %s", exc)
                return False

        return request_approval

    def _register_session_rails(self, session_id: str) -> None:
        """Register EditApprovalRail for a session."""
        if not hasattr(self._rail_registry, "get_rails"):
            return
        existing = self._rail_registry.get_rails(session_id)
        if any(isinstance(r, EditApprovalRail) for r in existing):
            return
        self._rail_registry.register(session_id, EditApprovalRail(session_id))

    # ---- ACP Agent interface ------------------------------------------------

    async def initialize(
        self,
        protocol_version: int | None = None,
        client_capabilities: ClientCapabilities | None = None,
        client_info: Implementation | None = None,
        **kwargs: Any,
    ) -> InitializeResponse:
        resolved = protocol_version if isinstance(protocol_version, int) else acp.PROTOCOL_VERSION
        client_name = client_info.name if client_info else "unknown"
        logger.info("Initialize from %s (protocol v%s)", client_name, resolved)

        return InitializeResponse(
            protocol_version=acp.PROTOCOL_VERSION,
            agent_info=Implementation(name="agent-z", version="1.0.0"),
            agent_capabilities=AgentCapabilities(
                load_session=True,
                prompt_capabilities=PromptCapabilities(image=True),
                session_capabilities=SessionCapabilities(
                    fork=SessionForkCapabilities(),
                    list=SessionListCapabilities(),
                    resume=SessionResumeCapabilities(),
                ),
            ),
            auth_methods=[],
        )

    async def authenticate(self, method_id: str, **kwargs: Any) -> AuthenticateResponse | None:
        return AuthenticateResponse(success=True)

    async def new_session(
        self,
        cwd: str,
        mcp_servers: list[McpServerHttp | McpServerSse | McpServerStdio] | None = None,
        **kwargs: Any,
    ) -> NewSessionResponse:
        session = self._sessions.create_session(cwd=cwd)
        self._session_modes[session.session_id] = self._MODE_DEFAULT
        self._register_session_rails(session.session_id)
        logger.info("new_session %s cwd=%s", session.session_id, cwd)
        return NewSessionResponse(session=SessionInfo(session_id=session.session_id, cwd=cwd))

    async def load_session(
        self,
        cwd: str,
        session_id: str,
        mcp_servers: list[McpServerHttp | McpServerSse | McpServerStdio] | None = None,
        **kwargs: Any,
    ) -> LoadSessionResponse | None:
        state = self._sessions.get_session(session_id)
        if state is None:
            return None
        self._session_modes.setdefault(session_id, self._MODE_DEFAULT)
        self._register_session_rails(session_id)
        return LoadSessionResponse(session=SessionInfo(session_id=session_id, cwd=state.cwd or cwd))

    async def resume_session(
        self,
        cwd: str,
        session_id: str,
        mcp_servers: list[McpServerHttp | McpServerSse | McpServerStdio] | None = None,
        **kwargs: Any,
    ) -> PromptResponse:
        state = self._sessions.get_session(session_id)
        if state is None:
            return PromptResponse(stop_reason=StopReason.END_TURN)
        # ponytail: replay history to rebuild agent internal state (tool tracking, curator memory).
        # Agent-Z doesn't yet expose a replay API — for now just log it.
        logger.info("resume_session %s with %d messages", session_id, len(state.history))
        return PromptResponse(stop_reason=StopReason.END_TURN)

    async def list_sessions(
        self,
        cursor: str | None = None,
        cwd: str | None = None,
        **kwargs: Any,
    ) -> ListSessionsResponse:
        sessions = self._sessions.list_sessions(cursor=cursor)
        return ListSessionsResponse(
            sessions=[SessionInfo(session_id=s.session_id, cwd=s.cwd or "") for s in sessions],
            next_cursor=None,
        )

    async def cancel(self, session_id: str, **kwargs: Any) -> None:
        self._running_sessions.discard(session_id)
        self._sessions.update_session(session_id, status=SessionStatus.CANCELLED)

    async def fork_session(
        self,
        cwd: str,
        session_id: str,
        mcp_servers: list[McpServerHttp | McpServerSse | McpServerStdio] | None = None,
        **kwargs: Any,
    ) -> NewSessionResponse:
        original = self._sessions.get_session(session_id)
        new_session = self._sessions.create_session(cwd=cwd)
        if original:
            for msg in original.history:
                self._sessions.add_message(new_session.session_id, msg["role"], msg["content"])
        return NewSessionResponse(session=SessionInfo(session_id=new_session.session_id, cwd=cwd))

    async def prompt(
        self,
        prompt: list[TextContentBlock | ImageContentBlock | ResourceContentBlock | EmbeddedResourceContentBlock],
        session_id: str,
        **kwargs: Any,
    ) -> PromptResponse:
        state = self._sessions.get_session(session_id)
        if state is None:
            return PromptResponse(stop_reason=StopReason.END_TURN)

        # Extract text
        user_text = ""
        for block in prompt:
            if isinstance(block, TextContentBlock):
                user_text += block.text
            elif isinstance(block, EmbeddedResourceContentBlock):
                res = getattr(block, "resource", None)
                if res and hasattr(res, "text"):
                    user_text += res.text

        if not user_text.strip():
            return PromptResponse(stop_reason=StopReason.END_TURN)

        # Slash command handling
        if isinstance(user_text, str) and user_text.startswith("/"):
            response_text = self._handle_slash(user_text, session_id)
            if response_text is not None:
                if self._conn:
                    await self._conn.session_update(session_id, acp.update_agent_message_text(response_text))
                return PromptResponse(stop_reason=StopReason.END_TURN)

        self._running_sessions.add(session_id)
        self._sessions.add_message(session_id, "user", user_text)

        try:
            if self._agent:
                response = await self._agent.chat(user_text)
                response_text = getattr(response, "content", str(response))
            else:
                response_text = "Agent not configured. Run 'agentz acp' with a loaded agent."
        except Exception as exc:
            logger.error("prompt error: %s", exc)
            response_text = f"Error: {exc}"
        finally:
            self._running_sessions.discard(session_id)

        self._sessions.add_message(session_id, "assistant", response_text)
        if self._conn:
            await self._conn.session_update(session_id, acp.update_agent_message_text(response_text))

        return PromptResponse(stop_reason=StopReason.END_TURN)

    async def set_session_mode(self, mode_id: str, session_id: str, **kwargs: Any) -> None:
        self._session_modes[session_id] = mode_id
        policy = self._MODE_TO_EDIT_APPROVAL.get(mode_id, "ask")
        logger.info("session %s mode=%s policy=%s", session_id, mode_id, policy)
        if self._conn:
            from acp.schema import CurrentModeUpdate
            await self._conn.session_update(session_id, CurrentModeUpdate(current_mode_id=mode_id))

    async def set_session_model(self, model_id: str, session_id: str, **kwargs: Any) -> None:
        pass  # ponytail: P4 multi-model

    async def set_config_option(self, config_id: str, session_id: str, value: str | bool, **kwargs: Any) -> None:
        pass

    async def close_session(self, session_id: str, **kwargs: Any) -> None:
        self._sessions.delete_session(session_id)

    # ---- Slash command handler ----------------------------------------------

    def _handle_slash(self, text: str, session_id: str) -> str | None:
        parts = text.strip().split(maxsplit=1)
        cmd = parts[0].lower()

        handlers = {
            "/help": lambda: "\n".join(f"/{k}: {v}" for k, v in _build_slash_commands().items()),
            "/version": lambda: "Agent-Z 1.0.0",
            "/tools": lambda: "Tools are available through the agent.",
            "/context": lambda: self._sessions.get_session(session_id) and f"Messages: {len(self._sessions.get_session(session_id).history)}" or "No session.",
            "/reset": lambda: "History cleared." if self._sessions.clear_history(session_id) else "Session not found.",
            "/compact": lambda: "Context compression not yet available.",
        }

        if cmd in handlers:
            return handlers[cmd]()  # type: ignore
        return None


async def _async_main() -> None:
    _setup_logging()

    # Build and run agent
    agent = None
    try:
        from agent.agent import create_agent_from_config
        agent = create_agent_from_config()
    except Exception as exc:
        logger.warning("Could not create agent: %s", exc)

    acp_agent = AgentZACPAgent(agent)

    try:
        await acp.run_agent(acp_agent, use_unstable_protocol=True)
    except KeyboardInterrupt:
        logger.info("Shutting down")
    except Exception:
        logger.exception("ACP agent crashed")
        sys.exit(1)


def _setup_logging() -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    suppress_library_logs()


if __name__ == "__main__":
    asyncio.run(_async_main())
