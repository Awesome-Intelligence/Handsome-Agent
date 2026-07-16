"""Cron job scheduling subsystem for Agent-Z.

🚪 Access - 🔧 System - Scheduled job execution
🧠 Decision - ⏰ Scheduler - Persistent timed work

Ported from Hermes's ``cron/`` package.
Provides scheduled-task execution — jobs run from a persistent JSON store
under ``$AGENT_Z_HOME/cron/`` and are dispatched by a background ticker
invoked from the gateway daemon (or directly via
``agentz cron tick``).

Three schedule kinds are supported:

  * ``once`` — one-shot ISO timestamp
  * ``interval`` — recurring ``every Nm|Nh|Nd``
  * ``cron``   — standard 5- or 6-field cron expression (requires
                 ``croniter``).

Two execution modes:

  * ``prompt`` — LLM-backed agent run (default)
  * ``script`` — classic watchdog (``--no-agent --script <path>``)

A file lock on ``<AGENT_Z_HOME>/cron/.tick.lock`` serializes tick()
across processes so concurrent gateway / CLI invocations cannot
double-fire.
"""

from cron.jobs import (
    JOBS_FILE,
    AmbiguousJobReference,
    create_job,
    get_job,
    get_due_jobs,
    list_jobs,
    load_jobs,
    mark_job_run,
    pause_job,
    remove_job,
    resolve_job_id,
    resolve_job_ref,
    resume_job,
    save_job_output,
    trigger_job,
    update_job,
)
from cron.lifecycle_guard import (
    GatewayLifecycleBlocked,
    check_gateway_lifecycle,
    contains_gateway_lifecycle_command,
)
from cron.scheduler import (
    BackgroundTicker,
    run_job,
    run_one_job,
    set_scheduler_hooks,
    clear_scheduler_hooks,
    tick,
)

__all__ = [
    "JOBS_FILE",
    "AmbiguousJobReference",
    "create_job",
    "get_job",
    "get_due_jobs",
    "list_jobs",
    "load_jobs",
    "mark_job_run",
    "pause_job",
    "remove_job",
    "resolve_job_id",
    "resolve_job_ref",
    "resume_job",
    "save_job_output",
    "trigger_job",
    "update_job",
    "tick",
    "run_one_job",
    "run_job",
    "BackgroundTicker",
    "set_scheduler_hooks",
    "clear_scheduler_hooks",
    "GatewayLifecycleBlocked",
    "check_gateway_lifecycle",
    "contains_gateway_lifecycle_command",
]
