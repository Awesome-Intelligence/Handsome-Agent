# 🚪 Access - gateway/session.py
"""
Session management for the gateway.
Ported from Hermes agent - https://github.com/NousResearch/hermes-agent
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


def _now() -> datetime:
    return datetime.now()


def _hash_id(value: str) -> str:
    """Deterministic 12-char hex hash of an identifier."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _hash_sender_id(value: str) -> str:
    """Hash a sender ID to ``user_<12hex>``."""
    return f"user_{_hash_id(value)}"


def _hash_chat_id(value: str) -> str:
    """Hash the numeric portion of a chat ID, preserving platform prefix."""
    colon = value.find(":")
    if colon > 0:
        prefix = value[:colon]
        return f"{prefix}:{_hash_id(value[colon + 1:])}"
    return _hash_id(value)


class Platform(Enum):
    """Supported messaging platforms."""

    LOCAL = "local"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    WHATSAPP = "whatsapp"
    WHATSAPP_CLOUD = "whatsapp_cloud"
    SLACK = "slack"
    SIGNAL = "signal"
    MATTERMOST = "mattermost"
    MATRIX = "matrix"
    HOMEASSISTANT = "homeassistant"
    EMAIL = "email"
    SMS = "sms"
    DINGTALK = "dingtalk"
    API_SERVER = "api_server"
    WEBHOOK = "webhook"
    MSGRAPH_WEBHOOK = "msgraph_webhook"
    FEISHU = "feishu"
    WECOM = "wecom"
    WECOM_CALLBACK = "wecom_callback"
    WEIXIN = "weixin"
    BLUEBUBBLES = "bluebubbles"
    QQBOT = "qqbot"
    YUANBAO = "yuanbao"
    RELAY = "relay"
    NTFY = "ntfy"
    GOOGLE_CHAT = "google_chat"
    PHOTON = "photon"
    LINE = "line"
    IRC = "irc"
    TEAMS = "teams"
    RAFT = "raft"
    SIMPLEX = "simplex"

    @classmethod
    def _missing_(cls, value):
        if not isinstance(value, str) or not value.strip():
            return None
        value = value.strip().lower()
        if value in cls._value2member_map_:
            return cls._value2member_map_[value]
        return None


@dataclass
class SessionSource:
    """Describes where a message originated from."""

    platform: Platform
    chat_id: str
    chat_name: str | None = None
    chat_type: str = "dm"
    user_id: str | None = None
    user_name: str | None = None
    thread_id: str | None = None
    chat_topic: str | None = None
    user_id_alt: str | None = None
    chat_id_alt: str | None = None
    is_bot: bool = False
    scope_id: str | None = None
    guild_id: str | None = None
    parent_chat_id: str | None = None
    message_id: str | None = None
    role_authorized: bool = False
    profile: str | None = None
    delivered_via_upstream_relay: bool = False

    def __post_init__(self) -> None:
        if self.scope_id is None and self.guild_id is not None:
            self.scope_id = self.guild_id
        elif self.scope_id is not None:
            self.guild_id = self.scope_id

    @property
    def description(self) -> str:
        """Human-readable description of the source."""
        if self.platform == Platform.LOCAL:
            return "CLI terminal"

        parts = []
        if self.chat_type == "dm":
            parts.append(f"DM with {self.user_name or self.user_id or 'user'}")
        elif self.chat_type == "group":
            parts.append(f"group: {self.chat_name or self.chat_id}")
        elif self.chat_type == "channel":
            parts.append(f"channel: {self.chat_name or self.chat_id}")
        else:
            parts.append(self.chat_name or self.chat_id)

        if self.thread_id:
            parts.append(f"thread: {self.thread_id}")

        return ", ".join(parts)

    def to_dict(self) -> dict:
        return {
            "platform": self.platform.value,
            "chat_id": self.chat_id,
            "chat_name": self.chat_name,
            "chat_type": self.chat_type,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "thread_id": self.thread_id,
            "chat_topic": self.chat_topic,
            "user_id_alt": self.user_id_alt,
            "chat_id_alt": self.chat_id_alt,
            "is_bot": self.is_bot,
            "scope_id": self.scope_id,
            "guild_id": self.guild_id,
            "parent_chat_id": self.parent_chat_id,
            "message_id": self.message_id,
            "role_authorized": self.role_authorized,
            "profile": self.profile,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionSource":
        return cls(
            platform=Platform(data["platform"]),
            chat_id=str(data["chat_id"]),
            chat_name=data.get("chat_name"),
            chat_type=data.get("chat_type", "dm"),
            user_id=data.get("user_id"),
            user_name=data.get("user_name"),
            thread_id=data.get("thread_id"),
            chat_topic=data.get("chat_topic"),
            user_id_alt=data.get("user_id_alt"),
            chat_id_alt=data.get("chat_id_alt"),
            is_bot=data.get("is_bot", False),
            scope_id=data.get("scope_id", data.get("guild_id")),
            parent_chat_id=data.get("parent_chat_id"),
            message_id=data.get("message_id"),
            role_authorized=data.get("role_authorized", False),
            profile=data.get("profile"),
        )


def _session_key_namespace(profile: Optional[str]) -> str:
    if not profile or profile == "default":
        return "agent:main"
    return f"agent:{profile}"


def build_session_key(
    source: SessionSource,
    group_sessions_per_user: bool = True,
    thread_sessions_per_user: bool = False,
    profile: Optional[str] = None,
) -> str:
    """Build a deterministic session key from a message source."""
    ns = _session_key_namespace(profile)
    platform = source.platform.value

    if source.chat_type == "dm":
        dm_chat_id = source.chat_id
        if dm_chat_id:
            if source.thread_id:
                return f"{ns}:{platform}:dm:{dm_chat_id}:{source.thread_id}"
            return f"{ns}:{platform}:dm:{dm_chat_id}"

        dm_participant_id = source.user_id_alt or source.user_id
        if dm_participant_id:
            if source.thread_id:
                return f"{ns}:{platform}:dm:{dm_participant_id}:{source.thread_id}"
            return f"{ns}:{platform}:dm:{dm_participant_id}"
        if source.thread_id:
            return f"{ns}:{platform}:dm:{source.thread_id}"
        return f"{ns}:{platform}:dm"

    participant_id = source.user_id_alt or source.user_id
    key_parts = [ns, platform, source.chat_type]

    if source.chat_id:
        key_parts.append(source.chat_id)
    if source.thread_id:
        key_parts.append(source.thread_id)

    isolate_user = group_sessions_per_user
    if source.thread_id and not thread_sessions_per_user:
        isolate_user = False

    if isolate_user and participant_id:
        key_parts.append(str(participant_id))

    return ":".join(key_parts)
