# 🚪 Access - gateway/whatsapp_identity.py
"""Shared helpers for canonicalising WhatsApp sender identity.

Ported from Hermes agent - https://github.com/NousResearch/hermes-agent
"""

from __future__ import annotations

import json
import logging
import re
from typing import Set

logger = logging.getLogger(__name__)

# WhatsApp JIDs are numeric (or plus-prefixed numeric) with optional
# ``@``, ``.`` and ``:`` separators. ``\w`` is pinned to ASCII so
# full-width digits / Unicode word chars can't sneak through.
_SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9@.+\-]+$")

# A target that is "just a phone number" — optional leading ``+`` then digits
# and the usual human separators (spaces, dots, dashes, parens). Anything that
# already carries an ``@`` is a fully-qualified JID and must pass through
# untouched (group ``@g.us``, LID ``@lid``, ``status@broadcast`` etc.).
_BARE_PHONE_RE = re.compile(r"^\+?[\d\s().\-]+$")


def normalize_whatsapp_identifier(value: str) -> str:
    """Strip WhatsApp JID/LID syntax down to its stable numeric identifier.

    Accepts any of the identifier shapes the WhatsApp bridge may emit:
    ``"60123456789@s.whatsapp.net"``, ``"60123456789:47@s.whatsapp.net"``,
    ``"60123456789@lid"``, or a bare ``"+601****6789"``.
    Returns just the numeric identifier (``"60123456789"``) suitable for
    equality comparisons.
    """
    return (
        str(value or "")
        .strip()
        .replace("+", "", 1)
        .split(":", 1)[0]
        .split("@", 1)[0]
    )


def to_whatsapp_jid(value: str) -> str:
    """Normalize an *outbound* WhatsApp target to a bridge-safe JID.

    Baileys' ``jidDecode`` crashes on a bare phone number — it expects a
    fully-qualified JID such as ``50766715226@s.whatsapp.net``. This helper
    is the inverse of :func:`normalize_whatsapp_identifier`: instead of
    stripping a JID down to its numeric core for comparison, it *builds*
    the JID a send must use.

    Behaviour:

    - ``"+50766715226"`` / ``"50766715226"`` → ``"50766715226@s.whatsapp.net"``
    - ``"50766715226@s.whatsapp.net"`` → unchanged
    - ``"group-id@g.us"`` / ``"130631430344750@lid"`` → unchanged
    - ``"user:device@s.whatsapp.net"`` style colon-before-``@`` → ``@`` form
    - anything that isn't a recognizable bare phone → returned unchanged

    Returns ``""`` for an empty/whitespace input.
    """
    if not value:
        return ""

    normalized = str(value).strip()
    if ":" in normalized and "@" in normalized:
        prefix, _, domain = normalized.partition(":")
        normalized = f"{prefix.split(':', 1)[0]}@{domain}"

    if "@" in normalized:
        return normalized

    if _BARE_PHONE_RE.fullmatch(normalized):
        digits = re.sub(r"\D+", "", normalized)
        if digits:
            return f"{digits}@s.whatsapp.net"

    return normalized


def expand_whatsapp_aliases(identifier: str) -> Set[str]:
    """Resolve WhatsApp phone/LID aliases via bridge session mapping files.

    Returns the set of all identifiers transitively reachable through any
    bridge session mapping files, starting from ``identifier``.
    The result always includes the normalized input itself, so callers
    can safely ``in`` check against the return value without a separate
    fallback branch.

    Returns an empty set if ``identifier`` normalizes to empty.

    In Agent-Z, this is a stub that only returns the normalized identifier
    itself since the bridge session mapping files are Hermes-specific.
    """
    normalized = normalize_whatsapp_identifier(identifier)
    if not normalized:
        return set()
    return {normalized}


def canonical_whatsapp_identifier(identifier: str) -> str:
    """Return a stable WhatsApp sender identity across phone-JID/LID variants.

    In Agent-Z, this is a stub that just returns the normalized identifier.
    """
    normalized = normalize_whatsapp_identifier(identifier)
    if not normalized:
        return ""
    return normalized
