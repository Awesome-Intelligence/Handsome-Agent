#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cron command — scheduled job management.

🚪 Access - 💬 CLI - Cron job lifecycle
🧠 Decision - ⏰ Scheduler - CLI surface

Subcommands:
  list          — show registered jobs (default + disabled)
  show <id>     — show one job in detail
  create        — register a new scheduled task (prompt / --script mode)
  remove <id>   — delete a job and prune its output dir
  pause <id>    — pause without deleting
  resume <id>   — re-arm a paused job
  trigger <id>  — run on the next tick
  run <id>      — execute NOW synchronously (CI / manual run)
  tick          — one scheduler tick (test / manual)
  status        — service / heartbeat overview

Backed by the ``cron/`` Python package — single source of truth for
state. CLI commands are thin wrappers around the public API
(``cron.create_job`` etc.).
"""

# Copyright © 2026 Handsome Agent Contributors.
# Licensed under the MIT license. See LICENSE for details.

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from cron.jobs import (
    JOBS_FILE,
    AmbiguousJobReference,
    create_job as _create_job_api,
    get_job,
    get_ticker_heartbeat_age,
    get_ticker_success_age,
    list_jobs,
    pause_job,
    remove_job,
    resolve_job_ref,
    resolve_job_id,
    resume_job,
    trigger_job,
    update_job,
)
from cron.lifecycle_guard import GatewayLifecycleBlocked
from cron.scheduler import run_one_job, tick as scheduler_tick

from common.i18n import t
from common.logging_manager import get_access_logger
from common.terminal.colors import Colors, color
from common.terminal.ui import (
    print_error,
    print_header,
    print_info,
    print_success,
    print_warning,
)


_LOG = get_access_logger("cli.cron")


def _table(jobs: List[Dict[str, Any]]) -> None:
    if not jobs:
        print_info(t("cron.empty", fallback="No cron jobs configured"))
        print_info(
            t(
                "cron.empty_hint",
                fallback="Use 'handsome cron create' to add one",
            )
        )
        return

    header = (
        f"  {color('ID', Colors.BOLD):<14} "
        f"{color('STATE', Colors.BOLD):<10} "
        f"{color('SCHEDULE', Colors.BOLD):<22} "
        f"{color('MODE', Colors.BOLD):<10} "
        f"{color('NAME', Colors.BOLD)}"
    )
    print(color(header, Colors.DIM))
    print(color("  " + "-" * 90, Colors.DIM))

    for job in jobs:
        marker = "⏸ " if not job.get("enabled", True) else "  "
        if job.get("state") == "paused":
            marker = "⏸ "
        state_color = Colors.AVOCADO_BRIGHT if job.get("enabled", True) else Colors.DIM
        mode = "script" if job.get("no_agent") else "agent"
        print(
            f"{color(marker, Colors.DIM)}"
            f"{color(job.get('id', '?')[:12], Colors.AVOCADO_BRIGHT):<14} "
            f"{color(job.get('state', '?'), state_color):<10} "
            f"{color(job.get('schedule_display', '?'), Colors.AVOCADO):<22} "
            f"{color(mode, Colors.MAGENTA):<10} "
            f"{job.get('name', '')[:40]}"
        )

    print()
    print_info(
        t(
            "cron.total",
            fallback="Total: {n} job(s); {a} active, {p} paused",
        ).format(
            n=len(jobs),
            a=sum(1 for j in jobs if j.get("enabled", True)),
            p=sum(1 for j in jobs if not j.get("enabled", True)),
        )
    )


def cmd_list(args: argparse.Namespace) -> int:
    include_disabled = bool(getattr(args, "all", False))
    jobs = list_jobs(include_disabled=include_disabled)
    print_header(
        t("cron.list_header", fallback="⏰ Cron Job Registry")
    )

    if getattr(args, "json", False):
        print(json.dumps({"jobs": jobs}, indent=2, ensure_ascii=False))
        return 0

    _table(jobs)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    ref = args.job_id
    try:
        job = resolve_job_ref(ref)
    except AmbiguousJobReference as exc:  # pragma: no cover - surfaced later
        print_error(
            t(
                "cron.ambiguous",
                fallback=(
                    "Multiple jobs named '{ref}' — use the ID instead. "
                    "Matches: {ids}"
                ),
            ).format(ref=exc.ref, ids=", ".join(m["id"] for m in exc.matches))
        )
        return 4
    if not job:
        print_error(
            t(
                "cron.not_found",
                fallback="Cron job not found: {id}",
            ).format(id=ref)
        )
        return 1

    print_header(
        t(
            "cron.show_header",
            fallback="⏰ Job {id}",
        ).format(id=job.get("id", "?"))
    )

    if getattr(args, "json", False):
        print(json.dumps(job, indent=2, ensure_ascii=False))
        return 0

    rows = [
        ("ID", job.get("id", "?")),
        ("Name", job.get("name", "")),
        ("State", job.get("state", "?")),
        ("Enabled", job.get("enabled", True)),
        (
            "Schedule",
            job.get("schedule_display")
            or json.dumps(job.get("schedule", {}), ensure_ascii=False),
        ),
        ("Mode", "script (no_agent)" if job.get("no_agent") else "agent"),
        ("Prompt", (job.get("prompt") or "")[:200]),
        ("Script", job.get("script") or "—"),
        ("Repeat", job.get("repeat", {})),
        ("Next run at", job.get("next_run_at") or "—"),
        ("Last run at", job.get("last_run_at") or "—"),
        ("Last status", job.get("last_status") or "—"),
        ("Last error", job.get("last_error") or "—"),
        ("Last delivery error", job.get("last_delivery_error") or "—"),
        ("Created at", job.get("created_at") or "—"),
        ("Deliver", job.get("deliver") or "—"),
        ("Origin", job.get("origin") or "—"),
        ("Workdir", job.get("workdir") or "—"),
        ("Toolsets", job.get("enabled_toolsets") or "—"),
        ("Skills", job.get("skills") or []),
        ("Model", job.get("model") or "—"),
        ("Provider", job.get("provider") or "—"),
    ]
    for label, value in rows:
        print(f"  {color(label + ':', Colors.BOLD)} {value}")
    print()
    return 0


def cmd_create(args: argparse.Namespace) -> int:
    schedule = args.schedule
    prompt = args.prompt
    no_agent = bool(getattr(args, "no_agent", False))
    script = getattr(args, "script", None)

    if no_agent and not script:
        print_error(
            t(
                "cron.no_agent_needs_script",
                fallback="--no-agent requires --script <path>",
            )
        )
        return 2

    if (not prompt) and (not no_agent):
        print_error(
            t(
                "cron.prompt_required",
                fallback="Provide either a --prompt or --script (with --no-agent)",
            )
        )
        return 2

    if getattr(args, "json", False):
        pass  # tolerated; always print result below as json when requested

    name = getattr(args, "name", None)
    repeat = getattr(args, "repeat", None)
    deliver = getattr(args, "deliver", None)
    skill = getattr(args, "skill", None)
    skills = (
        [s.strip() for s in getattr(args, "skills", []) if s.strip()]
        if getattr(args, "skills", None)
        else None
    )
    workdir = getattr(args, "workdir", None)

    try:
        job = _create_job_api(
            prompt=prompt,
            schedule=schedule,
            name=name,
            repeat=repeat,
            deliver=deliver,
            skill=skill,
            skills=skills,
            script=script,
            no_agent=no_agent,
            workdir=workdir,
        )
    except GatewayLifecycleBlocked as exc:
        print_error(str(exc))
        return 3
    except ValueError as exc:
        print_error(
            t(
                "cron.create_invalid",
                fallback="Invalid cron job: {err}",
            ).format(err=exc)
        )
        return 2

    print_success(
        t(
            "cron.created",
            fallback="✓ Created cron job {id} ({name})",
        ).format(id=job["id"], name=job.get("name", "?"))
    )
    print_info(
        t(
            "cron.next_run",
            fallback="Next run: {when}",
        ).format(when=job.get("next_run_at") or "?")
    )
    if getattr(args, "json", False):
        print(json.dumps({"job": job}, indent=2, ensure_ascii=False))
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    raw_ref = args.job_id
    try:
        job_id = resolve_job_id(raw_ref)
    except AmbiguousJobReference as exc:
        print_error(str(exc))
        return 4

    if job_id is None and not getattr(args, "yes", False) and not _confirm(
        t(
            "cron.remove_confirm_unknown",
            fallback="No job named '{id}' — remove anyway?",
        ).format(id=raw_ref)
    ):
        return 1

    removed = remove_job(job_id)
    if not removed:
        print_error(
            t(
                "cron.remove_failed",
                fallback="Failed to remove job {id}",
            ).format(id=raw_ref)
        )
        return 1

    print_success(
        t(
            "cron.removed",
            fallback="✓ Removed job {id}",
        ).format(id=job_id)
    )
    return 0


def cmd_pause(args: argparse.Namespace) -> int:
    try:
        job_id = resolve_job_id(args.job_id)
    except AmbiguousJobReference as exc:
        print_error(str(exc))
        return 4
    if not job_id:
        print_error(
            t(
                "cron.not_found",
                fallback="Cron job not found: {id}",
            ).format(id=args.job_id)
        )
        return 1
    job = pause_job(job_id, reason=getattr(args, "reason", None))
    if not job:
        print_error(
            t(
                "cron.not_found",
                fallback="Cron job not found: {id}",
            ).format(id=args.job_id)
        )
        return 1
    print_success(
        t(
            "cron.paused",
            fallback="⏸ Paused job {id}",
        ).format(id=args.job_id)
    )
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    try:
        job_id = resolve_job_id(args.job_id)
    except AmbiguousJobReference as exc:
        print_error(str(exc))
        return 4
    if not job_id:
        print_error(
            t(
                "cron.not_found",
                fallback="Cron job not found: {id}",
            ).format(id=args.job_id)
        )
        return 1
    job = resume_job(job_id)
    if not job:
        print_error(
            t(
                "cron.not_found",
                fallback="Cron job not found: {id}",
            ).format(id=args.job_id)
        )
        return 1
    print_success(
        t(
            "cron.resumed",
            fallback="▶ Resumed job {id} (next run: {when})",
        ).format(
            id=args.job_id,
            when=job.get("next_run_at") or "?",
        )
    )
    return 0


def cmd_trigger(args: argparse.Namespace) -> int:
    try:
        job_id = resolve_job_id(args.job_id)
    except AmbiguousJobReference as exc:
        print_error(str(exc))
        return 4
    if not job_id:
        print_error(
            t(
                "cron.not_found",
                fallback="Cron job not found: {id}",
            ).format(id=args.job_id)
        )
        return 1
    job = trigger_job(job_id)
    if not job:
        print_error(
            t(
                "cron.not_found",
                fallback="Cron job not found: {id}",
            ).format(id=args.job_id)
        )
        return 1
    print_success(
        t(
            "cron.triggered",
            fallback="🚀 Triggered job {id} for next tick",
        ).format(id=args.job_id)
    )
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    try:
        job = resolve_job_ref(args.job_id)
    except AmbiguousJobReference as exc:
        print_error(
            t(
                "cron.ambiguous",
                fallback=(
                    "Multiple jobs named '{ref}' — use the ID instead. "
                    "Matches: {ids}"
                ),
            ).format(
                ref=exc.ref, ids=", ".join(m["id"] for m in exc.matches)
            )
        )
        return 4
    if not job:
        print_error(
            t(
                "cron.not_found",
                fallback="Cron job not found: {id}",
            ).format(id=args.job_id)
        )
        return 1

    print_header(
        t(
            "cron.run_header",
            fallback="▶ Running {id} synchronously",
        ).format(id=args.job_id)
    )

    ok = run_one_job(job, verbose=bool(getattr(args, "verbose", False)))
    print_success(
        t(
            "cron.run_done",
            fallback="Job {id} completed (status={ok})",
        ).format(id=args.job_id, ok="ok" if ok else "error")
    )
    return 0 if ok else 1


def cmd_tick(args: argparse.Namespace) -> int:
    verbose = bool(getattr(args, "verbose", True))
    n = scheduler_tick(verbose=verbose, sync=True)
    print_info(
        t(
            "cron.tick_done",
            fallback="Tick executed {n} job(s)",
        ).format(n=n)
    )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    print_header(
        t("cron.status_header", fallback="📊 Cron Status")
    )

    jobs = list_jobs(include_disabled=True)
    active = [j for j in jobs if j.get("enabled", True)]
    paused = [j for j in jobs if not j.get("enabled", True)]

    heartbeat_age = get_ticker_heartbeat_age()
    success_age = get_ticker_success_age()

    print(f"  {color('Jobs file:', Colors.BOLD)} {JOBS_FILE}")
    print(
        f"  {color('Jobs registered:', Colors.BOLD)} {len(jobs)}"
        f" ({color(len(active), Colors.AVOCADO_BRIGHT)} active,"
        f" {color(len(paused), Colors.DIM)} paused)"
    )

    if heartbeat_age is None:
        print_warning(
            t(
                "cron.no_heartbeat",
                fallback="No ticker heartbeat recorded. Run 'handsome cron tick' or start the gateway daemon.",
            )
        )
    else:
        age_str = _format_age(heartbeat_age)
        print(
            f"  {color('Ticker heartbeat:', Colors.BOLD)} "
            f"{age_str} ago"
        )
        if success_age is not None:
            print(
                f"  {color('Last successful tick:', Colors.BOLD)} "
                f"{_format_age(success_age)} ago"
            )

    recent = [
        j
        for j in jobs
        if j.get("last_run_at")
    ]
    recent.sort(key=lambda j: j.get("last_run_at") or "", reverse=True)
    if recent:
        print()
        print(color("  Recent runs:", Colors.BOLD))
        for j in recent[:5]:
            ts = j.get("last_run_at", "")[:19].replace("T", " ")
            status_color = (
                Colors.GREEN
                if j.get("last_status") == "ok"
                else Colors.RED
            )
            print(
                f"    {color(ts, Colors.DIM)} "
                f"{color(j.get('last_status', '?'), status_color)} "
                f"{j.get('id', '?')[:12]} {j.get('name', '')}"
            )

    return 0


def _format_age(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        return f"{int(seconds // 60)}m{int(seconds % 60)}s"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h{int((seconds % 3600) // 60)}m"
    return f"{int(seconds // 86400)}d{int((seconds % 86400) // 3600)}h"


def _confirm(question: str) -> bool:
    """Tiny y/N interactive confirmation. Falls back to False on EOF."""
    try:
        ans = input(f"{question} [y/N] ").strip().lower()
        return ans in {"y", "yes"}
    except EOFError:
        return False


# ---------------------------------------------------------------------------
# argparse wiring
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the ``handsome cron`` subparser.

    Wired into :mod:`cli.main`; also usable standalone (see ``__main__``).
    """
    parser = argparse.ArgumentParser(
        prog="handsome cron",
        description=t(
            "cron.parser_description",
            fallback="Manage scheduled (cron) jobs.",
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    sub = parser.add_subparsers(dest="cron_command", required=True)

    # list
    list_p = sub.add_parser(
        "list",
        help=t("cron.help.list", fallback="List registered jobs"),
    )
    list_p.add_argument(
        "--all",
        action="store_true",
        help=t(
            "cron.help.list_all",
            fallback="Include paused/disabled jobs",
        ),
    )
    list_p.add_argument(
        "--json",
        action="store_true",
        help=t("cron.help.json", fallback="Output JSON"),
    )
    list_p.set_defaults(func=cmd_list)

    # show
    show_p = sub.add_parser(
        "show",
        help=t("cron.help.show", fallback="Show one job"),
    )
    show_p.add_argument("job_id", help="Job ID (or unique name)")
    show_p.add_argument(
        "--json",
        action="store_true",
        help=t("cron.help.json", fallback="Output JSON"),
    )
    show_p.set_defaults(func=cmd_show)

    # create
    create_p = sub.add_parser(
        "create",
        help=t("cron.help.create", fallback="Create a new cron job"),
    )
    create_p.add_argument(
        "schedule",
        help=(
            "Schedule: '30m', '2h', 'every 30m', '0 9 * * *', or "
            "ISO timestamp '2026-12-31T23:59'"
        ),
    )
    create_p.add_argument(
        "--prompt",
        help="Prompt to send to the agent (required unless --no-agent)",
    )
    create_p.add_argument(
        "--script",
        help="Run a script instead of the agent (use with --no-agent)",
    )
    create_p.add_argument(
        "--no-agent",
        action="store_true",
        help="Treat script output as the final response (no LLM)",
    )
    create_p.add_argument("--name", help="Friendly name (default: prompt snippet)")
    create_p.add_argument(
        "--repeat",
        type=int,
        default=None,
        help=(
            "Stop after N runs. Omit for recurring; for one-shots "
            "default is 1"
        ),
    )
    create_p.add_argument(
        "--deliver",
        default=None,
        help=(
            "Delivery target: 'local', 'origin', or "
            "'platform:chat_id'. Default: origin if set, else local"
        ),
    )
    create_p.add_argument(
        "--skill",
        action="append",
        default=None,
        help="Skill to load (repeat flag for multiple, legacy single-skill)",
    )
    create_p.add_argument(
        "--skills",
        action="append",
        default=None,
        help="Skill(s) to load (repeat flag, takes precedence over --skill)",
    )
    create_p.add_argument(
        "--workdir",
        default=None,
        help="Absolute path; AGENTS.md/skills/tools honour it",
    )
    create_p.add_argument(
        "--json",
        action="store_true",
        help="Print the created job as JSON",
    )
    create_p.set_defaults(func=cmd_create)

    # remove
    remove_p = sub.add_parser(
        "remove",
        help=t("cron.help.remove", fallback="Remove a job"),
    )
    remove_p.add_argument("job_id", help="Job ID or name")
    remove_p.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip interactive confirmation",
    )
    remove_p.set_defaults(func=cmd_remove)

    # pause
    pause_p = sub.add_parser(
        "pause",
        help=t("cron.help.pause", fallback="Pause a job"),
    )
    pause_p.add_argument("job_id", help="Job ID or name")
    pause_p.add_argument("--reason", default=None, help="Pause reason")
    pause_p.set_defaults(func=cmd_pause)

    # resume
    resume_p = sub.add_parser(
        "resume",
        help=t("cron.help.resume", fallback="Resume a paused job"),
    )
    resume_p.add_argument("job_id", help="Job ID or name")
    resume_p.set_defaults(func=cmd_resume)

    # trigger
    trigger_p = sub.add_parser(
        "trigger",
        help=t("cron.help.trigger", fallback="Trigger next-tick run"),
    )
    trigger_p.add_argument("job_id", help="Job ID or name")
    trigger_p.set_defaults(func=cmd_trigger)

    # run
    run_p = sub.add_parser(
        "run",
        help=t("cron.help.run", fallback="Run a job synchronously now"),
    )
    run_p.add_argument("job_id", help="Job ID or name")
    run_p.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logging",
    )
    run_p.set_defaults(func=cmd_run)

    # tick
    tick_p = sub.add_parser(
        "tick",
        help=t("cron.help.tick", fallback="Run one scheduler tick"),
    )
    tick_p.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="Verbose logging",
    )
    tick_p.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress per-tick info logs",
    )
    tick_p.set_defaults(func=cmd_tick)

    # status
    status_p = sub.add_parser(
        "status",
        help=t("cron.help.status", fallback="Service status / heartbeat"),
    )
    status_p.set_defaults(func=cmd_status)

    return parser


# Backward-compatible imperative functions (used by tests / main.py pre-parser)
def list_cron_jobs(json_output: bool = False) -> None:
    """Backward-compatible list helper used by ``handsome cron list``."""
    args = argparse.Namespace(all=False, json=json_output)
    sys.exit(cmd_list(args))


def check_cron_status() -> None:
    """Backward-compatible status helper used by ``handsome cron status``."""
    args = argparse.Namespace()
    sys.exit(cmd_status(args))


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
