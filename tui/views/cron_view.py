"""
Cron-related Modal screens for the TUI sidebar.

🚪 Access - 💬 TUI - Cron modals
🧠 Decision - ⏰ Scheduler - TUI surface

Two Modal screens back the CronPane sidebar widget:

* :class:`CronCreateScreen`  — 3-field form to register a new scheduled job.
  Calls ``cron.create_job`` on submit and returns the new job's id to the
  caller via ``dismiss()``.
* :class:`CronDetailScreen`  — read-only detail view (metadata + last
  output excerpt). Triggered by pressing ``enter`` on a CronPane row.

Both modals follow the same defensive pattern as ``SkillDetailScreen``:
``try/except ImportError`` so the module loads even if Textual is missing
(degrade to a no-op class for unit tests / docs builds).
"""

# Copyright © 2026 Agent-Z Contributors.
# Licensed under the MIT license. See LICENSE for details.

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Any, Dict, List, Optional

# Textual imports — guarded so the module is importable headless.
try:
    from textual.app import ComposeResult
    from textual.screen import ModalScreen
    from textual.binding import Binding
    from textual.containers import Container, Horizontal, Vertical, VerticalScroll
    from textual.widgets import Button, Input, Label, Static, TextArea
    from textual import on
    TEXTUAL_AVAILABLE = True
except ImportError:  # pragma: no cover - textual not installed
    TEXTUAL_AVAILABLE = False

    class ModalScreen:  # type: ignore[no-redef]
        """Fallback ``ModalScreen`` used when textual is unavailable."""

    def ComposeResult(*_args, **_kwargs):  # type: ignore[no-redef]
        return None

    class _Stub:  # noqa: D401 - tiny stand-in
        def __init__(self, *a, **kw) -> None:
            pass

        def __getattr__(self, name):
            return _Stub()

        def __call__(self, *a, **kw):
            return _Stub()

    Binding = Input = Label = Static = TextArea = Button = _Stub  # type: ignore
    Container = Horizontal = Vertical = VerticalScroll = _Stub  # type: ignore
    on = lambda *_a, **_kw: (lambda f: f)  # type: ignore


# Local imports that always work (no textual dependency).
from common.i18n import t
from common.logging_manager import get_access_logger

_LOG = get_access_logger("tui.cron_view")


# ============================================================================
# Shared CSS
# ============================================================================


CRON_VIEW_CSS = """
CronCreateScreen, CronDetailScreen {
    align: center middle;
    background: $boost 40%;
}

CronCreateScreen #create-container,
CronDetailScreen #detail-container {
    width: 90%;
    height: auto;
    max-height: 90%;
    background: $surface 90%;
    border: solid $primary;
    padding: 0;
}

CronCreateScreen #create-header,
CronDetailScreen #detail-header {
    height: auto;
    padding: 0 1;
    background: $primary 20%;
    border-bottom: solid $primary;
}

CronCreateScreen #create-title,
CronDetailScreen #detail-title {
    text-style: bold;
    color: $primary;
    width: 100%;
    content-align: center middle;
}

CronCreateScreen #form-body {
    height: auto;
    padding: 1 2;
}

CronCreateScreen .form-row {
    height: auto;
    margin-bottom: 1;
}

CronCreateScreen .form-label {
    height: 1;
    color: $text-muted;
    margin-bottom: 0;
}

CronCreateScreen .form-hint {
    height: 1;
    color: $text-muted;
    text-style: italic;
    margin-top: 0;
}

CronCreateScreen #form-buttons {
    height: auto;
    align-horizontal: center;
    padding: 0 1 1 1;
}

CronCreateScreen #form-buttons Button {
    margin: 0 1;
}

CronCreateScreen #form-error {
    height: auto;
    color: $error;
    padding: 0 2 1 2;
}

CronDetailScreen #detail-body {
    height: 1fr;
    padding: 1;
}

CronDetailScreen #detail-output {
    height: auto;
    max-height: 16;
    border: solid $accent 30%;
    padding: 0 1;
    overflow-y: auto;
}

CronDetailScreen #detail-meta {
    height: auto;
    color: $text-muted;
    padding: 0 0 1 0;
}

CronDetailScreen #detail-footer {
    height: auto;
    align-horizontal: center;
    padding: 0 1 1 1;
}

CronDetailScreen #detail-footer Button {
    margin: 0 1;
}
"""


# ============================================================================
# CronCreateScreen
# ============================================================================


class CronCreateScreen(ModalScreen if TEXTUAL_AVAILABLE else object):
    """Three-field form to register a new cron job.

    Fields (all required):
      * ``name``     — display name (string)
      * ``schedule`` — duration / interval / cron expression / @alias
      * ``prompt``   — short LLM prompt (long prompts should use the CLI)

    On submit, calls :func:`cron.create_job` and dismisses with the
    resulting job id. On validation error, stays open and surfaces the
    message in the inline ``#form-error`` widget.
    """

    CSS = CRON_VIEW_CSS

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("ctrl+s", "submit", "Submit", show=True),
    ]

    PLACEHOLDER_SCHEDULE = "every 5m / @daily / 0 9 * * *"
    PLACEHOLDER_PROMPT = "summarise yesterday's commits"
    PLACEHOLDER_NAME = "daily-brief"

    def __init__(self, default_schedule: str = "", default_name: str = "", **kwargs):
        super().__init__(**kwargs)
        self._default_schedule = default_schedule
        self._default_name = default_name
        self._logger = _LOG

    def compose(self) -> ComposeResult:  # type: ignore[override]
        with Container(id="create-container"):
            yield Static(
                t("tui.cron.create_title", fallback="⏰ New Cron Job"),
                id="create-title",
            )
            with Vertical(id="form-body"):
                with Vertical(classes="form-row"):
                    yield Label(
                        t("tui.cron.field_name", fallback="Name"),
                        classes="form-label",
                    )
                    yield Input(
                        value=self._default_name,
                        placeholder=self.PLACEHOLDER_NAME,
                        id="input-name",
                    )
                with Vertical(classes="form-row"):
                    yield Label(
                        t("tui.cron.field_schedule", fallback="Schedule"),
                        classes="form-label",
                    )
                    yield Input(
                        value=self._default_schedule,
                        placeholder=self.PLACEHOLDER_SCHEDULE,
                        id="input-schedule",
                    )
                    yield Static(
                        t(
                            "tui.cron.field_schedule_hint",
                            fallback=(
                                "Duration (30m), interval (every 5m), "
                                "cron expr (0 9 * * *), or @alias (@daily, "
                                "@every 5m)"
                            ),
                        ),
                        classes="form-hint",
                    )
                with Vertical(classes="form-row"):
                    yield Label(
                        t("tui.cron.field_prompt", fallback="Prompt"),
                        classes="form-label",
                    )
                    yield TextArea(
                        text="",
                        id="input-prompt",
                    )
                yield Static("", id="form-error")
            with Horizontal(id="form-buttons"):
                yield Button(
                    t("tui.cron.submit", fallback="Create"),
                    id="btn-submit",
                    variant="primary",
                )
                yield Button(
                    t("tui.cron.cancel", fallback="Cancel"),
                    id="btn-cancel",
                    variant="default",
                )

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_submit(self) -> None:
        self._try_submit()

    @on(Button.Pressed, "#btn-submit")
    def _on_submit_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self._try_submit()

    @on(Button.Pressed, "#btn-cancel")
    def _on_cancel_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss(None)

    def _try_submit(self) -> None:
        name = self.query_one("#input-name", Input).value.strip()
        schedule = self.query_one("#input-schedule", Input).value.strip()
        prompt = self.query_one("#input-prompt", TextArea).text.strip()
        err = self.query_one("#form-error", Static)

        if not name:
            err.update(
                t("tui.cron.error_name_required", fallback="✗ Name is required")
            )
            return
        if not schedule:
            err.update(
                t("tui.cron.error_schedule_required", fallback="✗ Schedule is required")
            )
            return
        if not prompt:
            err.update(
                t("tui.cron.error_prompt_required", fallback="✗ Prompt is required")
            )
            return

        try:
            from cron import create_job  # local import: avoid heavy import in unit tests

            job = create_job(
                prompt=prompt,
                schedule=schedule,
                name=name,
            )
        except Exception as exc:  # ValueError, lifecycle_guard, etc.
            self._logger.warning("create_job failed: %s", exc)
            err.update(
                t(
                    "tui.cron.error_create_failed",
                    fallback="✗ Failed to create job: {err}",
                ).format(err=str(exc))
            )
            return

        self.dismiss(job.get("id") if isinstance(job, dict) else None)


# ============================================================================
# CronDetailScreen
# ============================================================================


class CronDetailScreen(ModalScreen if TEXTUAL_AVAILABLE else object):
    """Read-only detail modal for a single cron job.

    Renders schedule, state, last run info, and (if available) the
    most-recent output excerpt from ``$HANDSOME_HOME/cron/output/<id>/``.
    """

    CSS = CRON_VIEW_CSS

    BINDINGS = [
        Binding("escape", "close", "Close", show=True),
    ]

    def __init__(self, job: Dict[str, Any], **kwargs):
        super().__init__(**kwargs)
        self._job = job
        self._logger = _LOG

    def compose(self) -> ComposeResult:  # type: ignore[override]
        job = self._job
        with Container(id="detail-container"):
            yield Static(
                t("tui.cron.detail_title", fallback="⏰ Cron Job Detail"),
                id="detail-title",
            )
            with Vertical(id="detail-body"):
                yield Static(self._format_meta(job), id="detail-meta")
                yield Static(
                    self._format_output_excerpt(job),
                    id="detail-output",
                    markup=False,
                )
            with Horizontal(id="detail-footer"):
                yield Button(
                    t("tui.cron.close", fallback="Close"),
                    id="btn-close",
                    variant="primary",
                )

    def action_close(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#btn-close")
    def _on_close_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss(None)

    # ------------------------------------------------------------------
    # Formatting helpers (also exercised by unit tests)
    # ------------------------------------------------------------------

    @staticmethod
    def _format_meta(job: Dict[str, Any]) -> str:
        """Build the metadata block (id / name / state / schedule / next)."""
        schedule = job.get("schedule", {}) or {}
        schedule_disp = schedule.get("display") or str(schedule.get("kind", "—"))
        state = job.get("state", "—")
        enabled = job.get("enabled", True)
        next_run = job.get("next_run_at") or "—"
        last_run = job.get("last_run_at") or "—"
        last_status = job.get("last_status") or "—"
        last_error = (job.get("last_error") or "").strip() or "—"
        job_id = job.get("id", "—")
        name = job.get("name") or "(unnamed)"

        lines = [
            f"ID:        {job_id}",
            f"Name:      {name}",
            f"State:     {state}{'' if enabled else ' (disabled)'}",
            f"Schedule:  {schedule_disp}",
            f"Next run:  {next_run}",
            f"Last run:  {last_run}",
            f"Last stat: {last_status}",
            f"Last err:  {last_error}",
        ]
        return "\n".join(lines)

    @staticmethod
    def _format_output_excerpt(
        job: Dict[str, Any],
        *,
        max_lines: int = 8,
        max_chars: int = 600,
    ) -> str:
        """Return a truncated excerpt of the most-recent output file.

        Falls back to a friendly "no output yet" string when no run has
        produced a markdown file yet.
        """
        try:
            output_dir = _resolve_output_dir(job.get("id", ""))
        except Exception:
            return t(
                "tui.cron.no_output",
                fallback="(no output yet)",
            )
        if output_dir is None or not output_dir.exists():
            return t(
                "tui.cron.no_output",
                fallback="(no output yet)",
            )
        try:
            # Sort by *filename* rather than mtime: filenames in this
            # subsystem are ISO-8601 timestamps (e.g.
            # ``2026-07-14T00-00-00.md``), so lexical sort == chronological
            # sort, and is immune to FS mtime drift on rapid successive runs.
            files = sorted(
                (p for p in output_dir.glob("*.md") if p.is_file()),
                key=lambda p: p.name,
                reverse=True,
            )
        except OSError:
            return t("tui.cron.no_output", fallback="(no output yet)")
        if not files:
            return t("tui.cron.no_output", fallback="(no output yet)")
        try:
            text = files[0].read_text(encoding="utf-8", errors="replace")
        except OSError:
            return t("tui.cron.no_output", fallback="(no output yet)")

        text = text.strip()
        if not text:
            return t("tui.cron.no_output", fallback="(no output yet)")
        truncated = "\n".join(text.splitlines()[:max_lines])
        if len(truncated) > max_chars:
            truncated = truncated[:max_chars] + "…"
        return f"[dim]— {files[0].name} —[/dim]\n{truncated}"


# ============================================================================
# Helpers (shared by both modals + tests)
# ============================================================================


def _resolve_output_dir(job_id: str) -> Optional[Path]:
    """Resolve ``$HANDSOME_HOME/cron/output/<job_id>/`` without importing the
    full :mod:`cron` package (keeps this module headless-test friendly).
    """
    if not job_id:
        return None
    import os as _os
    from pathlib import Path as _P

    home = _os.environ.get("HANDSOME_HOME")
    if not home:
        try:
            from common.config import HANDSOME_HOME  # type: ignore
            home = str(HANDSOME_HOME)
        except Exception:
            home = str(_P.home() / ".handsome_agent")
    return _P(home) / "cron" / "output" / job_id


def format_next_run_delta(next_run_at: Optional[str]) -> str:
    """Render a friendly 'next run in X' suffix for the sidebar.

    Returns ``""`` when ``next_run_at`` is missing or unparseable.
    Negative deltas (i.e. overdue) render as ``"(due now)"`` — useful for
    callers that want to highlight overdue jobs.
    """
    if not next_run_at:
        return ""
    try:
        # Tolerate trailing "Z" by swapping to "+00:00".
        normalized = next_run_at.replace("Z", "+00:00")
        target = _dt.datetime.fromisoformat(normalized)
    except ValueError:
        return ""
    now = _dt.datetime.now(target.tzinfo) if target.tzinfo else _dt.datetime.now()
    delta = target - now
    secs = int(delta.total_seconds())
    if secs <= 0:
        return "(due now)"
    if secs < 60:
        return f"in {secs}s"
    if secs < 3600:
        return f"in {secs // 60}m {secs % 60:02d}s"
    if secs < 86400:
        h, rem = divmod(secs, 3600)
        return f"in {h}h {rem // 60:02d}m"
    days, rem = divmod(secs, 86400)
    return f"in {days}d {rem // 3600}h"


__all__ = [
    "CronCreateScreen",
    "CronDetailScreen",
    "format_next_run_delta",
    "CRON_VIEW_CSS",
]
