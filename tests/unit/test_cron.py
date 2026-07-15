"""Unit tests for the cron subsystem.

🚪 Access - 🧪 Tests - Cron lifecycle and scheduler

Covers:
  * ``cron.jobs``     — CRUD, schedule parsing, due-job selection,
    one-shot recovery, lifecycle_guard integration, output pruning.
  * ``cron.lifecycle_guard`` — gateway-lifecycle command rejection.
  * ``cron.scheduler``  — tick lock, no_agent script short-circuit,
    silence suppression, deliver-hook handshake, BackgroundTicker
    thread lifecycle.

Runs hermetic: every test redirects ``$HANDSOME_HOME`` to a tmpdir and
isolates ``$HANDSOME_AGENT_RUNNER`` to a stub callable.
"""

# Copyright © 2026 Handsome Agent Contributors.
# Licensed under the MIT license. See LICENSE for details.

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

# Ensure we can import the cron package regardless of where pytest runs.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect HANDSOME_HOME and cron storage to a tmpdir."""
    monkeypatch.setenv("HANDSOME_HOME", str(tmp_path))
    # Force lazy resolution: common.config caches HANDSOME_HOME at import
    # time, but cron/jobs.py re-resolves via _get_active_home() each call.
    # We additionally refresh common.config.HANDSOME_HOME for consumers
    # that imported it.
    import common.config as _common_config

    monkeypatch.setattr(_common_config, "HANDSOME_HOME", Path(tmp_path))

    # Re-bind cron.jobs module-level path aliases so OUTPUT_DIR et al
    # point at the tmpdir. Production consumers invoke ensure_dirs()
    # before any I/O, so this is a safe refresh for tests too.
    import cron.jobs as _cron_jobs

    _cron_jobs._refresh_paths()
    return tmp_path


@pytest.fixture
def jobs_module():
    """Import cron.jobs freshly so per-test HOME redirects kick in."""
    import cron.jobs as j

    return j


@pytest.fixture
def scheduler_module():
    import cron.scheduler as s

    return s


@pytest.fixture
def clean_cron_dir(tmp_home: Path):
    """Make sure no leftover cron/ dir exists when a test starts."""
    cron_dir = tmp_home / "cron"
    if cron_dir.exists():
        shutil.rmtree(cron_dir)
    return cron_dir


@pytest.fixture(autouse=True)
def _reset_cron_globals(monkeypatch: pytest.MonkeyPatch):
    """Reset cron schedulers' in-process state between tests."""
    import cron.scheduler as s

    s.clear_scheduler_hooks()
    s._parallel_pool = None
    s._parallel_pool_max_workers = None
    s._sequential_pool = None
    with s._running_lock:
        s._running_job_ids.clear()
    yield
    s.clear_scheduler_hooks()


# ---------------------------------------------------------------------------
# Schedule parsing
# ---------------------------------------------------------------------------


class TestScheduleParsing:
    def test_duration(self, jobs_module):
        from cron.jobs import parse_duration, parse_schedule

        assert parse_duration("30m") == 30
        assert parse_duration("2h") == 120
        assert parse_duration("1d") == 1440
        assert parse_duration("45 mins") == 45
        with pytest.raises(ValueError):
            parse_duration("not-a-duration")

        # One-shot durations
        once = parse_schedule("30m")
        assert once["kind"] == "once"
        assert "run_at" in once
        assert once["display"].startswith("once in 30m")

    def test_every_interval(self, jobs_module):
        from cron.jobs import parse_schedule

        sched = parse_schedule("every 15m")
        assert sched["kind"] == "interval"
        assert sched["minutes"] == 15
        assert sched["display"] == "every 15m"

    def test_iso_timestamp(self, jobs_module):
        from cron.jobs import parse_schedule

        sched = parse_schedule("2026-12-31T23:59")
        assert sched["kind"] == "once"
        assert "2026-12-31" in sched["run_at"]

    def test_cron_expression(self, jobs_module):
        from cron.jobs import parse_schedule, HAS_CRONITER

        if not HAS_CRONITER:
            pytest.skip("croniter not installed")
        sched = parse_schedule("0 9 * * *")
        assert sched["kind"] == "cron"
        assert sched["expr"] == "0 9 * * *"

    def test_invalid_schedule(self, jobs_module):
        from cron.jobs import parse_schedule

        with pytest.raises(ValueError):
            parse_schedule("not a real schedule at all")


# ---------------------------------------------------------------------------
# Persistence + CRUD
# ---------------------------------------------------------------------------


class TestJobsCrud:
    def test_create_and_list(
        self, jobs_module, tmp_home, clean_cron_dir
    ):
        from cron.jobs import create_job, list_jobs

        job = create_job(prompt="Say hi", schedule="every 1m")
        assert job["id"]
        assert job["prompt"] == "Say hi"
        assert job["enabled"] is True
        assert job["state"] in ("scheduled", "paused")
        assert job["next_run_at"]

        jobs = list_jobs()
        assert any(j["id"] == job["id"] for j in jobs)

    def test_create_idempotency(
        self, jobs_module, tmp_home, clean_cron_dir
    ):
        from cron.jobs import create_job

        ids = {create_job(prompt=f"x{i}", schedule="every 1m")["id"] for i in range(5)}
        assert len(ids) == 5

    def test_create_rejects_blocked_prompt(
        self, jobs_module, tmp_home, clean_cron_dir
    ):
        from cron.lifecycle_guard import GatewayLifecycleBlocked

        with pytest.raises(GatewayLifecycleBlocked):
            jobs_module.create_job(
                prompt="please run: handsome gateway restart now",
                schedule="every 1m",
            )

    def test_create_no_agent_requires_script(
        self, jobs_module, tmp_home, clean_cron_dir
    ):
        with pytest.raises(ValueError):
            jobs_module.create_job(
                prompt="ignored",
                schedule="every 1m",
                no_agent=True,
            )

    def test_pause_resume(
        self, jobs_module, tmp_home, clean_cron_dir
    ):
        from cron.jobs import (
            create_job,
            get_job,
            pause_job,
            resume_job,
        )

        job = create_job(prompt="x", schedule="every 1m")
        paused = pause_job(job["id"], reason="manual")
        assert paused is not None
        assert paused["enabled"] is False
        assert paused["state"] == "paused"
        assert paused["paused_reason"] == "manual"

        resumed = resume_job(job["id"])
        assert resumed["enabled"] is True
        assert resumed["next_run_at"]

    def test_update_schedule(
        self, jobs_module, tmp_home, clean_cron_dir
    ):
        from cron.jobs import create_job, update_job

        job = create_job(prompt="x", schedule="every 1m")
        original_next = job["next_run_at"]
        updated = update_job(job["id"], {"schedule": "every 5m"})
        assert updated["schedule"]["minutes"] == 5
        assert updated["next_run_at"] != original_next

    def test_update_blocks_immutable_id(
        self, jobs_module, tmp_home, clean_cron_dir
    ):
        from cron.jobs import create_job, update_job

        job = create_job(prompt="x", schedule="every 1m")
        with pytest.raises(ValueError):
            update_job(job["id"], {"id": "evilslashes../.."})

    def test_remove_cleans_output_dir(
        self, jobs_module, tmp_home, clean_cron_dir
    ):
        from cron.jobs import create_job, remove_job, save_job_output

        job = create_job(prompt="x", schedule="every 1m")
        save_job_output(job["id"], "hello world")
        out_dir = tmp_home / "cron" / "output" / job["id"]
        assert out_dir.exists()

        removed = remove_job(job["id"])
        assert removed is True
        assert not out_dir.exists()

    def test_get_job_by_name(
        self, jobs_module, tmp_home, clean_cron_dir
    ):
        from cron.jobs import AmbiguousJobReference, create_job, resolve_job_ref

        create_job(
            prompt="unique", schedule="every 1m", name="morning-brief"
        )
        ref = resolve_job_ref("morning-brief")
        assert ref is not None
        assert ref["name"] == "morning-brief"

        create_job(prompt="x2", schedule="every 1m", name="dup")
        create_job(prompt="x3", schedule="every 1m", name="dup")
        with pytest.raises(AmbiguousJobReference):
            resolve_job_ref("DUP")

    def test_corrupt_jobs_file_repair(
        self, jobs_module, tmp_home, clean_cron_dir
    ):
        """Bare-list form should auto-repair into the dict wrapper."""
        from cron.jobs import JOBS_FILE, save_jobs

        JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
        JOBS_FILE.write_text(
            json.dumps([{"id": "abc", "prompt": "x"}], ensure_ascii=False),
            encoding="utf-8",
        )
        loaded = jobs_module.load_jobs()
        assert any(j["id"] == "abc" for j in loaded)
        # After repair, file should now be the dict wrapper.
        data = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        assert "jobs" in data


# ---------------------------------------------------------------------------
# Due-job selection + repeat
# ---------------------------------------------------------------------------


class TestGetDueJobs:
    def test_due_now(self, jobs_module, tmp_home, clean_cron_dir):
        from cron.jobs import create_job, mark_job_run, update_job

        from cron.jobs import get_due_jobs

        # One-shot 5 minutes ago → already due
        job = create_job(prompt="x", schedule="5m")
        # Roll next_run_at into the past to make it due immediately.
        update_job(
            job["id"],
            {"next_run_at": "2000-01-01T00:00:00+00:00"},
        )
        due = get_due_jobs()
        assert any(d["id"] == job["id"] for d in due)

    def test_paused_jobs_excluded(
        self, jobs_module, tmp_home, clean_cron_dir
    ):
        from cron.jobs import (
            create_job,
            get_due_jobs,
            pause_job,
            update_job,
        )

        job = create_job(prompt="x", schedule="5m")
        update_job(
            job["id"],
            {"next_run_at": "2000-01-01T00:00:00+00:00"},
        )
        pause_job(job["id"])
        assert not any(d["id"] == job["id"] for d in get_due_jobs())

    def test_mark_run_one_shot_completes(
        self, jobs_module, tmp_home, clean_cron_dir
    ):
        from cron.jobs import (
            create_job,
            get_job,
            mark_job_run,
        )

        job = create_job(prompt="x", schedule="5m", repeat=1)
        mark_job_run(job["id"], success=True)
        # repeat=1 one-shot should auto-delete.
        assert get_job(job["id"]) is None

    def test_mark_run_recurring(
        self, jobs_module, tmp_home, clean_cron_dir
    ):
        from cron.jobs import (
            create_job,
            get_job,
            mark_job_run,
        )

        job = create_job(prompt="x", schedule="every 1m")
        mark_job_run(job["id"], success=True)
        refetched = get_job(job["id"])
        assert refetched is not None
        assert refetched["last_status"] == "ok"
        assert refetched["last_run_at"]
        # next_run_at moves into the future (last + 1m)
        assert refetched["next_run_at"] > refetched["last_run_at"]


# =============================================================================
# Lifecycle guard
# =============================================================================


class TestLifecycleGuard:
    def test_handsome_gateway_restart_blocked(
        self, jobs_module, tmp_home
    ):
        from cron.lifecycle_guard import check_gateway_lifecycle

        with pytest.raises(Exception) as ei:
            check_gateway_lifecycle(
                prompt="run this: handsome gateway restart"
            )
        assert "Blocked" in str(ei.value) or "blocked" in str(ei.value)

    def test_handsome_gateway_stop_blocked(self):
        from cron.lifecycle_guard import check_gateway_lifecycle

        with pytest.raises(Exception):
            check_gateway_lifecycle(prompt="handsome gateway stop")

    def test_unrelated_passive_text_allowed(self):
        from cron.lifecycle_guard import (
            contains_gateway_lifecycle_command,
        )

        assert (
            contains_gateway_lifecycle_command(
                "discussed API gateway autoscaling today"
            )
            is False
        )

    def test_script_content_scanned(self, tmp_home):
        from cron.lifecycle_guard import check_gateway_lifecycle

        bad_script = tmp_home / "scripts" / "evil.sh"
        bad_script.parent.mkdir(parents=True, exist_ok=True)
        bad_script.write_text(
            "#!/bin/bash\nhandsome gateway restart", encoding="utf-8"
        )
        with pytest.raises(Exception):
            check_gateway_lifecycle(
                prompt="benign",
                script=str(bad_script),
            )


# =============================================================================
# Scheduler — script + tick lock
# =============================================================================


class TestSchedulerScriptMode:
    def test_script_short_circuit(
        self, scheduler_module, tmp_home, clean_cron_dir
    ):
        """A no_agent script job should not invoke the Agent runner."""
        from cron.jobs import create_job
        from cron.scheduler import run_job

        script = tmp_home / "scripts" / "hello.sh"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text(
            "#!/bin/sh\necho 'watchdog says hello'\n", encoding="utf-8"
        )

        job = create_job(
            prompt="ignored",
            schedule="every 1m",
            name="hello-watchdog",
            script="hello.sh",
            no_agent=True,
        )
        # ensure script is the resolved path
        from cron.jobs import update_job

        update_job(
            job["id"], {"script": str(script)}
        )

        success, doc, final_response, error = run_job(
            {
                **job,
                "script": str(script),
                "workdir": None,
            }
        )
        assert success is True
        assert "watchdog says hello" in final_response

    def test_silent_script(
        self, scheduler_module, tmp_home, clean_cron_dir
    ):
        from cron.jobs import create_job
        from cron.scheduler import SILENT_MARKER, run_job

        script = tmp_home / "scripts" / "silent.sh"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text(
            "#!/bin/sh\nexit 0\n", encoding="utf-8"
        )

        job = create_job(
            prompt="ignored",
            schedule="every 1m",
            name="silent-watchdog",
            script=str(script),
            no_agent=True,
        )
        # Run via scheduler
        success, doc, response, error = run_job({**job, "workdir": None})
        assert success is True
        assert response == SILENT_MARKER

    def test_wake_gate(
        self, scheduler_module, tmp_home, clean_cron_dir
    ):
        """wakeAgent=false short-circuits even on agent jobs."""
        from cron.jobs import create_job
        from cron.scheduler import (
            SILENT_MARKER,
            clear_scheduler_hooks,
            run_job,
            set_scheduler_hooks,
        )

        script = tmp_home / "scripts" / "skip.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text(
            "import json, sys; print(json.dumps({'wakeAgent': False}))",
            encoding="utf-8",
        )

        job = create_job(
            prompt="real prompt",
            schedule="every 1m",
            name="skip-on-empty",
            script=str(script),
        )

        # Custom runner that records if it was invoked.
        called = {"n": 0}

        def fake_runner(prompt: str, job: dict):
            called["n"] += 1
            return f"PROMPT-ONLY:{prompt}"

        os.environ["HANDSOME_AGENT_RUNNER"] = (
            "tests.unit.test_cron:fake_runner"
        )
        try:
            success, doc, response, error = run_job({**job, "workdir": None})
        finally:
            os.environ.pop("HANDSOME_AGENT_RUNNER", None)
            clear_scheduler_hooks()

        assert success is True
        assert response == SILENT_MARKER
        # Agent runner should NOT have been called because the
        # wake-gate returned wakeAgent=false
        assert called["n"] == 0


class TestBackgroundTicker:
    def test_start_stop(self, scheduler_module):
        from cron.scheduler import BackgroundTicker

        bt = BackgroundTicker(interval_seconds=1)
        bt.start()
        time.sleep(0.5)
        bt.stop(timeout=2.0)
        # BackgroundTicker must terminate cleanly; the daemon thread
        # doesn't expose a ``is_alive`` requirement post-stop but at
        # minimum we make sure stop() returned without raising.


class TestTickLock:
    def test_tick_skipped_under_lock(
        self, scheduler_module, tmp_home, clean_cron_dir, monkeypatch
    ):
        """If the .tick.lock is already held, tick returns 0 quickly."""
        from cron.scheduler import tick

        # Occupy the lock by hand.
        from cron.scheduler import _get_lock_paths

        _, lock_file = _get_lock_paths()
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        # Open and LOCK_EX the file for the duration of the test.
        try:
            import fcntl as _fcntl
        except ImportError:  # pragma: no cover
            _fcntl = None

        if _fcntl is not None:
            fd = open(lock_file, "w")
            _fcntl.flock(fd, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
            try:
                assert tick(verbose=False, sync=True) == 0
            finally:
                _fcntl.flock(fd, _fcntl.LOCK_UN)
                fd.close()
        else:
            # On platforms without fcntl (Windows, in CI), the cross-
            # process lock is a no-op; tick runs.  Accept either.
            tick(verbose=False, sync=True)


# =============================================================================
# Scheduler: tick + delivery hook
# =============================================================================


class TestTickDispatch:
    def test_tick_runs_due_jobs(
        self, scheduler_module, jobs_module, tmp_home, clean_cron_dir
    ):
        from cron.jobs import create_job, update_job
        from cron.scheduler import (
            clear_scheduler_hooks,
            set_scheduler_hooks,
            tick,
        )

        # Create a no_agent script job whose output is uniquely tagged.
        script = tmp_home / "scripts" / "tag.sh"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text(
            "#!/bin/sh\necho 'tick-ran-'$(date +%s)\n", encoding="utf-8"
        )
        job = create_job(
            prompt="ignored",
            schedule="every 1m",
            name="dispatch-test",
            script=str(script),
            no_agent=True,
        )
        update_job(
            job["id"],
            {"next_run_at": "2000-01-01T00:00:00+00:00"},
        )

        delivered = []
        set_scheduler_hooks(
            {"deliver": lambda j, c: delivered.append(c) or None}
        )
        try:
            n = tick(verbose=False, sync=True)
        finally:
            clear_scheduler_hooks()

        # Tick should have dispatched exactly our due job.
        assert n >= 1
        # Delivery hook fired (the script's stdout is non-empty)
        assert any("tick-ran-" in d for d in delivered), delivered

    def test_silence_suppressed_on_delivery(
        self, scheduler_module, jobs_module, tmp_home, clean_cron_dir
    ):
        from cron.jobs import create_job, update_job
        from cron.scheduler import (
            SILENT_MARKER,
            clear_scheduler_hooks,
            set_scheduler_hooks,
            tick,
        )

        # A wake-gate script returns SILENT equivalent → delivery suppressed.
        script = tmp_home / "scripts" / "silent_wake.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text(
            textwrap.dedent(
                """\
                import json
                print(json.dumps({"wakeAgent": False}))
                """
            ),
            encoding="utf-8",
        )
        job = create_job(
            prompt="real",
            schedule="every 1m",
            name="silent-dispatch",
            script=str(script),
        )
        update_job(
            job["id"],
            {"next_run_at": "2000-01-01T00:00:00+00:00"},
        )

        delivered = []
        # Stub the runner so we never need a real agent.
        os.environ["HANDSOME_AGENT_RUNNER"] = (
            "tests.unit.test_cron:never_called_runner"
        )
        set_scheduler_hooks(
            {"deliver": lambda j, c: delivered.append(c) or None}
        )
        try:
            tick(verbose=False, sync=True)
        finally:
            os.environ.pop("HANDSOME_AGENT_RUNNER", None)
            clear_scheduler_hooks()

        # Wake-gate fired → suppress delivery entirely.
        assert all(SILENT_MARKER not in d for d in delivered), delivered


def never_called_runner(prompt: str, job: dict):  # pragma: no cover
    raise AssertionError(
        "agent runner must NOT be called when wake-gate is false"
    )


# =============================================================================
# Advisor-reviewed coverage (Hermes parity gaps)
# =============================================================================


class TestCronParseShape:
    """Cron expressions that the legacy regex used to reject."""

    def test_named_month(self, jobs_module):
        from cron.jobs import parse_schedule, HAS_CRONITER

        if not HAS_CRONITER:
            pytest.skip("croniter not installed")
        sched = parse_schedule("0 9 * * MON")
        assert sched["kind"] == "cron"
        assert sched["expr"] == "0 9 * * MON"

    def test_six_field_seconds(self, jobs_module):
        from cron.jobs import parse_schedule, HAS_CRONITER

        if not HAS_CRONITER:
            pytest.skip("croniter not installed")
        sched = parse_schedule("*/15 * * * * *")
        assert sched["kind"] == "cron"
        assert sched["expr"] == "*/15 * * * * *"

    def test_at_alias_daily(self, jobs_module):
        from cron.jobs import parse_schedule, HAS_CRONITER

        if not HAS_CRONITER:
            pytest.skip("croniter not installed")
        sched = parse_schedule("@daily")
        assert sched["kind"] == "cron"
        assert sched["expr"] == "@daily"

    def test_step_range(self, jobs_module):
        from cron.jobs import parse_schedule, HAS_CRONITER

        if not HAS_CRONITER:
            pytest.skip("croniter not installed")
        sched = parse_schedule("0 9-17/2 * * *")
        assert sched["kind"] == "cron"

    def test_bare_date_now_rejected(self, jobs_module):
        """A bare `2026-12-31` must NOT slip through as a one-shot —
        it is ambiguous (which zone's midnight?)."""
        from cron.jobs import parse_schedule

        with pytest.raises(ValueError):
            parse_schedule("2026-12-31")

    def test_iso_with_z_suffix(self, jobs_module):
        from cron.jobs import parse_schedule

        # ISO 8601 with Z suffix is interpreted as UTC; just make sure
        # the schedule parses and has the expected kind.
        parsed = parse_schedule("2027-01-02T03:04:05Z")
        assert parsed["kind"] == "once"
        assert parsed["run_at"].endswith("+00:00")

    def test_at_every_recurring_alias(self, jobs_module):
        """`@every 5m` (Hermes-style alias) must parse as recurring interval."""
        from cron.jobs import parse_schedule

        parsed = parse_schedule("@every 5m")
        assert parsed["kind"] == "interval"
        assert parsed["minutes"] == 5

    def test_at_alone_rejected(self, jobs_module):
        from cron.jobs import parse_schedule

        with pytest.raises(ValueError):
            parse_schedule("@")


class TestPathEscape:
    """Output-dir path sandbox."""

    @pytest.mark.parametrize(
        "bad_id",
        [
            "../escape",
            "..",
            ".",
            "sub/file",
            "C:colon",
            "\x00abc",
        ],
    )
    def test_job_output_dir_rejects(
        self, jobs_module, tmp_home, bad_id
    ):
        from cron.jobs import _job_output_dir

        with pytest.raises(ValueError):
            _job_output_dir(bad_id)


class TestTickAsyncContract:
    def test_tick_async_returns_dispatched_count(
        self, scheduler_module, jobs_module, tmp_home, clean_cron_dir
    ):
        from cron.jobs import create_job, update_job
        from cron.scheduler import (
            clear_scheduler_hooks,
            set_scheduler_hooks,
            tick,
        )

        # Make two jobs both immediately due.
        j1 = create_job(
            prompt="x", schedule="every 1m", name="async-1"
        )
        j2 = create_job(
            prompt="x", schedule="every 1m", name="async-2"
        )
        update_job(
            j1["id"], {"next_run_at": "2000-01-01T00:00:00+00:00"}
        )
        update_job(
            j2["id"], {"next_run_at": "2000-01-01T00:00:00+00:00"}
        )

        # Use a stub deliver hook so the script body short-circuits the
        # agent runner (agent runner is irrelevant for this test).
        set_scheduler_hooks({"deliver": lambda j, c: None})
        try:
            n = tick(verbose=False, sync=False)
            assert n == 2  # dispatched, not completed
        finally:
            clear_scheduler_hooks()


class TestWorkdirValidation:
    def test_relative_workdir_rejected(
        self, jobs_module, tmp_home, clean_cron_dir
    ):
        with pytest.raises(ValueError):
            jobs_module.create_job(
                prompt="x", schedule="every 1m", workdir="relative/path"
            )

    def test_nonexistent_workdir_rejected(
        self, jobs_module, tmp_home, clean_cron_dir
    ):
        with pytest.raises(ValueError):
            jobs_module.create_job(
                prompt="x",
                schedule="every 1m",
                workdir=str(tmp_home / "does-not-exist"),
            )


class TestToolsetScopeRestore:
    """`_run_agent_prompt` must restore prior toolset scope even on failure."""

    def test_restore_on_failure(self, jobs_module, scheduler_module,
                                 tmp_home, clean_cron_dir,
                                 monkeypatch):
        from cron.jobs import create_job

        prior = ["interactive-tool-a"]
        applied = {"after": None, "restored": None}

        def fake_agent_factory(llm_provider=None, **kwargs):
            raise RuntimeError("boom (LLM not configured)")

        # Provide a stub both for the import + factory.
        class FakeAgent:
            def __init__(self, *a, **kw):
                pass

            async def chat(self, user_input: str):
                raise RuntimeError("boom")

        import sys as _sys
        agent_stub = _sys.modules.setdefault(
            "agent.agent", type(_sys)("agent.agent")
        )
        agent_stub.Agent = FakeAgent  # type: ignore[attr-defined]

        sel_stub = _sys.modules.setdefault(
            "agent.tool_selector.llm_tool_selector",
            type(_sys)("agent.tool_selector.llm_tool_selector"),
        )

        def get_enabled_toolsets():
            return prior if applied["restored"] is None else applied["restored"]

        def set_enabled_toolsets(value):
            if not applied["after"]:
                applied["after"] = list(value)
            else:
                applied["restored"] = list(value)

        sel_stub.get_enabled_toolsets = get_enabled_toolsets  # type: ignore[attr-defined]
        sel_stub.set_enabled_toolsets = set_enabled_toolsets  # type: ignore[attr-defined]

        scheduler_module.set_scheduler_hooks({})
        job = create_job(
            prompt="x",
            schedule="every 1m",
            name="scope-restore",
            enabled_toolsets=["cron-only"],
        )
        try:
            ok, doc, response, error = scheduler_module.run_job(
                {**job, "workdir": None}
            )
            assert ok is False
            # Either the runtime guard or the scope-restore fired.
            assert applied["after"] == ["cron-only"]
            # After the run, prior toolset was restored.
            assert applied["restored"] == prior
        finally:
            # Clean up the stubs so we don't pollute later imports.
            for mod in ("agent.agent", "agent.tool_selector.llm_tool_selector"):
                _sys.modules.pop(mod, None)


class TestCronCliRemove:
    """`handsome cron remove <ref>` must resolve by name and respect --yes."""

    def _ns(self, **overrides):
        from cli.cli_commands import cron as cli_cron

        parser = cli_cron.build_parser()
        args = parser.parse_args(["remove", "stub-id"])
        for k, v in overrides.items():
            setattr(args, k, v)
        return args

    def test_resolves_name(self, jobs_module, tmp_home, clean_cron_dir,
                           monkeypatch):
        from cli.cli_commands import cron as cli_cron
        from cron.jobs import create_job, get_job, list_jobs

        job = create_job(
            prompt="hello",
            schedule="every 1m",
            name="by-name-target",
        )

        args = self._ns(job_id="by-name-target", yes=True)
        rc = cli_cron.cmd_remove(args)
        assert rc == 0
        assert get_job(job["id"]) is None
        assert all(j["id"] != job["id"] for j in list_jobs())

    def test_unknown_ref_with_yes_returns_error(self, jobs_module, tmp_home,
                                                clean_cron_dir, monkeypatch):
        from cli.cli_commands import cron as cli_cron

        args = self._ns(job_id="definitely-not-here", yes=True)
        # remove_job returns False → CLI returns 1, not blocking on stdin.
        rc = cli_cron.cmd_remove(args)
        assert rc == 1

    def test_ambiguous_name_returns_rc4(self, jobs_module, tmp_home,
                                        clean_cron_dir, monkeypatch,
                                        capsys):
        from cli.cli_commands import cron as cli_cron
        from cron.jobs import create_job
        import json as _json

        create_job(prompt="a", schedule="every 1m", name="dup-name")
        create_job(prompt="b", schedule="every 1m", name="dup-name-2")
        jobs_module._refresh_paths()
        # Force the same name on both jobs to trigger AmbiguousJobReference.
        data = _json.loads(jobs_module.JOBS_FILE.read_text(encoding="utf-8"))
        for entry in data["jobs"]:
            entry["name"] = "dup-name"
        jobs_module.JOBS_FILE.write_text(
            _json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        args = self._ns(job_id="dup-name", yes=True)
        rc = cli_cron.cmd_remove(args)
        captured = capsys.readouterr()
        assert rc == 4
        assert "ambiguous" in (captured.out + captured.err).lower()
