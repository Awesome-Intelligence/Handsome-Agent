"""Cron job storage and management.

🚪 Access - 🔧 System - Job persistence layer
🧠 Decision - ⏰ Scheduler - Job lifecycle state machine

Ported from Hermes's ``cron/jobs.py`` (issue #32754). Stores scheduled
jobs in ``$AGENT_Z_HOME/cron/jobs.json`` and per-run output under
``$AGENT_Z_HOME/cron/output/<job_id>/<timestamp>.md``.

Job schema (the on-disk format):

  ::

      {
        "id": "ab12cd34ef56",          # 12-char hex; immutable
        "name": "Morning brief",
        "prompt": "...",                # self-contained LLM input
        "script": null,                 # path relative to $AGENT_Z_HOME/scripts
        "no_agent": false,              # true → script IS the job
        "skills": ["example-skill"],    # skill load-order
        "skill": "example-skill",       # legacy single-skill alias (auto-kept in sync)
        "model": null, "provider": null, "base_url": null,
        "schedule": {                   # parsed schedule dict
          "kind": "interval",
          "minutes": 30,
          "display": "every 30m",
        },
        "schedule_display": "every 30m",
        "repeat": {"times": null, "completed": 0},
        "enabled": true,
        "state": "scheduled",
        "created_at": "...", "next_run_at": "...",
        "last_run_at": null,
        "last_status": null,
        "last_error": null,
        "last_delivery_error": null,
        "deliver": "origin",            # or "local", "platform:chat", ...
        "origin": null,                 # {"platform": "...", "chat_id": "..."}
        "enabled_toolsets": null,
        "workdir": null,
      }

The module is the single source of truth for ALL on-disk job mutations.
Callers (CLI / model tool / REST layer) go through ``create_job``,
``update_job``, ``pause_job``, ``resume_job``, ``remove_job``,
``mark_job_run`` and ``save_job_output``.  Persistence is guarded by
``_jobs_lock``: in-process ``RLock`` + cross-process advisory file lock
(``fcntl`` on Unix / ``msvcrt`` on Windows / no-op fallback elsewhere).
"""

# Copyright © 2026 Agent-Z Contributors.
# Licensed under the MIT license. See LICENSE for details.

from __future__ import annotations

import contextlib
import copy
import json
import os
import re
import shutil
import tempfile
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Cross-process advisory file locking for jobs.json critical sections.
# fcntl is Unix-only; on Windows fall back to msvcrt. Either may be
# absent, in which case ``_jobs_lock()`` degrades to in-process locking
# only (the pre-existing behaviour) rather than failing.
try:
    import fcntl
except ImportError:  # pragma: no cover - non-Unix
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover - non-Windows
    msvcrt = None

from common.config import get_agentz_home
from common.cron_time import now as _hermes_now
from common.file_utils import atomic_replace
from common.logging_manager import get_decision_logger
from common.i18n import t

try:
    from croniter import croniter
    HAS_CRONITER = True
except ImportError:
    HAS_CRONITER = False


logger = get_decision_logger("cron", sublayer="scheduler")


# =============================================================================
# Configuration
# =============================================================================

# Cron lives under $AGENT_Z_HOME/cron/.  Tests can monkeypatch
# ``_get_active_home()`` to redirect without touching env vars.
AGENTZ_DIR = get_agentz_home().resolve()
CRON_DIR = AGENTZ_DIR / "cron"
JOBS_FILE = CRON_DIR / "jobs.json"

# Heartbeat file the in-process ticker touches on every loop iteration.
TICKER_HEARTBEAT_FILE = CRON_DIR / "ticker_heartbeat"
TICKER_SUCCESS_FILE = CRON_DIR / "ticker_last_success"
TICKER_INTERVAL_SECONDS = 60

# In-process lock protecting load_jobs→modify→save_jobs cycles.
_jobs_file_lock = threading.RLock()
_jobs_lock_state = threading.local()
OUTPUT_DIR = CRON_DIR / "output"
ONESHOT_GRACE_SECONDS = 120


# =============================================================================
# Optional home override (test hook)
# =============================================================================


def _get_active_home() -> Path:
    """Return the current cron home.

    Honors a runtime override (``_HERMES_HOME_OVERRIDE``) so tests can
    redirect cron storage to a tmpdir without mutating global env state.
    """
    override = globals().get("_HERMES_HOME_OVERRIDE")
    if override is not None:
        return Path(override)
    return get_agentz_home()


# Lazy-resolved paths. We bind these at module import time but
# ``_get_active_home()`` makes them mockable.
def _cron_dir() -> Path:
    return (_get_active_home() / "cron").resolve()


# Back-compat module-level aliases — these are RECOMPUTED inside
# ``ensure_dirs()`` and at startup so callers and tests can mutate
# the active home between operations.  Reading the constant directly
# is fast and safe; re-running ``ensure_dirs()`` (or any function
# that calls it) refreshes them.
def _refresh_paths() -> None:
    """Re-bind module-level path constants to the active home.

    Called from ``ensure_dirs()`` and at module import; safe to call
    multiple times (cheap).
    """
    global CRON_DIR, JOBS_FILE, TICKER_HEARTBEAT_FILE
    global TICKER_SUCCESS_FILE, OUTPUT_DIR
    base = _cron_dir()
    CRON_DIR = base
    JOBS_FILE = base / "jobs.json"
    TICKER_HEARTBEAT_FILE = base / "ticker_heartbeat"
    TICKER_SUCCESS_FILE = base / "ticker_last_success"
    OUTPUT_DIR = base / "output"


_refresh_paths()


# =============================================================================
# Locking
# =============================================================================


def _jobs_lock_file() -> Path:
    """Return the advisory lock path for the current cron directory."""
    return _get_active_home().joinpath("cron").resolve() / ".jobs.lock"


@contextlib.contextmanager
def _jobs_lock():
    """Serialize a load_jobs→modify→save_jobs critical section.

    Combines an in-process RLock (cheap mutual exclusion between the
    gateway's parallel tick threads) with a cross-process advisory file
    lock on ``<cron dir>/.jobs.lock`` (mutual exclusion between the
    gateway process and standalone ``agentz`` CLI invocations).

    Nested calls in the same thread reuse the held lock so legacy
    callers that invoke ``save_jobs()`` inside a broader mutation
    section don't deadlock.
    """
    depth = getattr(_jobs_lock_state, "depth", 0)
    if depth:
        _jobs_lock_state.depth = depth + 1
        try:
            yield
        finally:
            _jobs_lock_state.depth -= 1
        return

    with _jobs_file_lock:
        _jobs_lock_state.depth = 1
        lock_fd = None
        try:
            try:
                ensure_dirs()
                lock_fd = open(_jobs_lock_file(), "a+", encoding="utf-8")
                lock_fd.seek(0)
                if fcntl is not None:
                    fcntl.flock(lock_fd, fcntl.LOCK_EX)
                elif msvcrt is not None:
                    getattr(msvcrt, "locking")(
                        lock_fd.fileno(), getattr(msvcrt, "LK_LOCK"), 1
                    )
            except (OSError, IOError) as e:  # pragma: no cover
                logger.warning(
                    "jobs.json cross-process lock unavailable (%s); "
                    "proceeding with in-process lock only", e
                )
            try:
                yield
            finally:
                if lock_fd is not None:
                    try:
                        if fcntl is not None:
                            fcntl.flock(lock_fd, fcntl.LOCK_UN)
                        elif msvcrt is not None:
                            getattr(msvcrt, "locking")(
                                lock_fd.fileno(), getattr(msvcrt, "LK_UNLCK"), 1
                            )
                    except (OSError, IOError):
                        pass
                    finally:
                        lock_fd.close()
        finally:
            _jobs_lock_state.depth = 0


# Immutable job fields — never change after creation. ``id`` in
# particular is used as a filesystem path component under OUTPUT_DIR.
_IMMUTABLE_JOB_FIELDS = frozenset({"id"})


# =============================================================================
# Path sandboxing
# =============================================================================


def _job_output_dir(job_id: str) -> Path:
    """Resolve a job's output directory, rejecting path-escape attempts.

    Job IDs are filesystem path components under ``OUTPUT_DIR``. Reject
    anything that isn't a single safe path component — including
    embedded NUL bytes which can corrupt ``open()`` on POSIX even when
    the visual string looks harmless.
    """
    text = str(job_id or "").strip()
    if (
        not text
        or text in {".", ".."}
        or "/" in text
        or "\\" in text
        or "\x00" in text
    ):
        raise ValueError(f"Invalid cron job id for output path: {job_id!r}")
    if Path(text).is_absolute() or Path(text).drive:
        raise ValueError(f"Invalid cron job id for output path: {job_id!r}")
    return OUTPUT_DIR / text


# =============================================================================
# Field normalization helpers
# =============================================================================


def _normalize_skill_list(
    skill: Optional[str] = None,
    skills: Optional[Any] = None,
) -> List[str]:
    """Normalize legacy/single-skill and multi-skill inputs."""
    if skills is None:
        raw_items = [skill] if skill else []
    elif isinstance(skills, str):
        raw_items = [skills]
    else:
        raw_items = list(skills)

    normalized: List[str] = []
    for item in raw_items:
        text = str(item or "").strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def _apply_skill_fields(job: Dict[str, Any]) -> Dict[str, Any]:
    """Return a job dict with canonical ``skills`` and legacy ``skill``."""
    normalized = dict(job)
    skills = _normalize_skill_list(normalized.get("skill"), normalized.get("skills"))
    normalized["skills"] = skills
    normalized["skill"] = skills[0] if skills else None
    return normalized


def _coerce_job_text(value: Any, fallback: str = "") -> str:
    """Coerce nullable cron fields to strings for readers."""
    if value is None:
        return fallback
    return str(value)


def _schedule_display_for_job(job: Dict[str, Any]) -> str:
    display = _coerce_job_text(job.get("schedule_display")).strip()
    if display:
        return display

    schedule = job.get("schedule")
    if isinstance(schedule, dict):
        for key in ("display", "value", "expr", "run_at"):
            text = _coerce_job_text(schedule.get(key)).strip()
            if text:
                return text
    elif schedule is not None:
        return str(schedule)

    return "?"


def _normalize_job_record(job: Dict[str, Any]) -> Dict[str, Any]:
    """Return a read-safe cron job shape for consumers.

    Older or hand-edited jobs can have nullable fields. Storage is left
    untouched on read; we only ensure consumers never crash.
    """
    normalized = _apply_skill_fields(job)
    job_id = _coerce_job_text(normalized.get("id"), "unknown")
    prompt = _coerce_job_text(normalized.get("prompt"))
    normalized["id"] = job_id
    normalized["prompt"] = prompt

    name = _coerce_job_text(normalized.get("name")).strip()
    if not name:
        script = _coerce_job_text(normalized.get("script")).strip()
        label_source = (
            prompt
            or (normalized["skills"][0] if normalized.get("skills") else "")
            or script
            or job_id
            or "cron job"
        )
        name = label_source[:50].strip() or "cron job"
    normalized["name"] = name
    normalized["schedule_display"] = _schedule_display_for_job(normalized)

    state = _coerce_job_text(normalized.get("state")).strip()
    if not state:
        state = "scheduled" if normalized.get("enabled", True) else "paused"
    normalized["state"] = state

    return normalized


def _secure_dir(path: Path) -> None:
    """Set directory to owner-only access (0700). No-op on Windows."""
    try:
        os.chmod(path, 0o700)
    except (OSError, NotImplementedError):
        pass


def _secure_file(path: Path) -> None:
    """Set file to owner-only read/write (0600). No-op on Windows."""
    try:
        if path.exists():
            os.chmod(path, 0o600)
    except (OSError, NotImplementedError):
        pass


def ensure_dirs() -> None:
    """Ensure cron directories exist with secure permissions."""
    _refresh_paths()
    CRON_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _secure_dir(CRON_DIR)
    _secure_dir(OUTPUT_DIR)


# =============================================================================
# Schedule parsing
# =============================================================================


def parse_duration(s: str) -> int:
    """Parse a duration string into minutes.

    Examples: ``"30m"`` → 30; ``"2h"`` → 120; ``"1d"`` → 1440.
    """
    s = s.strip().lower()
    match = re.match(
        r"^(\d+)\s*(m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days)$", s
    )
    if not match:
        raise ValueError(
            t(
                "cron.invalid_duration",
                fallback=f"Invalid duration: '{s}'. Use format like '30m', '2h', or '1d'",
            )
        )

    value = int(match.group(1))
    unit = match.group(2)[0]

    multipliers = {"m": 1, "h": 60, "d": 1440}
    return value * multipliers[unit]


def parse_schedule(schedule: str) -> Dict[str, Any]:
    """Parse a user-supplied schedule string into structured form.

    Returns a dict with ``kind`` and per-kind fields; the displayed
    schedule string is always at ``display`` for UI rendering.

    Examples::

        "30m"              → once in 30 minutes
        "2h"               → once in 2 hours
        "every 30m"        → recurring every 30 minutes
        "every 2h"         → recurring every 2 hours
        "0 9 * * *"        → cron expression
        "2026-02-03T14:00" → once at timestamp
    """
    schedule = schedule.strip()
    original = schedule
    schedule_lower = schedule.lower()

    # ``@`` alias dispatcher — accept Hermes-style ``@every 5m`` in
    # addition to the standard croniter set (``@daily``, ``@hourly``,
    # ``@yearly``, ``@monthly``, ``@weekly``, ``@reboot``).  We treat
    # any leading ``@`` as a hint to recurse on the payload *without*
    # the sigil, so the rest of the parser sees a canonical input.
    if schedule.startswith("@"):
        payload = schedule[1:].strip()
        if not payload:
            raise ValueError(
                t(
                    "cron.invalid_schedule",
                    fallback=(
                        f"Invalid schedule '{original}'. Use:\n"
                        "  - Duration: '30m', '2h', '1d' (one-shot)\n"
                        "  - Interval: 'every 30m', 'every 2h' (recurring)\n"
                        "  - Cron: '0 9 * * *' / '@daily' / named-month form\n"
                        "  - Timestamp: '2026-02-03T14:00:00' (one-shot at time)"
                    ),
                )
            )
        if payload.lower().startswith("every "):
            # ``@every 5m`` → just delegate to the ``every X`` branch.
            return parse_schedule(payload)
        # Otherwise defer to croniter for ``@daily`` / ``@reboot`` etc.
        # The croniter block below will accept it.

    # "every X" → recurring interval
    if schedule_lower.startswith("every "):
        duration_str = schedule[6:].strip()
        minutes = parse_duration(duration_str)
        return {
            "kind": "interval",
            "minutes": minutes,
            "display": f"every {minutes}m",
        }

    # Cron expression — defer to ``croniter`` so 5/6-field expressions,
    # named months (``MON``), ``L``/``W``/``#`` descriptors, and ``@``
    # aliases (``@daily`` etc.) all parse uniformly. ``croniter`` is the
    # source of truth here; the previous hand-rolled regex rejected a
    # whole class of valid expressions (incl. 6-field seconds and
    # named-month / ``@`` shorthand forms).
    if HAS_CRONITER:
        try:
            croniter(schedule, _hermes_now())
            return {
                "kind": "cron",
                "expr": schedule,
                "display": schedule,
            }
        except Exception:
            # Not a cron expression — fall through to timestamp / duration.
            pass
    else:
        # Fallback when croniter is missing: accept the legacy 5-field
        # numeric-only subset so the module still loads. Real users
        # without croniter will see ``cron.croniter_missing`` at create
        # time for any non-trivial expression.
        parts = schedule.split()
        if len(parts) >= 5 and all(
            re.match(r"^[\d\*\-,/]+$", p) for p in parts[:5]
        ):
            raise ValueError(
                t(
                    "cron.croniter_missing",
                    fallback=(
                        "Cron expressions require 'croniter' package. "
                        "Install with: pip install croniter"
                    ),
                )
            )

    # ISO timestamp (require an explicit ``T`` separator OR a date-only
    # form that ``datetime.fromisoformat`` can resolve). A bare
    # ``"2026-12-31"`` would otherwise be ambiguous (interpreted as the
    # current zone's midnight on that day), so require an explicit time
    # OR an explicit ``Z``/offset suffix.
    if (
        "T" in schedule
        or schedule.endswith("Z")
        or re.search(r"[+-]\d{2}:?\d{2}$", schedule)
    ):
        try:
            dt = datetime.fromisoformat(schedule.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                hermes_tz = _hermes_now().tzinfo
                dt = dt.replace(tzinfo=hermes_tz)
            return {
                "kind": "once",
                "run_at": dt.isoformat(),
                "display": f"once at {dt.strftime('%Y-%m-%d %H:%M')}",
            }
        except ValueError as e:
            raise ValueError(f"Invalid timestamp '{schedule}': {e}") from e

    # Duration like "30m"/"2h"/"1d" → one-shot from now
    try:
        minutes = parse_duration(schedule)
        run_at = _hermes_now() + timedelta(minutes=minutes)
        return {
            "kind": "once",
            "run_at": run_at.isoformat(),
            "display": f"once in {original}",
        }
    except ValueError:
        pass

    raise ValueError(
        t(
            "cron.invalid_schedule",
            fallback=(
                f"Invalid schedule '{original}'. Use:\n"
                "  - Duration: '30m', '2h', '1d' (one-shot)\n"
                "  - Interval: 'every 30m', 'every 2h' (recurring)\n"
                "  - Cron: '0 9 * * *' / '@daily' / named-month form\n"
                "  - Timestamp: '2026-02-03T14:00:00' (one-shot at time)"
            ),
        )
    )


def _ensure_aware(dt: datetime) -> datetime:
    """Return a timezone-aware datetime in Hermes configured timezone."""
    target_tz = _hermes_now().tzinfo
    if dt.tzinfo is None:
        local_tz = datetime.now().astimezone().tzinfo
        return dt.replace(tzinfo=local_tz).astimezone(target_tz)
    return dt.astimezone(target_tz)


def _timezone_offset_mismatch(stored: datetime, current: datetime) -> bool:
    """Return True when stored aware timestamp has a different UTC offset."""
    if stored.tzinfo is None or current.tzinfo is None:
        return False
    return stored.utcoffset() != current.utcoffset()


def _stored_wall_clock_is_future(stored: datetime, current: datetime) -> bool:
    """Return True when the stored local wall-clock time has not arrived yet."""
    return stored.replace(tzinfo=None) > current.replace(tzinfo=None)


def _recoverable_oneshot_run_at(
    schedule: Dict[str, Any],
    now: datetime,
    *,
    last_run_at: Optional[str] = None,
) -> Optional[str]:
    """Return a one-shot run time if it is still eligible to fire."""
    if schedule.get("kind") != "once":
        return None
    if last_run_at:
        return None

    run_at = schedule.get("run_at")
    if not run_at:
        return None

    run_at_dt = _ensure_aware(datetime.fromisoformat(run_at))
    if run_at_dt >= now - timedelta(seconds=ONESHOT_GRACE_SECONDS):
        return run_at
    return None


def _compute_grace_seconds(schedule: dict) -> int:
    """Compute how late a job can be and still catch up.

    Half the schedule period, clamped between 120s and 2h.
    """
    MIN_GRACE = 120
    MAX_GRACE = 7200

    kind = schedule.get("kind")

    if kind == "interval":
        period_seconds = schedule.get("minutes", 1) * 60
        grace = period_seconds // 2
        return max(MIN_GRACE, min(grace, MAX_GRACE))

    if kind == "cron" and HAS_CRONITER:
        try:
            now = _hermes_now()
            cron = croniter(schedule["expr"], now)
            first = cron.get_next(datetime)
            second = cron.get_next(datetime)
            period_seconds = int((second - first).total_seconds())
            grace = period_seconds // 2
            return max(MIN_GRACE, min(grace, MAX_GRACE))
        except Exception:
            pass

    return MIN_GRACE


def compute_next_run(
    schedule: Dict[str, Any], last_run_at: Optional[str] = None
) -> Optional[str]:
    """Compute the next run time for a schedule."""
    now = _hermes_now()

    if schedule["kind"] == "once":
        return _recoverable_oneshot_run_at(schedule, now, last_run_at=last_run_at)

    if schedule["kind"] == "interval":
        minutes = schedule["minutes"]
        if last_run_at:
            last = _ensure_aware(datetime.fromisoformat(last_run_at))
            next_run = last + timedelta(minutes=minutes)
        else:
            next_run = now + timedelta(minutes=minutes)
        return next_run.isoformat()

    if schedule["kind"] == "cron":
        if not HAS_CRONITER:
            logger.warning(
                "Cannot compute next run for cron schedule %r: 'croniter' is "
                "not installed.",
                schedule.get("expr"),
            )
            return None
        base_time = now
        if last_run_at:
            base_time = _ensure_aware(datetime.fromisoformat(last_run_at))
        cron = croniter(schedule["expr"], base_time)
        next_run = cron.get_next(datetime)
        return next_run.isoformat()

    return None


# =============================================================================
# Ticker heartbeat (liveness signal)
# =============================================================================


def _atomic_write_epoch(path: Path) -> None:
    """Atomically write the current epoch time to ``path``."""
    ensure_dirs()
    fd, tmp_path = tempfile.mkstemp(dir=str(CRON_DIR), suffix=".tmp", prefix=".hb_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(str(time.time()))
            f.flush()
            os.fsync(f.fileno())
        atomic_replace(Path(tmp_path), path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def record_ticker_heartbeat(success: bool = False) -> None:
    """Record a ticker liveness signal, and optionally a successful-tick signal."""
    try:
        _atomic_write_epoch(TICKER_HEARTBEAT_FILE)
    except Exception:
        pass
    if success:
        try:
            _atomic_write_epoch(TICKER_SUCCESS_FILE)
        except Exception:
            pass


def _epoch_file_age(path: Path) -> Optional[float]:
    try:
        raw = path.read_text(encoding="utf-8").strip()
        return max(0.0, time.time() - float(raw))
    except Exception:
        return None


def get_ticker_heartbeat_age() -> Optional[float]:
    """Seconds since the ticker loop last iterated, or None if unknown."""
    return _epoch_file_age(TICKER_HEARTBEAT_FILE)


def get_ticker_success_age() -> Optional[float]:
    """Seconds since the ticker last completed a tick WITHOUT raising, or None."""
    return _epoch_file_age(TICKER_SUCCESS_FILE)


# =============================================================================
# Job CRUD operations
# =============================================================================


def load_jobs() -> List[Dict[str, Any]]:
    """Load all jobs from storage."""
    ensure_dirs()
    if not JOBS_FILE.exists():
        return []

    _strict_retry = False

    try:
        with open(JOBS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        _strict_retry = True
        try:
            with open(JOBS_FILE, "r", encoding="utf-8") as f:
                data = json.loads(f.read(), strict=False)
        except Exception as e:
            logger.error("Failed to auto-repair jobs.json: %s", e)
            raise RuntimeError(
                f"Cron database corrupted and unrepairable: {e}"
            ) from e
    except IOError as e:
        logger.error("IOError reading jobs.json: %s", e)
        raise RuntimeError(f"Failed to read cron database: {e}") from e

    if isinstance(data, dict):
        jobs = data.get("jobs", [])
        if _strict_retry and jobs:
            save_jobs(jobs)
            logger.warning("Auto-repaired jobs.json (had invalid control characters)")
        return jobs
    if isinstance(data, list):
        if data:
            save_jobs(data)
            logger.warning("Auto-repaired jobs.json (bare list wrapped as dict)")
        return data

    raise RuntimeError(
        f"Cron database corrupted: expected {{'jobs': [...]}}, "
        f"got {type(data).__name__}"
    )


def _save_jobs_unlocked(jobs: List[Dict[str, Any]]) -> None:
    """Save all jobs to storage. Caller must hold ``_jobs_lock()``."""
    ensure_dirs()
    fd, tmp_path = tempfile.mkstemp(
        dir=str(JOBS_FILE.parent), suffix=".tmp", prefix=".jobs_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(
                {"jobs": jobs, "updated_at": _hermes_now().isoformat()},
                f,
                indent=2,
            )
            f.flush()
            os.fsync(f.fileno())
        atomic_replace(Path(tmp_path), JOBS_FILE)
        _secure_file(JOBS_FILE)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def save_jobs(jobs: List[Dict[str, Any]]) -> None:
    """Save all jobs to storage."""
    with _jobs_lock():
        _save_jobs_unlocked(jobs)


def _normalize_workdir(workdir: Optional[str]) -> Optional[str]:
    """Normalize and validate a cron job workdir."""
    if workdir is None:
        return None
    raw = str(workdir).strip()
    if not raw:
        return None
    expanded = Path(raw).expanduser()
    if not expanded.is_absolute():
        raise ValueError(
            f"Cron workdir must be an absolute path (got {raw!r})."
        )
    resolved = expanded.resolve()
    if not resolved.exists():
        raise ValueError(f"Cron workdir does not exist: {resolved}")
    if not resolved.is_dir():
        raise ValueError(f"Cron workdir is not a directory: {resolved}")
    return str(resolved)


def _normalize_job_optional_text(
    value: Any, *, strip_trailing_slash: bool = False
) -> Optional[str]:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if strip_trailing_slash:
        text = text.rstrip("/")
    return text or None


def _resolve_default_model_snapshot() -> Optional[str]:
    """Resolve config.yaml's ``model.default`` for drift detection."""
    try:
        from common.config import load_config  # local import to avoid cycle

        cfg = load_config() or {}
    except Exception:
        return None

    model_cfg = cfg.get("model") if isinstance(cfg, dict) else None
    if isinstance(model_cfg, str):
        return model_cfg.strip() or None
    if isinstance(model_cfg, dict):
        default = model_cfg.get("default") or model_cfg.get("model")
        if isinstance(default, str):
            return default.strip() or None
    return None


def _compute_provider_model_snapshots(
    *,
    provider: Any,
    model: Any,
    base_url: Any,
    no_agent: Any,
) -> Tuple[Optional[str], Optional[str]]:
    """Snapshot unpinned inference axes for the drift guard."""
    normalized_provider = _normalize_job_optional_text(provider)
    normalized_model = _normalize_job_optional_text(model)
    normalized_base_url = _normalize_job_optional_text(
        base_url, strip_trailing_slash=True
    )
    if bool(no_agent):
        return None, None

    provider_snapshot: Optional[str] = None
    model_snapshot: Optional[str] = None
    if normalized_provider is None:
        provider_snapshot = normalized_provider
    if normalized_model is None:
        model_snapshot = _resolve_default_model_snapshot()
    return provider_snapshot, model_snapshot


def create_job(
    prompt: Optional[str],
    schedule: str,
    name: Optional[str] = None,
    repeat: Optional[int] = None,
    deliver: Optional[str] = None,
    origin: Optional[Dict[str, Any]] = None,
    skill: Optional[str] = None,
    skills: Optional[List[str]] = None,
    model: Optional[str] = None,
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    script: Optional[str] = None,
    context_from: Optional[Union[str, List[str]]] = None,
    enabled_toolsets: Optional[List[str]] = None,
    workdir: Optional[str] = None,
    no_agent: bool = False,
) -> Dict[str, Any]:
    """Create a new cron job.

    See module docstring for the on-disk schema and per-parameter
    semantics. ``prompt`` is the self-contained LLM task instruction
    (ignored when ``no_agent=True`` except as a name hint).

    :returns: The created job dict.
    :raises ValueError: on validation failures (invalid schedule, bad
        workdir, gateway-lifecycle command, missing script for no_agent).
    """
    parsed_schedule = parse_schedule(schedule)

    if repeat is not None and repeat <= 0:
        repeat = None
    if parsed_schedule["kind"] == "once" and repeat is None:
        repeat = 1
    if deliver is None:
        deliver = "origin" if origin else "local"

    job_id = uuid.uuid4().hex[:12]
    now_iso = _hermes_now().isoformat()

    normalized_skills = _normalize_skill_list(skill, skills)
    normalized_model = _normalize_job_optional_text(model)
    normalized_provider = _normalize_job_optional_text(provider)
    normalized_base_url = _normalize_job_optional_text(
        base_url, strip_trailing_slash=True
    )
    normalized_script = str(script).strip() if isinstance(script, str) else None
    normalized_script = normalized_script or None
    normalized_toolsets: Optional[List[str]] = (
        [str(t).strip() for t in enabled_toolsets if str(t).strip()]
        if enabled_toolsets
        else None
    )
    normalized_workdir = _normalize_workdir(workdir)
    normalized_no_agent = bool(no_agent)

    if normalized_no_agent and not normalized_script:
        raise ValueError(
            "no_agent=True requires a script — with no agent and no script "
            "there is nothing for the job to run."
        )

    if isinstance(context_from, str):
        context_from = [context_from.strip()] if context_from.strip() else None
    elif isinstance(context_from, list):
        context_from = [str(j).strip() for j in context_from if str(j).strip()] or None
    else:
        context_from = None

    prompt_text = _coerce_job_text(prompt)

    # Reject cron jobs that schedule gateway-lifecycle commands.
    from cron.lifecycle_guard import check_gateway_lifecycle

    check_gateway_lifecycle(prompt_text, normalized_script)

    label_source = (
        prompt_text
        or (normalized_skills[0] if normalized_skills else None)
        or (normalized_script if normalized_no_agent else None)
        or "cron job"
    )

    provider_snapshot, model_snapshot = _compute_provider_model_snapshots(
        provider=normalized_provider,
        model=normalized_model,
        base_url=normalized_base_url,
        no_agent=normalized_no_agent,
    )

    job: Dict[str, Any] = {
        "id": job_id,
        "name": name or label_source[:50].strip(),
        "prompt": prompt_text,
        "skills": normalized_skills,
        "skill": normalized_skills[0] if normalized_skills else None,
        "model": normalized_model,
        "provider": normalized_provider,
        "provider_snapshot": provider_snapshot,
        "model_snapshot": model_snapshot,
        "base_url": normalized_base_url,
        "script": normalized_script,
        "no_agent": normalized_no_agent,
        "context_from": context_from,
        "schedule": parsed_schedule,
        "schedule_display": parsed_schedule.get("display", schedule),
        "repeat": {"times": repeat, "completed": 0},
        "enabled": True,
        "state": "scheduled",
        "paused_at": None,
        "paused_reason": None,
        "created_at": now_iso,
        "next_run_at": compute_next_run(parsed_schedule),
        "last_run_at": None,
        "last_status": None,
        "last_error": None,
        "last_delivery_error": None,
        "deliver": deliver,
        "origin": origin,
        "enabled_toolsets": normalized_toolsets,
        "workdir": normalized_workdir,
    }

    with _jobs_lock():
        jobs = load_jobs()
        jobs.append(job)
        save_jobs(jobs)

    return job


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Get a job by ID."""
    jobs = load_jobs()
    for job in jobs:
        if job["id"] == job_id:
            return _normalize_job_record(job)
    return None


class AmbiguousJobReference(LookupError):
    """Raised when a job name matches more than one job."""

    def __init__(self, ref: str, matches: List[Dict[str, Any]]):
        self.ref = ref
        self.matches = matches
        ids = ", ".join(m["id"] for m in matches)
        super().__init__(
            f"Job name '{ref}' is ambiguous — matches {len(matches)} jobs: "
            f"{ids}. Use the job ID instead."
        )


def resolve_job_ref(ref: str) -> Optional[Dict[str, Any]]:
    """Resolve a job reference (ID or name) to a job record.

    - Exact ID match wins.
    - Otherwise case-insensitive name match.
    - If a name matches more than one job, raises ``AmbiguousJobReference``.
    """
    if not ref:
        return None
    jobs = load_jobs()
    for job in jobs:
        if job["id"] == ref:
            return _normalize_job_record(job)
    ref_lower = ref.lower()
    name_matches = [j for j in jobs if (j.get("name") or "").lower() == ref_lower]
    if not name_matches:
        return None
    if len(name_matches) > 1:
        raise AmbiguousJobReference(
            ref, [_normalize_job_record(j) for j in name_matches]
        )
    return _normalize_job_record(name_matches[0])


def resolve_job_id(ref: str) -> Optional[str]:
    """Resolve a job reference (ID or name) to a job **ID string**.

    Thin convenience over :func:`resolve_job_ref` for call sites that
    need the ID only (e.g. ``remove_job``, ``pause_job``). Returns
    ``None`` when nothing matches.
    """
    record = resolve_job_ref(ref)
    if record is None:
        return None
    return record.get("id")


def list_jobs(include_disabled: bool = False) -> List[Dict[str, Any]]:
    """List all jobs, optionally including disabled ones."""
    jobs = [_normalize_job_record(j) for j in load_jobs()]
    if not include_disabled:
        jobs = [j for j in jobs if j.get("enabled", True)]
    return jobs


def update_job(job_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update a job by ID, refreshing derived schedule fields when needed."""
    bad_fields = _IMMUTABLE_JOB_FIELDS.intersection(updates or {})
    if bad_fields:
        raise ValueError(
            f"Cron job field(s) cannot be updated: {', '.join(sorted(bad_fields))}"
        )

    with _jobs_lock():
        jobs = load_jobs()
        for i, job in enumerate(jobs):
            if job["id"] != job_id:
                continue

            if "workdir" in updates:
                _wd = updates["workdir"]
                if _wd in {None, "", False}:
                    updates["workdir"] = None
                else:
                    updates["workdir"] = _normalize_workdir(_wd)

            updated = _apply_skill_fields({**job, **updates})
            schedule_changed = "schedule" in updates
            inference_fields_changed = bool(
                {"provider", "model", "base_url", "no_agent"}.intersection(updates)
            )

            if "skills" in updates or "skill" in updates:
                normalized_skills = _normalize_skill_list(
                    updated.get("skill"), updated.get("skills")
                )
                updated["skills"] = normalized_skills
                updated["skill"] = normalized_skills[0] if normalized_skills else None

            if schedule_changed:
                updated_schedule = updated["schedule"]
                if isinstance(updated_schedule, str):
                    updated_schedule = parse_schedule(updated_schedule)
                    updated["schedule"] = updated_schedule
                updated["schedule_display"] = updates.get(
                    "schedule_display",
                    updated_schedule.get("display", updated.get("schedule_display")),
                )
                if updated.get("state") != "paused":
                    updated["next_run_at"] = compute_next_run(updated_schedule)

            if inference_fields_changed:
                provider_snapshot, model_snapshot = _compute_provider_model_snapshots(
                    provider=updated.get("provider"),
                    model=updated.get("model"),
                    base_url=updated.get("base_url"),
                    no_agent=updated.get("no_agent"),
                )
                updated["provider_snapshot"] = provider_snapshot
                updated["model_snapshot"] = model_snapshot

            if (
                updated.get("enabled", True)
                and updated.get("state") != "paused"
                and not updated.get("next_run_at")
            ):
                updated["next_run_at"] = compute_next_run(updated["schedule"])

            jobs[i] = updated
            save_jobs(jobs)
            return _normalize_job_record(jobs[i])
    return None


def pause_job(
    job_id: str, reason: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Pause a job without deleting it. Accepts a job ID or name."""
    job = resolve_job_ref(job_id)
    if not job:
        return None
    return update_job(
        job["id"],
        {
            "enabled": False,
            "state": "paused",
            "paused_at": _hermes_now().isoformat(),
            "paused_reason": reason,
        },
    )


def resume_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Resume a paused job and compute the next future run from now."""
    job = resolve_job_ref(job_id)
    if not job:
        return None

    next_run_at = compute_next_run(job["schedule"])
    return update_job(
        job["id"],
        {
            "enabled": True,
            "state": "scheduled",
            "paused_at": None,
            "paused_reason": None,
            "next_run_at": next_run_at,
        },
    )


def trigger_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Schedule a job to run on the next scheduler tick."""
    job = resolve_job_ref(job_id)
    if not job:
        return None
    return update_job(
        job["id"],
        {
            "enabled": True,
            "state": "scheduled",
            "paused_at": None,
            "paused_reason": None,
            "next_run_at": _hermes_now().isoformat(),
        },
    )


def remove_job(job_id: str) -> bool:
    """Remove a job by ID or name. Cleans up its output directory."""
    job = resolve_job_ref(job_id)
    if not job:
        return False
    canonical_id = job["id"]
    with _jobs_lock():
        jobs = load_jobs()
        original_len = len(jobs)
        jobs = [j for j in jobs if j["id"] != canonical_id]
        if len(jobs) < original_len:
            try:
                job_output_dir = _job_output_dir(canonical_id)
            except ValueError as exc:
                # Legacy unsafe ID — refuse to delete (fail closed).
                logger.warning("Refusing to remove malformed job id: %s", exc)
                return False
            save_jobs(jobs)
            if job_output_dir.exists():
                shutil.rmtree(job_output_dir)
            return True
    return False


def mark_job_run(
    job_id: str,
    success: bool,
    error: Optional[str] = None,
    delivery_error: Optional[str] = None,
) -> None:
    """Mark a job as having been run.

    Updates ``last_run_at``, ``last_status``, increments the completed
    count, computes ``next_run_at``, and auto-deletes when the repeat
    limit is reached.
    """
    with _jobs_lock():
        jobs = load_jobs()
        for i, job in enumerate(jobs):
            if job["id"] == job_id:
                now_iso = _hermes_now().isoformat()
                job["last_run_at"] = now_iso
                job["last_status"] = "ok" if success else "error"
                job["last_error"] = error if not success else None
                job["last_delivery_error"] = delivery_error

                if job.get("repeat"):
                    repeat = job["repeat"]
                    times = repeat.get("times")
                    completed = repeat.get("completed", 0)
                    if times is not None and times > 0 and completed >= times:
                        jobs.pop(i)
                        save_jobs(jobs)
                        return
                    completed += 1
                    repeat["completed"] = completed
                    if times is not None and times > 0 and completed >= times:
                        jobs.pop(i)
                        save_jobs(jobs)
                        return

                # Compute next run
                job["next_run_at"] = compute_next_run(job["schedule"], now_iso)

                if job["next_run_at"] is None:
                    kind = job.get("schedule", {}).get("kind")
                    if kind in {"cron", "interval"}:
                        job["state"] = "error"
                        if not job.get("last_error"):
                            job["last_error"] = (
                                "Failed to compute next run for recurring "
                                "schedule (is the 'croniter' package installed?)"
                            )
                        logger.error(
                            "Job '%s' (%s) could not compute next_run_at",
                            job.get("name", job["id"]),
                            kind,
                        )
                    else:
                        job["enabled"] = False
                        job["state"] = "completed"
                elif job.get("state") != "paused":
                    job["state"] = "scheduled"

                save_jobs(jobs)
                return

        logger.warning("mark_job_run: job_id %s not found, skipping save", job_id)


def advance_next_run(job_id: str) -> bool:
    """Preemptively advance ``next_run_at`` for a recurring job before run."""
    with _jobs_lock():
        jobs = load_jobs()
        for job in jobs:
            if job["id"] == job_id:
                kind = job.get("schedule", {}).get("kind")
                if kind not in {"cron", "interval"}:
                    return False
                now_iso = _hermes_now().isoformat()
                new_next = compute_next_run(job["schedule"], now_iso)
                if new_next and new_next != job.get("next_run_at"):
                    job["next_run_at"] = new_next
                    save_jobs(jobs)
                    return True
                return False
        return False


def get_due_jobs() -> List[Dict[str, Any]]:
    """Get all jobs that are due to run now.

    For recurring jobs (cron/interval), if the scheduled time is stale
    (more than half a period in the past), the accumulated missed runs
    are collapsed — ``next_run_at`` is fast-forwarded to the next future
    occurrence so a backlog does NOT burst-fire on restart.
    """
    with _jobs_lock():
        return _get_due_jobs_locked()


def _get_due_jobs_locked() -> List[Dict[str, Any]]:
    """Inner implementation of ``get_due_jobs()``; requires ``_jobs_lock``."""
    now = _hermes_now()
    raw_jobs = load_jobs()
    jobs = [_apply_skill_fields(j) for j in copy.deepcopy(raw_jobs)]
    due: List[Dict[str, Any]] = []
    needs_save = False

    for job in jobs:
        if not job.get("enabled", True):
            continue

        next_run = job.get("next_run_at")
        if not next_run:
            schedule = job.get("schedule", {})
            kind = schedule.get("kind")

            recovered_next = _recoverable_oneshot_run_at(
                schedule, now, last_run_at=job.get("last_run_at")
            )
            recovery_kind = "one-shot" if recovered_next else None

            if not recovered_next and kind in {"cron", "interval"}:
                recovered_next = compute_next_run(schedule, now.isoformat())
                if recovered_next:
                    recovery_kind = kind

            if not recovered_next:
                continue

            job["next_run_at"] = recovered_next
            next_run = recovered_next
            logger.info(
                "Job '%s' had no next_run_at; recovering %s run at %s",
                job.get("name", job["id"]),
                recovery_kind,
                recovered_next,
            )
            for rj in raw_jobs:
                if rj["id"] == job["id"]:
                    rj["next_run_at"] = recovered_next
                    needs_save = True
                    break

        raw_next_run_dt = datetime.fromisoformat(next_run)
        schedule = job.get("schedule", {})
        kind = schedule.get("kind")

        next_run_dt = _ensure_aware(raw_next_run_dt)
        if (
            kind == "cron"
            and next_run_dt <= now
            and _timezone_offset_mismatch(raw_next_run_dt, now)
            and _stored_wall_clock_is_future(raw_next_run_dt, now)
        ):
            new_next = compute_next_run(schedule, now.isoformat())
            if new_next:
                logger.info(
                    "Job '%s' next_run_at offset changed. Recomputing cron run.",
                    job.get("name", job["id"]),
                )
                for rj in raw_jobs:
                    if rj["id"] == job["id"]:
                        rj["next_run_at"] = new_next
                        needs_save = True
                        break
                continue

        if next_run_dt <= now:
            grace = _compute_grace_seconds(schedule)
            if (
                kind in {"cron", "interval"}
                and (now - next_run_dt).total_seconds() > grace
            ):
                new_next = compute_next_run(schedule, now.isoformat())
                if new_next:
                    logger.info(
                        "Job '%s' missed its scheduled time; running now.",
                        job.get("name", job["id"]),
                    )
                    for rj in raw_jobs:
                        if rj["id"] == job["id"]:
                            rj["next_run_at"] = new_next
                            needs_save = True
                            break
            due.append(job)

    if needs_save:
        save_jobs(raw_jobs)

    return due


# =============================================================================
# Output pruning (#52383)
# =============================================================================


_CRON_OUTPUT_DEFAULT_KEEP = 50


def _cron_output_keep() -> int:
    """Resolve the per-job output-file retention cap from config."""
    try:
        from common.config import load_config

        cfg = load_config() or {}
        cron_cfg = cfg.get("cron", {}) if isinstance(cfg, dict) else {}
        return int(cron_cfg.get("output_retention", _CRON_OUTPUT_DEFAULT_KEEP))
    except Exception:
        return _CRON_OUTPUT_DEFAULT_KEEP


def _prune_job_output(job_output_dir: Path, keep: int) -> int:
    """Remove the oldest ``*.md`` run-output files beyond *keep*."""
    if keep <= 0:
        return 0
    try:
        files = sorted(
            (f for f in job_output_dir.glob("*.md") if f.is_file()),
            key=lambda f: f.name,
            reverse=True,
        )
    except OSError:
        return 0
    deleted = 0
    for stale in files[keep:]:
        try:
            stale.unlink()
            deleted += 1
        except OSError as exc:
            logger.debug("Failed to prune cron output %s: %s", stale.name, exc)
    return deleted


def save_job_output(job_id: str, output: str) -> Path:
    """Save job output to file. Returns the file path."""
    ensure_dirs()
    job_output_dir = _job_output_dir(job_id)
    job_output_dir.mkdir(parents=True, exist_ok=True)
    _secure_dir(job_output_dir)

    timestamp = _hermes_now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = job_output_dir / f"{timestamp}.md"

    fd, tmp_path = tempfile.mkstemp(
        dir=str(job_output_dir), suffix=".tmp", prefix=".output_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(output)
            f.flush()
            os.fsync(f.fileno())
        atomic_replace(Path(tmp_path), output_file)
        _secure_file(output_file)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    _prune_job_output(job_output_dir, _cron_output_keep())

    return output_file


# =============================================================================
# Skill reference rewriting (curator integration)
# =============================================================================


def referenced_skill_names() -> Set[str]:
    """Return skill names referenced by ANY cron job."""
    try:
        jobs = load_jobs()
    except Exception:
        logger.debug("referenced_skill_names: failed to load cron jobs", exc_info=True)
        return set()

    names: Set[str] = set()
    for job in jobs:
        if not isinstance(job, dict):
            continue
        for name in _normalize_skill_list(job.get("skill"), job.get("skills")):
            cleaned = str(name).strip().lstrip("/")
            if cleaned:
                names.add(cleaned)
    return names


def rewrite_skill_refs(
    consolidated: Optional[Dict[str, str]] = None,
    pruned: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Rewrite cron job skill references after a curator consolidation pass."""
    consolidated = dict(consolidated or {})
    pruned_set = set(pruned or [])
    pruned_set -= set(consolidated.keys())

    if not consolidated and not pruned_set:
        return {"rewrites": [], "jobs_updated": 0, "jobs_scanned": 0}

    with _jobs_lock():
        jobs = load_jobs()
        rewrites: List[Dict[str, Any]] = []
        changed = False

        for job in jobs:
            skills_before = _normalize_skill_list(job.get("skill"), job.get("skills"))
            if not skills_before:
                continue

            mapped: Dict[str, str] = {}
            dropped: List[str] = []
            new_skills: List[str] = []

            for name in skills_before:
                if name in consolidated:
                    target = consolidated[name]
                    mapped[name] = target
                    if target and target not in new_skills:
                        new_skills.append(target)
                elif name in pruned_set:
                    dropped.append(name)
                elif name not in new_skills:
                    new_skills.append(name)

            if not mapped and not dropped:
                continue

            job["skills"] = new_skills
            job["skill"] = new_skills[0] if new_skills else None
            changed = True

            rewrites.append(
                {
                    "job_id": job.get("id"),
                    "job_name": job.get("name") or job.get("id"),
                    "before": list(skills_before),
                    "after": list(new_skills),
                    "mapped": mapped,
                    "dropped": dropped,
                }
            )

        if changed:
            save_jobs(jobs)
            logger.info(
                "Curator rewrote skill references in %d cron job(s)", len(rewrites)
            )

        return {
            "rewrites": rewrites,
            "jobs_updated": len(rewrites),
            "jobs_scanned": len(jobs),
        }
