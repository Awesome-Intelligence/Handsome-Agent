"""Gateway lifecycle guard for cron job creation.

🚪 Access - 🔧 System - Hard-block on bootstrap self-disruption
🧠 Decision - ⏰ Scheduler - Lifecycle safety

Ported from Hermes ``cron/lifecycle_guard.py``. An agent running inside
a gateway can schedule a cron job that calls e.g.
``handsome gateway restart``. When the cron fires, the gateway dies,
the supervisor revives it, auto-resume picks up the offending session,
and the resumed turn re-runs the same logic — a SIGTERM-respawn loop
until manually broken.

This module rejects cron job specs whose prompt or script contains a
direct shell-level gateway-lifecycle command. It is enforced at
``cron.jobs.create_job`` so it fires on every job-creation path: the
``handsome cron create`` CLI subcommand AND any future model tool that
calls ``create_job`` directly, bypassing the CLI layer.

The pattern is intentionally command-shaped: it anchors on a concrete
command identifier (``handsome gateway``, ``launchctl ... hermes-gateway``,
``systemctl ... hermes-gateway``, ``pkill`` against the gateway) so it
cannot fire on prose. A cron ``prompt`` is fed to a future LLM, not a
shell, so an over-broad substring match on English would produce a high
false-positive rate without preventing the actual foot-gun.

This is a defence-in-depth layer. The agent's terminal tool blocks these
commands at *execution* time when inside a gateway, and
``handsome gateway stop|restart`` refuse to self-target. Blocking at
*creation* time as well means the agent gets an immediate, informative
rejection instead of scheduling a job that will only fail (silently)
when it fires.
"""

# Copyright © 2026 Agent-Z Contributors.
# Licensed under the MIT license. See LICENSE for details.

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


class GatewayLifecycleBlocked(ValueError):
    """Raised when a cron job spec contains a gateway-lifecycle command."""


# Shell-level command shapes that target the gateway lifecycle. Each
# branch is anchored on a concrete command identifier so a match can
# only fire on actual shell-command-shaped strings, not on prose.
#
# Branches:
#   A: `handsome gateway restart|stop` — canonical foot-gun.
#   B: launchctl ops on a hermes-gateway label.
#   C: systemctl ops on a hermes-gateway unit.
#   D: pkill / kill targeting the hermes gateway process (both token
#      orders because real reproductions show both).
_GATEWAY_LIFECYCLE_PATTERN = re.compile(
    r"(?i)"
    # Branch A
    r"(?:handsome\s+gateway\s+(?:restart|stop))"
    # Branch B — launchctl
    r"|(?:launchctl\s+(?:kickstart|unload|load|stop|restart)\b[^\n]*\b"
    r"hermes[.\-]?gateway)"
    # Branch C — systemctl
    r"|(?:systemctl\s+(?:-\S+\s+)*(?:restart|stop|start)\b[^\n]*\b"
    r"hermes[.\-]?gateway)"
    # Branch D — pkill / kill
    r"|(?:p?kill\b[^\n]*\bhermes\b[^\n]*\bgateway)"
    r"|(?:p?kill\b[^\n]*\bgateway\b[^\n]*\bhermes)"
)


def contains_gateway_lifecycle_command(text: str) -> bool:
    """Return True if *text* contains a gateway lifecycle command pattern."""
    if not text:
        return False
    return bool(_GATEWAY_LIFECYCLE_PATTERN.search(text))


def _resolve_script_path(script_path: str) -> Path:
    """Resolve a cron ``script`` value the way the scheduler does.

    The scheduler resolves a bare/relative script path under
    ``<HANDSOME_HOME>/scripts/`` and only accepts absolute paths as-is.
    We mirror that here so the guard scans the file that will actually
    run — otherwise a job whose script lives at the scheduler's real
    location but is passed as the bare name would scan prompt-only
    content and let the command through.
    """
    from common.config import get_handsome_home

    raw = Path(script_path).expanduser()
    if raw.is_absolute():
        return raw
    return get_handsome_home() / "scripts" / raw


def _read_script_for_scanning(script_path: str) -> str:
    """Read a script file for lifecycle-pattern scanning.

    Decodes with ``errors="replace"`` so binary or non-UTF-8 content does
    not silently bypass the check — a plain text-mode read raises
    ``UnicodeDecodeError`` on such files, and swallowing that error
    would let an attacker hide the command in binary noise.
    """
    try:
        return _resolve_script_path(script_path).read_bytes().decode(
            "utf-8", errors="replace"
        )
    except OSError:
        return ""


def check_gateway_lifecycle(
    prompt: Optional[str],
    script: Optional[str] = None,
) -> None:
    """Raise ``GatewayLifecycleBlocked`` if *prompt* or *script* matches.

    ``prompt`` is scanned directly. ``script``, when supplied, is read
    from disk and concatenated for the scan. Both are considered
    together so a job cannot slip through by splitting the command
    across the prompt and the script.
    """
    combined = prompt or ""
    if script:
        script_text = _read_script_for_scanning(script)
        if script_text:
            combined = f"{combined}\n{script_text}"

    if contains_gateway_lifecycle_command(combined):
        raise GatewayLifecycleBlocked(
            "Blocked: cron job contains a gateway lifecycle command "
            "(restart/stop/kill). Run `handsome gateway restart` from a "
            "shell outside the running gateway instead."
        )
