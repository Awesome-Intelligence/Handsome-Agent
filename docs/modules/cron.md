# Cron subsystem — scheduled jobs

🚪 **Access** - 🔧 System - Timed work dispatcher
🧠 **Decision** - ⏰ Scheduler - Persistent, recurring, and one-shot job execution

The `cron/` package implements Agent-Z's scheduled-task layer,
ported in full from Hermes's `cron/` package. Jobs are stored as JSON in
`$AGENT_Z_HOME/cron/jobs.json`, executed either by the gateway daemon
or on-demand via `agentz cron tick`.

## What it does

- Registers schedules that fire **prompt** runs (LLM-backed) or **script**
  runs (no LLM, watchdog-style).
- Three schedule kinds: `once` (ISO timestamp), `interval` (e.g.
  `every 30m`), and `cron` expressions (e.g. `0 9 * * *`).
- Pauses / resumes / triggers / deletes jobs with positional CLI.
- Records per-run output under `$AGENT_Z_HOME/cron/output/<id>/`.
- Serialises ticks with a cross-process file lock so concurrent gateway
  and CLI invocations never double-fire.
- Enforces a **gateway-lifecycle guard** that blocks cron jobs that
  would invoke `agentz gateway restart|stop`, launchctl / systemctl
  ops on a hermes-gateway label, or `pkill` against the gateway —
  preventing an agent-driven SIGTERM-respawn loop (#32754).

## File layout

| Path | Purpose |
|------|---------|
| `cron/__init__.py` | Re-exports public API; sets up backward-compatible `tick` symbol. |
| `cron/jobs.py` | JSON storage, CRUD, schedule parsing, due-job selection, output saving. |
| `cron/scheduler.py` | `tick()`, `run_one_job`, `run_job`, pool management, BackgroundTicker. |
| `cron/lifecycle_guard.py` | Hard-block on `hermes_gateway` / `launchctl` / `systemctl` / `pkill` commands. |
| `cli/cli_commands/cron.py` | Sub-parser for `agentz cron ...`. |

## CLI quick reference

```bash
# Register a new job
agentz cron create 'every 30m' \
    --prompt 'Summarise session activity' \
    --name 'session-digest'

# Register a one-shot
agentz cron create '2026-12-31T23:30' \
    --prompt 'Happy new year kickoff'

# Register a watchdog-style script (no LLM)
agentz cron create 'every 1m' \
    --no-agent --script backup.sh \
    --name 'nightly-backup'

# Inspect
agentz cron list
agentz cron list --all --json
agentz cron show pinger

# Lifecycle
agentz cron pause pinger --reason 'manual hold'
agentz cron resume pinger
agentz cron trigger pinger   # fire on next tick
agentz cron run pinger       # fire NOW synchronously
agentz cron remove pinger

# Operations
agentz cron tick              # run one scheduler tick (sync)
agentz cron status            # service heartbeat + recent runs
```

## On-disk schema

`$AGENT_Z_HOME/cron/jobs.json` is a JSON object:

```json
{
  "jobs": [
    {
      "id": "ab12cd34ef56",
      "name": "session-digest",
      "prompt": "Summarise session activity",
      "skills": [],
      "skill": null,
      "model": null,
      "provider": null,
      "provider_snapshot": null,
      "model_snapshot": null,
      "base_url": null,
      "script": null,
      "no_agent": false,
      "context_from": null,
      "schedule": {"kind": "interval", "minutes": 30, "display": "every 30m"},
      "schedule_display": "every 30m",
      "repeat": {"times": null, "completed": 0},
      "enabled": true,
      "state": "scheduled",
      "paused_at": null,
      "paused_reason": null,
      "created_at": "2026-07-13T22:00:03.364653+08:00",
      "next_run_at": "2026-07-13T22:30:03+08:00",
      "last_run_at": null,
      "last_status": null,
      "last_error": null,
      "last_delivery_error": null,
      "deliver": "local",
      "origin": null,
      "enabled_toolsets": null,
      "workdir": null
    }
  ],
  "updated_at": "2026-07-13T22:00:03.364653+08:00"
}
```

The per-run output lives under
`$AGENT_Z_HOME/cron/output/<job_id>/<timestamp>.md`; retention is
controlled by `cron.output_retention` in `config.yaml` (default 50).

## Execution flow

1. CLI / gateway invokes `tick()`.
2. `tick()` acquires `<AGENT_Z_HOME>/cron/.tick.lock` (cross-process
   fcntl/msvcrt; falls back to in-process lock when neither is present).
3. `get_due_jobs()` reads `jobs.json` (in `_jobs_lock`) and returns
   jobs whose `next_run_at <= now()`. Stale recurring slots are
   fast-forwarded to the next future occurrence to avoid backlog
   bursts.
4. `advance_next_run()` advances `next_run_at` for recurring jobs
   before dispatch, so a mid-run crash never re-fires the same job.
5. Each due job is dispatched to either:
   - the **persistent parallel pool** (workdir-less jobs), or
   - the **persistent sequential pool** (workdir jobs that mutate
     process-global `os.environ["TERMINAL_CWD"]`).
6. `run_one_job()` runs the body and saves output:
   - **no_agent** short-circuit: the script's stdout is delivered
     verbatim (or saved silently when empty / `wakeAgent=false`).
   - **agent** path: `agent.agent.Agent.chat(prompt)` (or a custom
     `AGENTZ_RUNNER` override).
7. `mark_job_run()` updates `last_run_at`, `last_status`, increments
   `repeat.completed`, and auto-deletes finite one-shots.

## Hooks adapter

`set_scheduler_hooks({...})` lets a host process (gateway, daemon)
inject:

| Hook | Signature | When |
|------|-----------|------|
| `deliver` | `(job, content) -> error_str_or_None` | Final delivery |
| `pre_run` | `(job) -> None` | Before agent invocation |
| `post_run` | `(job, success, output, error) -> None` | After `mark_job_run` |

All hooks are best-effort and never raise into the runner.

## Tests

`tests/unit/test_cron.py` covers schedule parsing, CRUD, due-job
selection, lifecycle_guard, script + agent paths, scheduler tick lock,
and dispatch hooks. Run with:

```bash
pytest tests/unit/test_cron.py -v
```

## Configuration knobs

| Key | Default | Effect |
|-----|---------|--------|
| `cron.output_retention` | 50 | Per-job output file cap (newest N kept). |
| `cron.max_parallel_jobs` | unbounded | Cap on the persistent parallel pool size. |
| `cron.script_timeout` | 300s | Hard timeout for `no_agent` scripts. |
| `cron.mirror_delivery` | false | Reserved for cross-platform delivery hook. |
| `AGENTZ_CRON_MAX_PARALLEL` | unset | Env override for parallel-pool ceiling. |
| `AGENTZ_AGENT_RUNNER` | unset | Custom runner override (`module:callable`). |
| `AGENTZ_TZ` | system | IANA timezone used by `now()`. |

## Operational notes

- The first tick is automatically invoked by the gateway daemon; for
  manual testing run `agentz cron tick` while the daemon is down.
- One-shot jobs with `repeat=1` auto-delete on completion.
- The output directory is secure (chmod 0o700 / 0o600 on POSIX); the
  same protections apply to `jobs.json`. This is enforced because
  cron output can contain LLM responses that may quote secrets /
  user input.
- `remove_job()` also `shutil.rmtree`s the job's output directory;
  legacy unsafe IDs (`../escape` etc.) fail closed without deleting.

## Onboarding cheat-sheet

- `agentz cron` alone (no sub-command) prints the same output as
  `agentz cron list`. The dispatcher in `cli/main.py` rewrites
  the empty case to `list` for back-compat.
- `agentz cron --help` will **not** show the sub-command list — the
  top-level parser only sees a free-form `cron_args`. Run
  `agentz cron list --help`, `agentz cron create --help`, etc.
  to discover per-sub-command flags.
- `no_agent` script jobs run with no LLM cost. They work even when
  `agentz setup` has never been run, because they never touch the
  Agent runner.
- Agent-backed jobs require `llm.provider` + `llm.model` to be set
  (via `agentz setup` or directly in `config.yaml`). When missing,
  the cron reports `Cron agent has no LLM configured` instead of a
  bare traceback.
- Cron schedules use `croniter` (`'*/15 * * * * *'`, `'@daily'`,
  `'0 9 * * MON'` all parse).
- The `tick(sync=False)` mode returns the number of jobs *dispatched*
  (not completed); `tick(sync=True)` blocks until they finish.

## Known gaps vs Hermes

The following Hermes-only features are intentionally deferred and
landed via the `set_scheduler_hooks({...})` seam — wired up by future
gateway integration work:

| Feature | Status | Hook |
|---------|--------|------|
| Per-platform delivery (Telegram, Discord, etc.) | **Not wired** in default `agentz` run; cron saves output to disk + sends `delivery_error` empty. | `deliver(job, content)` |
| Mirror cron delivery into the user chat session | **Not wired** | `post_run` |
| Profile secret scope for the cron agent | **Not wired** | `pre_run` |
| MCP orphan subprocess sweep | **Not wired** | `pre_run` / `post_run` |
| Prompt-injection scan on the assembled prompt | **Not wired** | wrap `_run_agent_prompt` |
| `claim_dispatch` CAS pre-claim for crash safety (#38758) | **Not implemented** — use `AGENTZ_CRON_MAX_PARALLEL=1` to bound re-fire risk |

Operators that need these today should install a gateway hook
adapter separately — see `cron.scheduler.set_scheduler_hooks`.

