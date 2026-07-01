"""Skill provenance tracking — record and query skill write origins.

This module tracks where skills originate (agent-created, user-created,
hub-installed, restored) and manages the background-review context flag.

Provenance data is persisted to ~/.handsome_agent/.provenance/ as JSON files.

Usage:
    from agent.skill_provenance import (
        SkillSource,
        mark_skill_provenance,
        get_skill_provenance,
        list_skills_by_source,
        is_background_review,
    )

    # Mark a skill as agent-created
    mark_skill_provenance("my_skill", SkillSource.AGENT_CREATED, {"review_id": "abc"})

    # Query provenance
    prov = get_skill_provenance("my_skill")

    # List all agent-created skills
    agent_skills = list_skills_by_source(SkillSource.AGENT_CREATED)
"""

from __future__ import annotations

import contextvars
import json
from enum import Enum
from pathlib import Path
from typing import Any


class SkillSource(str, Enum):
    """Enumeration of skill write origins."""

    AGENT_CREATED = "agent_created"
    USER_CREATED = "user_created"
    HUB_INSTALLED = "hub_installed"
    RESTORED = "restored"


# The sentinel value the background review fork uses
BACKGROUND_REVIEW = "background_review"

_write_origin: contextvars.ContextVar[str] = contextvars.ContextVar(
    "skill_write_origin",
    default="foreground",
)


def set_current_write_origin(origin: str) -> contextvars.Token[str]:
    """Bind the active write origin to the current context.

    Returns a Token the caller must pass to reset_current_write_origin
    in a finally block.
    """
    return _write_origin.set(origin or "foreground")


def reset_current_write_origin(token: contextvars.Token[str]) -> None:
    """Restore the prior write origin context."""
    _write_origin.reset(token)


def get_current_write_origin() -> str:
    """Return the active write origin.

    Default: "foreground" — any tool call made by a regular (non-review)
    agent, from the CLI, the gateway, cron, or a subagent.

    "background_review" — the self-improvement review fork; only skills
    created under this origin should be marked agent-created for curator
    management.
    """
    return _write_origin.get()


def is_background_review() -> bool:
    """Convenience: True iff the current write origin is the background
    review fork."""
    return get_current_write_origin() == BACKGROUND_REVIEW


def _get_provenance_dir() -> Path:
    """Get the provenance data directory, creating it if necessary."""
    home = Path.home()
    provenance_dir = home / ".handsome_agent" / ".provenance"
    provenance_dir.mkdir(parents=True, exist_ok=True)
    return provenance_dir


def _get_provenance_file(skill_name: str) -> Path:
    """Get the provenance file path for a skill."""
    safe_name = skill_name.replace("/", "_").replace("\\", "_")
    return _get_provenance_dir() / f"{safe_name}.json"


def mark_skill_provenance(
    skill_name: str,
    source: SkillSource,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Record the provenance of a skill.

    Args:
        skill_name: The name of the skill.
        source: The source type (from SkillSource enum).
        metadata: Optional additional metadata to store.
    """
    provenance_file = _get_provenance_file(skill_name)

    provenance_data = {
        "skill_name": skill_name,
        "source": source.value if isinstance(source, SkillSource) else source,
        "write_origin": get_current_write_origin(),
        "metadata": metadata or {},
    }

    provenance_file.write_text(
        json.dumps(provenance_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def get_skill_provenance(skill_name: str) -> dict[str, Any] | None:
    """Query the provenance of a skill.

    Args:
        skill_name: The name of the skill.

    Returns:
        A dict containing source, write_origin, and metadata, or None if not found.
    """
    provenance_file = _get_provenance_file(skill_name)

    if not provenance_file.exists():
        return None

    try:
        return json.loads(provenance_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def list_skills_by_source(source: SkillSource) -> list[dict[str, Any]]:
    """List all skills with a given source type.

    Args:
        source: The source type to filter by (from SkillSource enum).

    Returns:
        A list of provenance dicts for skills matching the source.
    """
    source_value = source.value if isinstance(source, SkillSource) else source
    results = []

    provenance_dir = _get_provenance_dir()
    if not provenance_dir.exists():
        return results

    for provenance_file in provenance_dir.glob("*.json"):
        try:
            data = json.loads(provenance_file.read_text(encoding="utf-8"))
            if data.get("source") == source_value:
                results.append(data)
        except (json.JSONDecodeError, OSError):
            continue

    return results
