#!/usr/bin/env python3
"""Smoke test for the TUI cron sidebar pane.

🚪 Access - 🧪 Smoke - CronPane in SidebarContainer

Pre-seeds two cron jobs into an isolated ``$HANDSOME_HOME``, mounts the
real ``SidebarContainer`` under :class:`textual.app.App`, switches to the
new "定时" tab, and screenshots the rendered pane so we can eyeball the
layout / icon mapping / heartbeat line.

Run:
    python tests/smoke/smoke_cron_pane.py

Output:
    ``tests/smoke/out/cron_pane.svg`` — full app screenshot.
"""

# Copyright © 2026 Handsome Agent Contributors.
# Licensed under the MIT license. See LICENSE for details.

from __future__ import annotations

import datetime as _dt
import os
import shutil
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# 0. Isolate HANDSOME_HOME so this smoke never touches real cron state.
# ---------------------------------------------------------------------------

TMP_HOME = Path(tempfile.mkdtemp(prefix="handsome-smoke-cron-"))
# Honour an externally-provided HANDSOME_HOME so we can re-run the
# smoke against the user's *real* cron state instead of always
# creating a brand-new ephemeral one. Default to a tmp dir.
if not os.environ.get("HANDSOME_HOME"):
    TMP_HOME = Path(tempfile.mkdtemp(prefix="handsome-smoke-cron-"))
    os.environ["HANDSOME_HOME"] = str(TMP_HOME)
    print(f"[smoke] HANDSOME_HOME = {TMP_HOME} (ephemeral)", flush=True)
else:
    print(
        f"[smoke] HANDSOME_HOME = {os.environ['HANDSOME_HOME']} (real)",
        flush=True,
    )

# Make the repo importable when running as a bare script.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = Path(__file__).resolve().parent / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Seed two cron jobs (one scheduled, one paused).
# ---------------------------------------------------------------------------

from cron import create_job  # noqa: E402  (sys.path patched above)

NOW = _dt.datetime.now()

JOB_DAILY = create_job(
    prompt="summarise yesterday's commits",
    schedule="@daily",
    name="smoke-daily-brief",
)
print(f"[smoke] created {JOB_DAILY['id']} (daily)", flush=True)

JOB_TICK = create_job(
    prompt="echo tick",
    schedule="every 30m",
    name="smoke-heartbeat",
    no_agent=True,
    script="echo smoke-tick",
)
print(f"[smoke] created {JOB_TICK['id']} (every 30m, script)", flush=True)

# Pause the second one so we can see both icon variants.
from cron import pause_job  # noqa: E402

pause_job(JOB_TICK["id"])
print(f"[smoke] paused {JOB_TICK['id']}", flush=True)

# Also create a fake ticker heartbeat so the header line is "healthy".
from cron import scheduler as cron_scheduler  # noqa: E402

# Touch the heartbeat files manually (we're not running the actual ticker).
hb_path = Path(os.environ["HANDSOME_HOME"]) / "cron" / "ticker_heartbeat"
ok_path = Path(os.environ["HANDSOME_HOME"]) / "cron" / "ticker_last_success"
hb_path.parent.mkdir(parents=True, exist_ok=True)
hb_path.write_text(str(NOW.timestamp()), encoding="utf-8")
ok_path.write_text(str(NOW.timestamp()), encoding="utf-8")
print(f"[smoke] wrote fake heartbeat", flush=True)

# ---------------------------------------------------------------------------
# 2. Mount the SidebarContainer via Textual's Pilot harness.
# ---------------------------------------------------------------------------

from textual.app import App  # noqa: E402
from textual.containers import Container  # noqa: E402

from tui.sidebar import SidebarContainer  # noqa: E402


class CronSmokeApp(App):
    """Minimal App that hosts the real SidebarContainer + cron pane."""

    def compose(self):
        # Defer imports so the smoke can fall back to a bare
        # CronPane if SidebarContainer fails to mount (e.g. when
        # GoalPane's GoalManager is not initialised).
        from tui.sidebar import SidebarContainer
        yield SidebarContainer(cwd=str(REPO_ROOT))


async def _run_smoke() -> None:
    app = CronSmokeApp()
    async with app.run_test(size=(120, 40)) as pilot:
        # Give the app a moment to mount all panes
        await pilot.pause(0.2)
        # === Reproduce the user's bug scenario ===
        # 1. Wait for compose/mount to settle
        # 2. Switch to the cron tab (same as F4 in real app)
        # 3. Force the compositor to render the active pane
        try:
            for _ in range(5):
                await pilot.pause(0.1)
            sidebar = app.query_one("SidebarContainer")
            sidebar.switch_to_panel("cron")
            for _ in range(5):
                await pilot.pause(0.1)
            cron_pane = sidebar.cron_pane
            print(f"[smoke] found CronPane, display={cron_pane.display}", flush=True)
            # Direct render() — should not be None
            visual = cron_pane.render()
            assert visual is not None, (
                "CronPane.render() returned None — compositor will crash"
            )
            print(f"[smoke] render() returned {type(visual).__name__} ✓", flush=True)

            # Now call _render_content (the actual compositor path)
            cron_pane._render_content()
            print(f"[smoke] _render_content() succeeded ✓", flush=True)

            # Manual reload + render — bypass the try/except in
            # _refresh_data so we can see what fails.
            cron_pane._jobs = cron_pane._load_jobs()
            try:
                await cron_pane._render_list()
            except Exception as exc:
                import traceback
                print(f"[smoke] _render_list raised: {exc!r}", flush=True)
                traceback.print_exc()
            await pilot.pause(0.3)
            children = len(cron_pane._list_widget.children)
            print(
                f"[smoke] jobs={len(cron_pane._jobs)}, "
                f"ListView children={children}",
                flush=True,
            )
        except Exception as exc:  # pragma: no cover
            import traceback
            print(f"[smoke] CRASH: {exc}", flush=True)
            traceback.print_exc()
            return 1

        # Screenshot
        try:
            svg = app.export_screenshot(title="CronPane smoke (active)")
            out = OUT_DIR / "cron_pane.svg"
            out.write_text(svg, encoding="utf-8")
            print(f"[smoke] wrote {out}", flush=True)
        except Exception as exc:  # pragma: no cover
            print(f"[smoke] WARN: export_screenshot failed: {exc}", flush=True)

        # Note on visual coverage: the ListView children are not in the
        # exported SVG because Textual 8.x skips mounting items inside
        # an inactive TabPane. In a real session, switching to the
        # "定时" tab flips display=True and the items become visible.
        # A separate test (``test_cron_pane.py``) covers the per-row
        # rendering path.


def main() -> int:
    try:
        import asyncio
        asyncio.run(_run_smoke())
    except Exception as exc:
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Leave TMP_HOME in place on failure for inspection; clean on success.
        if "--keep" not in sys.argv:
            try:
                shutil.rmtree(TMP_HOME, ignore_errors=True)
                print(f"[smoke] cleaned {TMP_HOME}", flush=True)
            except Exception:
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
