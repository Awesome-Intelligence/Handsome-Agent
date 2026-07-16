"""Cron time helpers.

Lightweight timezone-aware clock mirroring Hermes's ``hermes_time.now``
contract:

  * Returns a ``datetime`` whose ``tzinfo`` always reflects the active
    configured timezone (resolved from ``AGENTZ_TZ`` env var, falling
    back to ``AGENTZ_LANGUAGE``/system local).
  * Even when no fixed-offset IANA name is configured, the returned tzinfo
    is whatever ``datetime.now().astimezone().tzinfo`` produces — so
    formatting and arithmetic stay consistent end-to-end.

The cron subsystem stores every timestamp as ISO 8601 with explicit
offset.  Re-parsing that string and rounding through :func:`now()` keeps
schedule comparisons aligned with whatever the user intended on the
wall clock (avoiding bugs like "20:07 fired 7 hours late because the
stored instant used a different offset than today's``now()``").
"""

from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from typing import Optional


_tz_cache_lock = threading.Lock()
_tz_cache: Optional[object] = None


def _resolve_tz():
    """Resolve the active timezone from env / system.

    Order of precedence:
      1. ``AGENTZ_TZ`` env var — an IANA name (``Asia/Shanghai``)
         or a fixed ``+/-HH:MM`` offset.
      2. The system local zone (``datetime.now().astimezone().tzinfo``).

    The result is cached for process lifetime; a test that needs a
    different zone should monkeypatch ``_tz_cache``.
    """
    global _tz_cache
    with _tz_cache_lock:
        if _tz_cache is not None:
            return _tz_cache
        raw = os.environ.get("AGENTZ_TZ", "").strip()
        if raw:
            # Try fixed offset first (cheap and unambiguous).
            try:
                if len(raw) <= 6 and (raw.startswith("+") or raw.startswith("-")):
                    sign = 1 if raw[0] == "+" else -1
                    hh, mm = (int(x) for x in raw[1:].split(":"))
                    _tz_cache = timezone(sign * (hh * 3600 + mm * 60))
                    return _tz_cache
                from datetime import timezone as _tz
                from zoneinfo import ZoneInfo

                _tz_cache = ZoneInfo(raw)
                return _tz_cache
            except Exception:
                pass
        _tz_cache = datetime.now().astimezone().tzinfo
        return _tz_cache


def set_cron_timezone(tz) -> None:
    """Override the cron timezone cache. Intended for tests."""
    global _tz_cache
    with _tz_cache_lock:
        _tz_cache = tz


def now() -> datetime:
    """Return a timezone-aware ``datetime`` in the configured cron timezone.

    Mirrors Hermes's :func:`hermes_time.now` so ports of cron logic can
    call ``from common.cron_time import now as _hermes_now`` and behave
    identically.
    """
    return datetime.now(_resolve_tz())


def iso_now() -> str:
    """Return the current time as an ISO-8601 string with offset."""
    return now().isoformat()
