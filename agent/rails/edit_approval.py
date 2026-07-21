# 🧠 Decision - ✅ Task - ACP Edit Approval Rail

"""
ACP Edit Approval — intercepts file-mutating tool calls and requests
user approval via the ACP connection (ContextVar bridge).
"""

from __future__ import annotations

import asyncio
import re
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from agent.rails.rail import Rail, RailResult, RailPriority


# ---- ContextVar bridge ----

EditApprovalRequester = Callable[["EditProposal"], bool | asyncio.Event]
_EDIT_APPROVAL_REQUESTER: ContextVar[EditApprovalRequester | None] = ContextVar(
    "_EDIT_APPROVAL_REQUESTER", default=None
)


def set_edit_approval_requester(fn: EditApprovalRequester | None) -> None:
    _EDIT_APPROVAL_REQUESTER.set(fn)


def get_edit_approval_requester() -> EditApprovalRequester | None:
    return _EDIT_APPROVAL_REQUESTER.get()


# ---- Proposal ----

@dataclass(frozen=True)
class EditProposal:
    tool_name: str
    path: str
    old_text: str | None
    new_text: str
    arguments: dict[str, Any]


# ---- Helpers ----

SENSITIVE_NAMES = {".env", ".env.local", ".env.production", "id_rsa", "id_ed25519"}


def _is_sensitive(path: str) -> bool:
    parts = Path(path).expanduser().parts
    return ".ssh" in {p.lower() for p in parts} or Path(path).name.lower() in SENSITIVE_NAMES


def _proposal_for_write_file(args: dict[str, Any]) -> EditProposal:
    path = str(args.get("path", ""))
    content = args.get("content", "")
    old_text = None
    p = Path(path).expanduser()
    if p.exists():
        try:
            old_text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
    return EditProposal(tool_name="write_file", path=path, old_text=old_text, new_text=str(content), arguments=dict(args))


def _proposal_for_patch(args: dict[str, Any]) -> EditProposal | None:
    path = str(args.get("path", ""))
    mode = args.get("mode", "replace")
    if mode == "replace":
        old_string = args.get("old_string", "")
        new_string = args.get("new_string", "")
    elif mode == "patch":
        # ponytail: only capture first path in multi-file patch
        patch_body = args.get("patch", "")
        paths = re.findall(r"^\*\*\*\s+(?:Update|Add|Delete)\s+File:\s*(.+)$", patch_body, re.MULTILINE)
        if not paths:
            return None
        path = paths[0]
        old_string = new_string = patch_body
    else:
        return None
    old_text = None
    p = Path(path).expanduser()
    if p.exists():
        try:
            old_text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
    return EditProposal(tool_name="patch", path=path, old_text=old_text, new_text=new_string, arguments=dict(args))


def build_edit_proposal(tool_name: str, args: dict[str, Any]) -> EditProposal | None:
    if tool_name == "write_file":
        return _proposal_for_write_file(args)
    if tool_name == "patch":
        return _proposal_for_patch(args)
    return None


# ---- Rail ----

MUTATING_TOOLS = {"write_file", "patch"}


class EditApprovalRail(Rail):
    """Intercepts file-mutating tool calls and requests ACP user approval."""

    priority = RailPriority.HIGH  # Run early, before other rails

    def __init__(self, session_id: str):
        super().__init__(session_id)
        self._approved_paths: set[str] = set()

    async def before_tool_call(self, tool_name: str, args: dict[str, Any]) -> RailResult | None:
        if tool_name not in MUTATING_TOOLS:
            return None

        proposal = build_edit_proposal(tool_name, args)
        if proposal is None:
            return None

        # Auto-approve non-sensitive paths
        if not _is_sensitive(proposal.path):
            return None

        requester = get_edit_approval_requester()
        if requester is None:
            # No ACP connection — auto-approve with warning
            return RailResult(allowed=True)

        try:
            result = await asyncio.wait_for(
                asyncio.create_task(requester(proposal)) if asyncio.iscoroutinefunction(requester)
                else asyncio.get_event_loop().run_in_executor(None, lambda: requester(proposal)),
                timeout=120.0,
            )
            if asyncio.iscoroutine(result):
                result = await result
            allowed = bool(result)
        except asyncio.TimeoutError:
            return RailResult(allowed=False, error="Edit approval timed out (120s)")
        except Exception as exc:
            return RailResult(allowed=False, error=f"Edit approval error: {exc}")

        return RailResult(allowed=allowed, error=None if allowed else "edit denied")
