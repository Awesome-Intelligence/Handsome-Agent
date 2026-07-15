"""Unit tests for the cron sidebar pane.

🚪 Access - 🧪 Tests - TUI cron pane

Covers:
  * :func:`tui.views.cron_view.format_next_run_delta`  - relative time
    formatting (in Xs / Xm / Xh / Xd, plus overdue '(due now)').
  * :meth:`CronDetailScreen._format_meta`  - meta block rendering
    (id / name / state / schedule / next / last / error).
  * :meth:`CronDetailScreen._format_output_excerpt`  - reads most-recent
    ``*.md`` under ``$HANDSOME_HOME/cron/output/<id>/`` and truncates.
  * :mod:`common.locales` i18n key coverage  - all ``tui.cron.*`` keys
    are present in all four catalogs (zh / en / ja / ko).

All tests run hermetically: ``$HANDSOME_HOME`` is redirected to a tmpdir.
Textual is required to import the view module, so tests are skipped
when the library is not installed (e.g. minimal CI image).
"""

# Copyright © 2026 Handsome Agent Contributors.
# Licensed under the MIT license. See LICENSE for details.

from __future__ import annotations

import datetime as _dt
import os
import sys
from pathlib import Path

import pytest

TEXTUAL_AVAILABLE = True
try:
    import textual  # noqa: F401
except ImportError:  # pragma: no cover
    TEXTUAL_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not TEXTUAL_AVAILABLE,
    reason="textual not installed",
)

if TEXTUAL_AVAILABLE:
    from tui.views.cron_view import (
        CronCreateScreen,
        CronDetailScreen,
        format_next_run_delta,
    )


# ============================================================================
# format_next_run_delta
# ============================================================================


class TestFormatNextRunDelta:
    """Relative-time formatter used by CronPane list rows."""

    def test_none_returns_empty(self):
        assert format_next_run_delta(None) == ""
        assert format_next_run_delta("") == ""

    def test_unparseable_returns_empty(self):
        assert format_next_run_delta("not-an-iso-string") == ""

    def test_seconds(self):
        now = _dt.datetime.now()
        target = now + _dt.timedelta(seconds=42)
        out = format_next_run_delta(target.isoformat(timespec="seconds"))
        # Allow ±1s slack — clock may advance between target and format.
        assert out in ("in 42s", "in 41s")

    def test_minutes_and_seconds(self):
        now = _dt.datetime.now()
        target = now + _dt.timedelta(minutes=3, seconds=5)
        out = format_next_run_delta(target.isoformat(timespec="seconds"))
        # Either exact (3m 05s) or a second earlier (3m 04s).
        assert out in ("in 3m 05s", "in 3m 04s", "in 3m 03s")

    def test_hours_and_minutes(self):
        now = _dt.datetime.now()
        target = now + _dt.timedelta(hours=2, minutes=15)
        out = format_next_run_delta(target.isoformat(timespec="seconds"))
        assert out.startswith("in 2h ")

    def test_days_and_hours(self):
        now = _dt.datetime.now()
        target = now + _dt.timedelta(days=3, hours=4)
        out = format_next_run_delta(target.isoformat(timespec="seconds"))
        assert out.startswith("in 3d ")

    def test_overdue_marker(self):
        now = _dt.datetime.now()
        target = now - _dt.timedelta(minutes=5)
        out = format_next_run_delta(target.isoformat(timespec="seconds"))
        assert out == "(due now)"

    def test_z_suffix_normalised(self):
        # Trailing Z is swapped to +00:00 by the formatter.
        now = _dt.datetime.now(_dt.timezone.utc)
        target = now + _dt.timedelta(seconds=30)
        out = format_next_run_delta(target.isoformat(timespec="seconds").replace("+00:00", "Z"))
        # ±1s slack — formatter may run a fraction after target is sampled.
        assert out in ("in 30s", "in 29s")


# ============================================================================
# _format_meta
# ============================================================================


class TestDetailFormatMeta:
    """CronDetailScreen._format_meta builds a multi-line label."""

    def test_minimal_job(self):
        job = {"id": "abc123", "name": "demo", "schedule": {"display": "@daily"}}
        text = CronDetailScreen._format_meta(job)
        # Required lines
        for must in ("ID:", "abc123", "demo", "@daily", "Next run:"):
            assert must in text

    def test_includes_last_error(self):
        job = {
            "id": "x",
            "schedule": {"display": "every 5m"},
            "state": "scheduled",
            "last_status": "error",
            "last_error": "boom",
        }
        text = CronDetailScreen._format_meta(job)
        assert "boom" in text
        assert "error" in text

    def test_disabled_state_marker(self):
        job = {"id": "x", "schedule": {"display": "x"}, "enabled": False}
        text = CronDetailScreen._format_meta(job)
        assert "(disabled)" in text

    def test_blank_error_dashes(self):
        job = {"id": "x", "schedule": {"display": "x"}, "last_error": "  "}
        text = CronDetailScreen._format_meta(job)
        # blank error renders as a dash, not the raw whitespace
        assert "Last err:  —" in text


# ============================================================================
# _format_output_excerpt
# ============================================================================


class TestDetailFormatOutputExcerpt:
    """CronDetailScreen._format_output_excerpt reads from
    ``$HANDSOME_HOME/cron/output/<id>/``."""

    def test_no_output_dir_returns_placeholder(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HANDSOME_HOME", str(tmp_path))
        job = {"id": "no-such-job"}
        out = CronDetailScreen._format_output_excerpt(job)
        assert "no output" in out.lower() or "暂无" in out or "出力" in out or "출력" in out

    def test_empty_dir_returns_placeholder(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HANDSOME_HOME", str(tmp_path))
        (tmp_path / "cron" / "output" / "empty-job").mkdir(parents=True)
        out = CronDetailScreen._format_output_excerpt({"id": "empty-job"})
        # The text below covers all four languages.
        assert (
            "no output" in out.lower()
            or "暂无" in out
            or "出力" in out
            or "출력" in out
        )

    def test_reads_most_recent_md(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HANDSOME_HOME", str(tmp_path))
        out_dir = tmp_path / "cron" / "output" / "happy-job"
        out_dir.mkdir(parents=True)
        # Two files; ensure the newer one is picked
        (out_dir / "2025-01-01T00-00-00.md").write_text(
            "old run\nignored", encoding="utf-8"
        )
        (out_dir / "2026-07-14T00-00-00.md").write_text(
            "fresh run\nsecond line\nthird", encoding="utf-8"
        )
        out = CronDetailScreen._format_output_excerpt({"id": "happy-job"})
        assert "fresh run" in out
        assert "old run" not in out

    def test_truncates_long_excerpt(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HANDSOME_HOME", str(tmp_path))
        out_dir = tmp_path / "cron" / "output" / "long-job"
        out_dir.mkdir(parents=True)
        long_body = "x" * 5000
        (out_dir / "2026-07-14T00-00-00.md").write_text(
            long_body, encoding="utf-8"
        )
        out = CronDetailScreen._format_output_excerpt(
            {"id": "long-job"}, max_lines=2, max_chars=120
        )
        # The body is limited; the function appends "…" when truncated.
        assert out.endswith("…")
        # Body length should be bounded by max_chars + a small wrapper.
        assert len(out) < 400

    def test_path_escape_safe(self, tmp_path, monkeypatch):
        """Job IDs with traversal tokens must not escape the output dir."""
        monkeypatch.setenv("HANDSOME_HOME", str(tmp_path))
        out = CronDetailScreen._format_output_excerpt({"id": "../escape"})
        # The function never raises; falls back to placeholder.
        assert "no output" in out.lower() or "暂无" in out or "出力" in out or "출력" in out


# ============================================================================
# i18n key coverage
# ============================================================================


REQUIRED_KEYS = {
    "summary",
    "empty",
    "help_hint",
    "heartbeat_idle",
    "heartbeat_stale",
    "heartbeat_healthy",
    "created_notify",
    "paused",
    "resumed",
    "triggered",
    "removed",
    "error_no_selection",
    "error_cron_unavailable",
    "error_op_failed",
    "error_modal_unavailable",
    "create_title",
    "detail_title",
    "close",
    "submit",
    "cancel",
    "field_name",
    "field_schedule",
    "field_schedule_hint",
    "field_prompt",
    "error_name_required",
    "error_schedule_required",
    "error_prompt_required",
    "error_create_failed",
    "no_output",
}


class TestI18nKeyCoverage:
    """All four catalogs must define every ``tui.cron.*`` key."""

    @pytest.mark.parametrize("locale", ["zh", "en", "ja", "ko"])
    def test_all_keys_present(self, locale):
        from common.i18n import _load_catalog
        # Force a fresh load to pick up any disk changes.
        from common.i18n import _catalog_cache
        _catalog_cache.pop(locale, None)
        flat = _load_catalog(locale)
        # Build dotted-prefix set: "tui.cron.summary" etc.
        cron_keys = {k for k in flat.keys() if k.startswith("tui.cron.")}
        # Strip the prefix; required_keys are the suffix only.
        present = {k.split(".", 2)[2] for k in cron_keys}
        missing = REQUIRED_KEYS - present
        assert not missing, f"Missing tui.cron keys in {locale}: {missing}"

    def test_zh_fallback_when_key_absent(self, monkeypatch):
        """``t(key, fallback=...)`` must surface the fallback string when
        the key is missing in the active catalog — protects against
        accidentally renaming a key in one locale but not the others.
        """
        from common.i18n import t

        out = t("tui.cron.does_not_exist", fallback="my-fallback")
        assert out == "my-fallback"


# ============================================================================
# CronCreateScreen contract
# ============================================================================


class TestCreateScreenContract:
    """Spot-checks for the create screen (no Textual driver required)."""

    def test_default_invariants(self):
        screen = CronCreateScreen()
        # No accidental state pollution from defaults.
        assert screen._default_schedule == ""
        assert screen._default_name == ""
        # Bindings expose escape + ctrl+s
        keys = {b.key for b in screen.BINDINGS}
        assert "escape" in keys
        assert "ctrl+s" in keys

    def test_prefilled_defaults(self):
        screen = CronCreateScreen(default_name="seed", default_schedule="@daily")
        assert screen._default_name == "seed"
        assert screen._default_schedule == "@daily"


class TestCronPaneRenderContract:
    """Regression tests for compositor crash on first activation.

    Earlier versions of :class:`CronPane` did not override ``_render``,
    and a sibling business method also named ``_render`` returned
    ``None`` — the compositor then crashed with::

        AttributeError: 'NoneType' object has no attribute 'render_strips'

    We now override ``_render()`` to return a real ``Blank`` Visual
    *and* deliberately keep the business renderer named
    ``_render_widgets`` so the two can't accidentally shadow each
    other. These tests pin both contracts.
    """

    def test_render_returns_non_none(self):
        """``Widget._render()`` (the compositor path) must return a
        real Visual — never ``None``.

        Earlier the same name ``_render`` was used for a *business*
        helper that returned ``None``, which silently overrode the
        textual base method and crashed the compositor. This test
        pins the contract.
        """
        from tui.sidebar import CronPane
        from textual.visual import Visual

        pane = CronPane()
        # NOTE: assert via the private name — that's the actual
        # compositor entry point. Public ``render()`` is only used
        # as an input to ``visualize``.
        rendered = pane._render()
        if rendered is None:
            raise AssertionError(
                "CronPane._render() returned None — compositor will crash"
            )
        if not isinstance(rendered, Visual):
            raise AssertionError(
                f"CronPane._render() returned {type(rendered).__name__}, "
                "expected a Visual subclass"
            )

    def test_cron_pane_does_not_shadow_widget_render(self):
        """Direct contract: ``CronPane._render`` is the inherited one
        from ``Widget`` (or our Blank override), *not* the business
        ``_render_widgets`` helper. If somebody re-introduces a
        business method called ``_render`` later, this catches it.
        """
        from tui.sidebar import CronPane
        from textual.widget import Widget

        # Walk the MRO and assert that the *only* ``_render`` method
        # we encounter is either our explicit override or Widget's
        # base implementation. If some intervening class defines a
        # business ``_render`` that returns ``None``, the compositor
        # will crash — this test fails fast.
        widget_render = Widget._render
        for klass in CronPane.__mro__:
            if klass is object:
                continue
            render = klass.__dict__.get("_render")
            if render is None:
                continue
            # Must be either our explicit Blank-returning override
            # or the textual Widget base. Anything else means a class
            # is shadowing the contract.
            if render is widget_render:
                continue  # this is the textual base
            # Our override: verify it actually returns a Visual.
            from textual.renderables.blank import Blank
            from textual.visual import Visual
            self_render_obj = klass._render  # bound via __get__
            from tui.sidebar import CronPane
            pane = CronPane()
            result = pane._render()
            if not isinstance(result, Visual):
                raise AssertionError(
                    f"{klass.__name__}._render returned "
                    f"{type(result).__name__}, expected a Visual — "
                    "this is the same class of bug that crashed the "
                    "compositor earlier. Rename to _render_widgets."
                )

    def test_render_does_not_raise_on_repeated_calls(self):
        from tui.sidebar import CronPane

        pane = CronPane()
        for _ in range(3):
            rendered = pane.render()
            if rendered is None:
                raise AssertionError(
                    "CronPane.render() returned None on repeated calls"
                )

    def test_row_classes_split_properly_for_set_classes(self):
        """Regression test for the "blank cron pane" bug.

        Earlier ``_render_list`` called ``item.set_class(True, classes)``
        with a multi-class string like ``"cron-row paused"``. The
        singular :meth:`Widget.set_class` treats the entire string as
        one class name and rejects the space, raising ``WidgetError``.
        That exception was swallowed by the ``_refresh_data`` try/except,
        so the ``ListItem`` was never mounted and the pane rendered as
        empty even though ``_jobs`` had been loaded.

        We now use :meth:`Widget.set_classes` (plural), which accepts a
        multi-class string and splits on whitespace. This test pins
        ``_row_classes`` to keep the multi-class format so a future
        drive-by refactor can't accidentally fall back to the broken
        ``set_class`` API.
        """
        from tui.sidebar import CronPane

        pane = CronPane()
        # A paused job
        paused_row = pane._row_classes(
            {"enabled": False, "state": "paused", "last_status": None}
        )
        if " " not in paused_row:
            # Only one class — no spaces — but we WANT to test the
            # multi-class path that previously broke the pane. If the
            # output no longer contains whitespace, the contract
            # below is vacuously satisfied but the test pins nothing —
            # so we mark this as a hard failure of intent.
            raise AssertionError(
                "CronPane._row_classes no longer returns multi-class "
                "string — the set_class vs set_classes contract test "
                "is meaningless. Update the test alongside the code."
            )
        parts = paused_row.split()
        # Every part must be a valid CSS identifier (only letters,
        # digits, underscores, hyphens — no spaces).
        for part in parts:
            if not part.replace("-", "").replace("_", "").isalnum():
                raise AssertionError(
                    f"_row_classes produced a part with invalid "
                    f"identifier: {part!r}"
                )

    def test_row_classes_does_not_pass_to_singular_set_class(self):
        """Static analysis: scan ``_render_list`` for the broken
        ``set_class(True, ...)`` call pattern that previously swallowed
        :class:`WidgetError` and left the pane blank.

        Any future regression to the bug ("blank cron pane") would
        re-introduce this line; this test fails fast.
        """
        import re

        from tui.sidebar import SidebarContainer

        src_file = SidebarContainer.__module__.replace(".", "/") + ".py"
        import os

        import tui.sidebar as mod

        path = mod.__file__
        if path is None or not os.path.exists(path):
            raise AssertionError("Can't locate tui/sidebar.py for static check")
        text = open(path, encoding="utf-8").read()
        # Match ``.set_class(True, `` anywhere — this is the pattern
        # that's known to break with multi-class strings.
        if re.search(r"\.set_class\(\s*True\s*,", text):
            raise AssertionError(
                "tui/sidebar.py contains a `.set_class(True, …)` call. "
                "The singular set_class rejects multi-class strings "
                "(e.g. 'cron-row paused') with WidgetError. Use "
                "`set_classes(...)` for multi-class strings, or "
                "`set_class(True, 'name1', 'name2', ...)` for explicit "
                "class names."
            )
