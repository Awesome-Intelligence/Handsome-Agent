"""Cron job scheduler — executes due jobs.

🚪 Access - 🔧 System - Job execution loop
🧠 Decision - ⏰ Scheduler - Dispatch + agent bridge

Ported from Hermes ``cron/scheduler.py``. Provides ``tick()`` which
checks for due jobs and runs them, plus ``run_one_job`` and ``run_job``
for end-to-end execution.

The gateway daemon (or ``handsome cron tick``) calls ``tick()`` every
``TICKER_INTERVAL_SECONDS`` (60s). A file-based lock on
``<HANDSOME_HOME>/cron/.tick.lock`` ensures only one tick runs at a
time if multiple processes overlap.

Two execution paths:

* **no_agent / script** — the script IS the job. Stdout is delivered
  verbatim (or saved silently for empty output). No LLM cost.
* **default (LLM)** — the agent runs the job's prompt, optionally
  pre-seeding with skill(s), workdir, and a wake-gate script.

Hermes-only integrations (delivery adapters, profile secret scope,
per-platform mirror, MCP orphan sweep) live behind a thin
``scheduler_hooks`` adapter that Handsome-Agent's gateway or future
delivery layer can populate; calls are best-effort and never raise
into the runner.
"""

# Copyright © 2026 Handsome Agent Contributors.
# Licensed under the MIT license. See LICENSE for details.

from __future__ import annotations

import atexit
import concurrent.futures
import contextvars
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import fcntl
except ImportError:
    fcntl = None
    try:
        import msvcrt
    except ImportError:
        msvcrt = None

from common.config import get_handsome_home
from common.cron_time import now as _hermes_now
from common.i18n import t
from common.logging_manager import get_decision_logger

from cron.jobs import (
    advance_next_run,
    compute_next_run,
    get_due_jobs,
    mark_job_run,
    save_job_output,
)

logger = get_decision_logger("cron.scheduler", sublayer="scheduler")


# =============================================================================
# Public constants / sentinels
# =============================================================================


# Sentinel marker that a job's agent may prefix to its response to
# suppress delivery. Output is still saved for audit.
SILENT_MARKER = "[SILENT]"

# Canonical silence tokens recognized in cron output. Cron's contract is
# intentionally looser than the gateway's exact-whole-response rule: the
# cron system prompt INSTRUCTS the agent to emit "[SILENT]", and real
# agents often bracket it with a short note or trailing newline. We
# therefore suppress when a marker is the entire response OR appears as
# its own first/last line — but NOT when a token merely appears
# mid-sentence in a genuine report.
_CRON_SILENCE_TOKENS = frozenset({"[SILENT]", "SILENT", "NO_REPLY", "NO REPLY"})


# =============================================================================
# Lock paths
# =============================================================================


def _get_active_home() -> Path:
    """Return the current cron home (override-aware)."""
    override = globals().get("_HERMES_HOME_OVERRIDE")
    if override is not None:
        return Path(override)
    return get_handsome_home()


def _get_lock_paths() -> Tuple[Path, Path]:
    """Resolve cron tick lock paths at call time."""
    hermes_home = _get_active_home()
    lock_dir = hermes_home / "cron"
    return lock_dir, lock_dir / ".tick.lock"


def _interpreter_shutting_down(exc: Optional[BaseException] = None) -> bool:
    """True when the Python interpreter is finalizing."""
    if sys.is_finalizing():
        return True
    if exc is not None:
        return "cannot schedule new futures" in str(exc).lower()
    return False


# =============================================================================
# Hooks adapter (Hermes integration points)
# =============================================================================


# Hooks into Handsome-Agent specific subsystems (delivery, mirror,
# profile secret scope, etc.).  Tests and the gateway populate this
# before invoking ``tick()``; ``run_job`` uses best-effort reads.

_Hooks = Dict[str, Any]
_HOOKS: _Hooks = {}


def set_scheduler_hooks(hooks: _Hooks) -> None:
    """Install scheduler hooks.

    Recognised keys:

      * ``deliver`` — callable(job, content) -> error_message or None.
        Called for jobs whose ``deliver`` resolves to a target. A
        non-empty return value is recorded as ``last_delivery_error``.
      * ``pre_run``  — callable(job) -> None.  Invoked synchronously
        BEFORE agent execution.
      * ``post_run`` — callable(job, success, output, error) -> None.
        Invoked AFTER ``mark_job_run``.  Never raises into the runner.
    """
    global _HOOKS
    _HOOKS = dict(hooks or {})


def clear_scheduler_hooks() -> None:
    global _HOOKS
    _HOOKS = {}


# =============================================================================
# Pool management
# =============================================================================


_parallel_pool: Optional[concurrent.futures.ThreadPoolExecutor] = None
_parallel_pool_max_workers: Optional[int] = None
_running_job_ids: set = set()
_running_lock = threading.Lock()

# Sequential pool for env-mutating workdir jobs.
_sequential_pool: Optional[concurrent.futures.ThreadPoolExecutor] = None


class _ReadWriteLock:
    """Writer-preferring readers-writer lock for ``TERMINAL_CWD``."""

    def __init__(self) -> None:
        self._cond = threading.Condition(threading.Lock())
        self._readers = 0
        self._writer_active = False
        self._writers_waiting = 0

    def acquire_read(self) -> None:
        with self._cond:
            while self._writer_active or self._writers_waiting > 0:
                self._cond.wait()
            self._readers += 1

    def release_read(self) -> None:
        with self._cond:
            self._readers -= 1
            if self._readers == 0:
                self._cond.notify_all()

    def acquire_write(self) -> None:
        with self._cond:
            self._writers_waiting += 1
            try:
                while self._writer_active or self._readers > 0:
                    self._cond.wait()
            finally:
                self._writers_waiting -= 1
            self._writer_active = True

    def release_write(self) -> None:
        with self._cond:
            self._writer_active = False
            self._cond.notify_all()


_terminal_cwd_lock = _ReadWriteLock()


def _get_parallel_pool(max_workers: Optional[int]) -> concurrent.futures.ThreadPoolExecutor:
    global _parallel_pool, _parallel_pool_max_workers
    if _parallel_pool is None or _parallel_pool_max_workers != max_workers:
        if _parallel_pool is not None:
            _parallel_pool.shutdown(wait=False, cancel_futures=False)
        _parallel_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="cron-parallel",
        )
        _parallel_pool_max_workers = max_workers
    return _parallel_pool


def _get_sequential_pool() -> concurrent.futures.ThreadPoolExecutor:
    global _sequential_pool
    if _sequential_pool is None:
        _sequential_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="cron-seq",
        )
    return _sequential_pool


def _shutdown_pools() -> None:
    global _parallel_pool, _parallel_pool_max_workers, _sequential_pool
    if _parallel_pool is not None:
        _parallel_pool.shutdown(wait=True, cancel_futures=False)
        _parallel_pool = None
        _parallel_pool_max_workers = None
    if _sequential_pool is not None:
        _sequential_pool.shutdown(wait=True, cancel_futures=False)
        _sequential_pool = None


atexit.register(_shutdown_pools)


# =============================================================================
# Failure-summarisation + silence detection
# =============================================================================


def _summarize_cron_failure_for_delivery(job: dict, error: Optional[str]) -> str:
    """Compact one-line failure message for delivery.

    Full details stay in the cron output directory and the logs.
    """
    job_name = job.get("name") or job.get("id") or "cron job"
    text = (error or "unknown error").strip()
    lower = text.lower()

    if "429" in text or "rate limit" in lower or "usage limit" in lower:
        reason = "rate limit"
        if "weekly usage limit" in lower:
            reason = "weekly usage limit"
        elif "quota" in lower:
            reason = "quota limit"
        return (
            f"⚠️ Cron '{job_name}' failed: provider {reason}. "
            "Fallback chain was exhausted or unavailable."
        )

    if "readtimeout" in lower or "timed out" in lower or "timeout" in lower:
        return (
            f"⚠️ Cron '{job_name}' failed: provider timeout. "
            "Fallback chain was exhausted or unavailable."
        )

    if re.search(r"authenticat|authoriz", lower) or re.search(
        r"\b(401|403)\b", text
    ):
        return (
            f"⚠️ Cron '{job_name}' failed: provider authentication error."
        )

    cleaned = re.sub(
        r"^(RuntimeError|Exception|ValueError|HTTPStatusError):\s*",
        "",
        text[:2000],
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > 180:
        cleaned = cleaned[:177].rstrip() + "..."
    return f"⚠️ Cron '{job_name}' failed: {cleaned}"


def _is_cron_silence_response(text: str) -> bool:
    """Return True when a cron final response should suppress delivery."""
    if not isinstance(text, str):
        return False
    stripped = text.strip()
    if not stripped:
        return False

    def _is_token(line: str) -> bool:
        return " ".join(line.strip().upper().split()) in _CRON_SILENCE_TOKENS

    if _is_token(stripped):
        return True
    lines = [ln for ln in stripped.splitlines() if ln.strip()]
    if lines and (_is_token(lines[0]) or _is_token(lines[-1])):
        return True
    upper = stripped.upper()
    if upper.startswith("[SILENT]"):
        return True
    return False


# =============================================================================
# Script execution
# =============================================================================


def _get_script_timeout() -> int:
    try:
        from common.config import load_config

        cfg = load_config() or {}
        cron_cfg = cfg.get("cron", {}) if isinstance(cfg, dict) else {}
        return int(cron_cfg.get("script_timeout", 300))
    except Exception:
        return 300


def _run_job_script(script_path: str) -> Tuple[bool, str]:
    """Run a cron ``script`` and return ``(ok, output)``."""
    timeout = _get_script_timeout()
    hermes_home = _get_active_home()
    raw = Path(script_path).expanduser()
    if not raw.is_absolute():
        raw = hermes_home / "scripts" / raw
    if not raw.exists():
        return False, f"Script not found: {raw}"

    try:
        suffix = raw.suffix.lower()
        if suffix in (".sh", ".bash"):
            bash = shutil.which("bash") or shutil.which("sh")
            if bash is None:
                return (
                    False,
                    (
                        f"Cannot execute shell script {raw!r}: "
                        "no `bash` or `sh` on PATH. "
                        "On Windows, install Git-Bash or WSL, "
                        "or rename the script to `.py` / `.ps1` "
                        "so it can run via the Python interpreter."
                    ),
                )
            script_text = raw.read_text(encoding="utf-8", errors="replace")
            cmd = [bash, "-c", script_text]
        else:
            cmd = [sys.executable, str(raw)]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = (result.stdout or "") + (
            ("\n" + result.stderr) if result.stderr else ""
        )
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, f"Script timed out after {timeout}s"
    except Exception as exc:  # pragma: no cover
        return False, f"Script error: {exc}"


def _parse_wake_gate(script_output: str) -> bool:
    """Parse ``{"wakeAgent": false}`` script output.

    Returns ``True`` (wake the agent) when the JSON is missing or the
    explicit ``wakeAgent`` is not a Python ``False``.
    """
    try:
        payload = json.loads(script_output or "")
        if isinstance(payload, dict):
            return bool(payload.get("wakeAgent", True))
    except Exception:
        pass
    return True


# =============================================================================
# Prompt assembly
# =============================================================================


def _build_job_prompt(job: dict, prerun_script: Optional[Tuple[bool, str]] = None) -> Optional[str]:
    """Assemble the final agent prompt for a cron job.

    Returns ``None`` when the prerun script produced no usable output
    (sentinel for ``run_job`` to mark the run silent).
    """
    base = (job.get("prompt") or "").strip()
    if prerun_script is not None:
        _ok, script_output = prerun_script
        if _ok and script_output.strip():
            base = f"{base}\n\nScript output:\n{script_output.strip()}"

    if not base:
        return None
    return base


# =============================================================================
# Agent dispatch
# =============================================================================


def _run_agent_prompt(
    job: dict, prompt: str
) -> Tuple[bool, str, Optional[str]]:
    """Invoke the Agent on a cron-assembled prompt.

    Integration points (in priority order):

      1. ``HANDSOME_AGENT_RUNNER`` env var — ``module:callable`` form,
         invoked as ``callable(prompt=prompt, job=job)``. Allows the
         gateway / tests to plug in a custom runner without forking.
      2. Handsome-Agent's :class:`agent.agent.Agent` — full chat loop
         with tool-use, memory, and session persistence. Runs the
         async ``chat()`` via a fresh event loop.
      3. If neither is available (e.g. minimal CI runner), we return
         a clear ``"no agent runner configured"`` error so the failure
         is visible rather than silent.

    Toolset scoping: when ``job.enabled_toolsets`` is set, we scope
    the LLM tool selector for the duration of THIS run and restore
    the previous value in ``finally`` so concurrent / subsequent
    invocations (interactive chat, other cron jobs) never inherit the
    cron's toolset list.
    """
    override = os.environ.get("HANDSOME_AGENT_RUNNER", "").strip()
    if override:
        try:
            mod_name, _, attr = override.partition(":")
            module = __import__(mod_name, fromlist=["*"])
            runner = getattr(module, attr or "run")
            text = runner(prompt=prompt, job=job)
            return True, text, None
        except Exception as exc:  # pragma: no cover
            return False, "", f"Custom agent runner failed: {exc}"

    try:
        from agent.agent import Agent
    except Exception as exc:  # pragma: no cover - defensive
        return (
            False,
            "",
            f"Failed to import Handsome Agent: {exc}. "
            "Run `handsome setup` first, or set HANDSOME_AGENT_RUNNER.",
        )

    enable_toolsets = job.get("enabled_toolsets")
    prior_toolsets: Optional[List[str]] = None
    scope_applied = False
    try:
        import asyncio

        agent_instance = Agent(
            llm_provider=None,
            enable_session=False,
            force_new_session=True,
            enable_curator=False,
            checkpoints_enabled=False,
        )
        if enable_toolsets:
            try:
                from agent.tool_selector.llm_tool_selector import (
                    set_enabled_toolsets,
                    get_enabled_toolsets,
                )

                prior_toolsets = list(get_enabled_toolsets())
                set_enabled_toolsets(enable_toolsets)
                scope_applied = True
            except Exception as exc:
                logger.debug(
                    "Could not scope cron toolsets to %s: %s",
                    enable_toolsets,
                    exc,
                )
        response = asyncio.run(agent_instance.chat(user_input=prompt))
        text = (
            getattr(response, "content", None)
            or getattr(response, "final_result", "")
            or ""
        )
        return True, str(text), None
    except Exception as exc:
        # Translate the most common misconfiguration into an actionable
        # message so operators don't see a Python traceback on every cron.
        msg = str(exc)
        if "No LLM provider/model configured" in msg or (
            "provider" in msg.lower() and "model" in msg.lower()
        ):
            return (
                False,
                "",
                "Cron agent has no LLM configured. "
                "Run `handsome setup` or set `llm.provider` / `llm.model` "
                "in config.yaml (or per-job `model=...`).",
            )
        return False, "", f"Agent chat failed: {exc}"
    finally:
        # Always restore prior toolset scope — even on exceptions —
        # so we never leak cron toolsets into the next interactive
        # chat session.
        if scope_applied:
            try:
                from agent.tool_selector.llm_tool_selector import (
                    set_enabled_toolsets,
                )

                set_enabled_toolsets(prior_toolsets or [])
            except Exception as exc:
                logger.debug(
                    "Failed to restore prior toolsets: %s", exc
                )


# =============================================================================
# Public runners
# =============================================================================


def run_job(job: dict) -> Tuple[bool, str, str, Optional[str]]:
    """Execute a single cron job end-to-end.

    Returns ``(success, output_doc, final_response, error_message)``.
    """
    job_id = job.get("id", "?")
    job_name = str(job.get("name") or job.get("prompt") or job_id or "cron job")

    # ----- no_agent script mode -----
    if job.get("no_agent"):
        return _run_job_no_agent(job, job_id, job_name)

    # ----- LLM mode -----
    return _run_job_agent(job, job_id, job_name)


def _run_job_no_agent(
    job: dict, job_id: str, job_name: str
) -> Tuple[bool, str, str, Optional[str]]:
    """Script-only short-circuit (no LLM)."""
    script_path = job.get("script")
    if not script_path:
        err = "no_agent=True but no script is set for this job"
        logger.error("Job '%s': %s", job_id, err)
        return False, "", "", err

    _job_workdir = (job.get("workdir") or "").strip() or None
    _prior_cwd = None
    if _job_workdir and Path(_job_workdir).is_dir():
        _prior_cwd = os.getcwd()
        try:
            os.chdir(_job_workdir)
        except OSError:
            _prior_cwd = None

    try:
        ok, output = _run_job_script(script_path)
    finally:
        if _prior_cwd is not None:
            try:
                os.chdir(_prior_cwd)
            except OSError:
                pass

    now_str = _hermes_now().strftime("%Y-%m-%d %H:%M:%S")

    if not ok:
        alert = (
            f"⚠ Cron watchdog '{job_name}' script failed\n\n"
            f"{output}\n\n"
            f"Time: {now_str}"
        )
        doc = (
            f"# Cron Job: {job_name}\n\n"
            f"**Job ID:** {job_id}\n"
            f"**Run Time:** {now_str}\n"
            f"**Mode:** no_agent (script)\n"
            f"**Status:** script failed\n\n"
            f"{output}\n"
        )
        return False, doc, alert, output

    if not _parse_wake_gate(output):
        silent_doc = (
            f"# Cron Job: {job_name}\n\n"
            f"**Job ID:** {job_id}\n"
            f"**Run Time:** {now_str}\n"
            f"**Mode:** no_agent (script)\n"
            f"**Status:** silent (wakeAgent=false)\n"
        )
        return True, silent_doc, SILENT_MARKER, None

    if not output.strip():
        silent_doc = (
            f"# Cron Job: {job_name}\n\n"
            f"**Job ID:** {job_id}\n"
            f"**Run Time:** {now_str}\n"
            f"**Mode:** no_agent (script)\n"
            f"**Status:** silent (empty output)\n"
        )
        return True, silent_doc, SILENT_MARKER, None

    doc = (
        f"# Cron Job: {job_name}\n\n"
        f"**Job ID:** {job_id}\n"
        f"**Run Time:** {now_str}\n"
        f"**Mode:** no_agent (script)\n\n"
        f"---\n\n"
        f"{output}\n"
    )
    return True, doc, output, None


def _run_job_agent(
    job: dict, job_id: str, job_name: str
) -> Tuple[bool, str, str, Optional[str]]:
    """LLM-backed cron execution with optional wake-gate script."""
    script_path = job.get("script")
    prerun_script: Optional[Tuple[bool, str]] = None
    if script_path:
        prerun_script = _run_job_script(script_path)
        if prerun_script[0] and not _parse_wake_gate(prerun_script[1]):
            silent_doc = (
                f"# Cron Job: {job_name}\n\n"
                f"**Job ID:** {job_id}\n"
                f"**Run Time:** {_hermes_now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                "Script gate returned `wakeAgent=false` — agent skipped.\n"
            )
            return True, silent_doc, SILENT_MARKER, None

    prompt = _build_job_prompt(job, prerun_script=prerun_script)
    if prompt is None:
        logger.info("Job '%s': script produced no output, skipping AI call.", job_name)
        return True, "", SILENT_MARKER, None

    # Pre-run hook (delivery wiring, profile scope setup, etc.).
    pre_run = _HOOKS.get("pre_run")
    if callable(pre_run):
        try:
            pre_run(job)
        except Exception as exc:
            logger.debug("pre_run hook failed: %s", exc)

    success, final_response, error = _run_agent_prompt(job, prompt)
    now_str = _hermes_now().strftime("%Y-%m-%d %H:%M:%S")

    doc = (
        f"# Cron Job: {job_name}\n\n"
        f"**Job ID:** {job_id}\n"
        f"**Run Time:** {now_str}\n"
        f"**Mode:** agent\n"
        f"**Status:** {'ok' if success else 'error'}\n\n"
        f"---\n\n"
        f"{final_response or ''}\n"
    )
    return success, doc, final_response or "", error


def run_one_job(job: dict, *, verbose: bool = False) -> bool:
    """Run ONE due job end-to-end: execute → save → hook → mark.

    Returns ``True`` if the job was processed (even if its own run
    failed — failure is recorded via ``mark_job_run``). ``False`` only
    when processing itself raised.
    """
    try:
        # No-op CAS placeholder (Hermes pre-claims finite one-shots; we
        # simply respect ``repeat.times`` inside ``mark_job_run``).
        repeat = job.get("repeat") or {}
        if (
            repeat.get("times") is not None
            and job.get("schedule", {}).get("kind") == "once"
            and repeat.get("completed", 0) >= repeat.get("times", 0)
        ):
            logger.info(
                "Job '%s': dispatch limit reached — skipping",
                job.get("name", job["id"]),
            )
            return True

        success, output, final_response, error = run_job(job)

        delivery_error: Optional[str] = None
        try:
            output_file = save_job_output(job["id"], output)
            if verbose:
                logger.info("Output saved to: %s", output_file)
        except Exception as exc:
            logger.error("Failed to save cron output for %s: %s", job["id"], exc)

        deliver_content = final_response if success else _summarize_cron_failure_for_delivery(
            job, error
        )
        should_deliver = bool(deliver_content.strip())
        if (
            should_deliver
            and success
            and _is_cron_silence_response(deliver_content)
        ):
            logger.info(
                "Job '%s': agent returned %s — skipping delivery",
                job["id"],
                SILENT_MARKER,
            )
            should_deliver = False

        if should_deliver:
            deliver = _HOOKS.get("deliver")
            if callable(deliver):
                try:
                    delivery_error = deliver(job, deliver_content)
                except Exception as exc:
                    delivery_error = str(exc)
                    logger.error(
                        "Delivery hook failed for job %s: %s", job["id"], exc
                    )

        if success and not final_response.strip():
            success = False
            error = (
                "Agent completed but produced empty response "
                "(model error, timeout, or misconfiguration)"
            )

        mark_job_run(job["id"], success, error, delivery_error=delivery_error)

        post_run = _HOOKS.get("post_run")
        if callable(post_run):
            try:
                post_run(job, success, output, error)
            except Exception as exc:
                logger.debug("post_run hook failed: %s", exc)

        return True

    except Exception as exc:
        logger.error("Error processing job %s: %s", job["id"], exc)
        try:
            mark_job_run(job["id"], False, str(exc))
        except Exception:
            pass
        return False


# =============================================================================
# tick()
# =============================================================================


def tick(verbose: bool = True, sync: bool = True) -> int:
    """Check and run all due jobs.

    Uses a file lock so only one tick runs at a time, even if the
    gateway's in-process ticker and a standalone daemon or manual tick
    overlap.
    """
    lock_dir, lock_file = _get_lock_paths()
    lock_dir.mkdir(parents=True, exist_ok=True)

    lock_fd = None
    try:
        lock_fd = open(lock_file, "w", encoding="utf-8")
        if fcntl:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        elif msvcrt:
            msvcrt.locking(lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
    except (OSError, IOError):
        logger.debug("Tick skipped — another instance holds the lock")
        if lock_fd is not None:
            lock_fd.close()
        return 0

    try:
        due_jobs = get_due_jobs()

        if verbose and not due_jobs:
            logger.info(
                "%s - No jobs due", _hermes_now().strftime("%H:%M:%S")
            )
            return 0

        if verbose:
            logger.info(
                "%s - %s job(s) due",
                _hermes_now().strftime("%H:%M:%S"),
                len(due_jobs),
            )

        for job in due_jobs:
            advance_next_run(job["id"])

        # Resolve max workers: env > config > unbounded.
        max_workers: Optional[int] = None
        try:
            env_par = os.environ.get("HANDSOME_CRON_MAX_PARALLEL", "").strip()
            if env_par:
                max_workers = int(env_par) or None
        except (ValueError, TypeError):
            logger.warning(
                "Invalid HANDSOME_CRON_MAX_PARALLEL value; defaulting to unbounded"
            )
        if max_workers is None:
            try:
                from common.config import load_config

                cfg = load_config() or {}
                cron_cfg = cfg.get("cron", {}) if isinstance(cfg, dict) else {}
                cfg_par = cron_cfg.get("max_parallel_jobs")
                if cfg_par is not None:
                    max_workers = int(cfg_par) or None
            except Exception:
                pass

        if verbose:
            logger.info(
                "Running %d job(s) in parallel (max_workers=%s)",
                len(due_jobs),
                max_workers if max_workers else "unbounded",
            )

        sequential_jobs = [
            j for j in due_jobs if (j.get("workdir") or "").strip()
        ]
        parallel_jobs = [
            j for j in due_jobs if not (j.get("workdir") or "").strip()
        ]

        results: List[bool] = []
        all_futures: List[concurrent.futures.Future] = []

        def _process_job(j: dict) -> bool:
            return run_one_job(j, verbose=verbose)

        def _submit_with_guard(
            j: dict, pool: concurrent.futures.ThreadPoolExecutor
        ) -> Optional[concurrent.futures.Future]:
            job_id = j["id"]
            if _interpreter_shutting_down():
                logger.warning(
                    "Job '%s' not dispatched — interpreter is shutting down",
                    j.get("name", job_id),
                )
                return None
            with _running_lock:
                if job_id in _running_job_ids:
                    logger.info(
                        "Job '%s' already running — skipping",
                        j.get("name", job_id),
                    )
                    return None
                _running_job_ids.add(job_id)
            ctx = contextvars.copy_context()

            def _run_and_release(jj=j, c=ctx):
                try:
                    return c.run(_process_job, jj)
                finally:
                    with _running_lock:
                        _running_job_ids.discard(jj["id"])

            try:
                return pool.submit(_run_and_release)
            except RuntimeError as submit_err:
                if _interpreter_shutting_down(submit_err):
                    with _running_lock:
                        _running_job_ids.discard(job_id)
                    logger.warning(
                        "Job '%s' not dispatched — interpreter is shutting down",
                        j.get("name", job_id),
                    )
                    return None
                raise

        if sequential_jobs:
            seq_pool = _get_sequential_pool()
            for j in sequential_jobs:
                fut = _submit_with_guard(j, seq_pool)
                if fut is not None:
                    all_futures.append(fut)
                    if not sync:
                        results.append(True)

        if parallel_jobs:
            pool = _get_parallel_pool(max_workers)
            for j in parallel_jobs:
                fut = _submit_with_guard(j, pool)
                if fut is not None:
                    all_futures.append(fut)
                    if not sync:
                        results.append(True)

        if sync:
            for f in concurrent.futures.as_completed(all_futures):
                try:
                    results.append(f.result())
                except Exception as exc:
                    logger.error("Cron job future failed: %s", exc)
                    results.append(False)
            return sum(results)

        if all_futures:
            remaining = [len(all_futures)]

            def _on_done(_f: concurrent.futures.Future) -> None:
                remaining[0] -= 1
                try:
                    _exc = _f.exception()
                    if _exc is not None:
                        logger.error("Cron job future failed in async mode: %s", _exc)
                except Exception:
                    pass

            for _f in all_futures:
                _f.add_done_callback(_on_done)

        return sum(results)
    finally:
        if lock_fd is not None:
            try:
                if fcntl:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                elif msvcrt:
                    msvcrt.locking(lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
            except (OSError, IOError):
                pass
            lock_fd.close()


# =============================================================================
# Background ticker (optional convenience)
# =============================================================================


class BackgroundTicker:
    """Run ``tick()`` on a fixed interval in a daemon thread.

    Used by the Handsome-Agent gateway / daemon. Stop with ``stop()``.
    """

    def __init__(self, interval_seconds: int = 60) -> None:
        self.interval = interval_seconds
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name="handsome-cron-ticker",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    def _loop(self) -> None:
        from cron.jobs import record_ticker_heartbeat

        while not self._stop.is_set():
            tick_ok = False
            # Pre-tick heartbeat: ensures ``handsome cron status`` can
            # tell that the ticker thread is *alive*, even if a tick
            # blocks forever on a slow agent run.
            try:
                record_ticker_heartbeat(success=False)
            except Exception:
                pass
            try:
                count = tick(verbose=False, sync=True)
                tick_ok = True
                logger.debug("Cron tick fired %d job(s)", count)
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("Cron tick raised: %s", exc)
            try:
                record_ticker_heartbeat(success=tick_ok)
            except Exception:
                pass
            self._stop.wait(self.interval)


__all__ = [
    "SILENT_MARKER",
    "tick",
    "run_one_job",
    "run_job",
    "set_scheduler_hooks",
    "clear_scheduler_hooks",
    "BackgroundTicker",
]
