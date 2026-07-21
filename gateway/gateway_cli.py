"""🚪 Access - 🚪Gateway - Gateway CLI 入口

Two mutually exclusive gateway modes are exposed:

* **HTTP mode** (original, default): runs the ``agent.acp.adapter`` HTTP server
  for ACP / webhook-style programmatic access.  This is what ``agentz serve``
  historically started.
* **Channel mode** (NEW, triggered with ``--channel-gateway`` / the
  ``channel-gateway`` subcommand): starts all configured messaging platform
  adapters (Feishu / WeCom / Weixin / Telegram / Discord / …) via the new
  :class:`gateway.run.GatewayRunner` minimal runtime.

Examples::

    # Default: HTTP gateway (ACP)
    python -m gateway.gateway_cli --port 8080

    # Channel gateway: chat platforms
    python -m gateway.gateway_cli --channel-gateway
    python -m gateway.gateway_cli channel-gateway run
    python -m gateway.gateway_cli channel-gateway list   # list adapters
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def parse_args(argv=None):
    """Parse command line arguments with two modes + a channel-gateway subparser."""
    parser = argparse.ArgumentParser(
        prog="agentz-gateway",
        description="Agent-Z Gateway (HTTP / channel-gateway modes)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # ── HTTP mode (default) ─────────────────────────────────────────
  python -m gateway.gateway_cli                     # ACP HTTP server
  python -m gateway.gateway_cli --port 8080
  python -m gateway.gateway_cli http --port 8080 --debug

  # ── Channel-gateway mode (chat platforms) ────────────────────────
  python -m gateway.gateway_cli --channel-gateway   # start Feishu/WeCom/...
  python -m gateway.gateway_cli channel-gateway run
  python -m gateway.gateway_cli channel-gateway list      # show installed platforms
  python -m gateway.gateway_cli channel-gateway status    # same, with env health
""",
    )
    # ── Mode flag (legacy compat) ──────────────────────────────────────
    parser.add_argument(
        "--channel-gateway",
        action="store_true",
        help="Run the messaging-platform gateway (Feishu/WeCom/…) instead of the HTTP server.",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="HTTP mode: listen address (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="HTTP mode: listen port (default: 8000)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    sub = parser.add_subparsers(dest="subcommand", title="Subcommands")

    # ── http subcommand ────────────────────────────────────────────────
    http_p = sub.add_parser("http", help="Run the HTTP/ACP gateway server")
    http_p.add_argument("--host", default="0.0.0.0")
    http_p.add_argument("--port", type=int, default=8000)
    http_p.add_argument("--debug", action="store_true")
    http_p.set_defaults(mode_override="http")

    # ── channel-gateway subcommand ────────────────────────────────────
    cg = sub.add_parser(
        "channel-gateway",
        help="Run the messaging-platform gateway (Feishu/WeCom/Telegram/…)",
    )
    cg_sub = cg.add_subparsers(dest="cg_action", title="channel-gateway actions")
    cg_run = cg_sub.add_parser("run", help="Start the gateway (default action)")
    cg_run.add_argument("--debug", action="store_true")
    cg_list = cg_sub.add_parser("list", help="List installed platform adapters")
    cg_status = cg_sub.add_parser("status", help="Show platform + env health status")
    cg_status.add_argument("--debug", action="store_true")
    cg.set_defaults(mode_override="channel-gateway")

    return parser.parse_args(argv)


# ── Mode helpers ─────────────────────────────────────────────────────


def _mode_from_args(args) -> str:
    explicit = getattr(args, "mode_override", None)
    if explicit == "channel-gateway" or getattr(args, "channel_gateway", False):
        return "channel-gateway"
    if explicit == "http" or not (explicit or getattr(args, "channel_gateway", False)):
        # Default: HTTP mode
        return "http"
    return explicit or "http"


def _cg_action(args) -> str:
    return getattr(args, "cg_action", None) or "run"


# ── Subcommand: channel-gateway list/status ──────────────────────────


def _cmd_list_platforms() -> int:
    from gateway.platforms import ensure_discovered, platform_registry

    ensure_discovered()
    entries = platform_registry.all_entries()
    if not entries:
        print("(no platform adapters are registered)")
        return 1
    print(f"Installed platform adapters ({len(entries)}):")
    for entry in sorted(entries, key=lambda e: e.name):
        deps_ok = False
        try:
            deps_ok = bool(entry.check_fn())
        except Exception:
            deps_ok = False
        deps_mark = "✅" if deps_ok else "❌ (deps missing)"
        req_env = (
            ", ".join(entry.required_env) if entry.required_env else "(none)"
        )
        hint = f" — install hint: {entry.install_hint}" if entry.install_hint and not deps_ok else ""
        print(
            f"  {entry.emoji or '🔌'} {entry.name:<22} {entry.label:<22} "
            f"{deps_mark}  required_env: {req_env}{hint}"
        )
    return 0


def _cmd_status() -> int:
    import os

    exit_code = _cmd_list_platforms()
    print()
    print("Detected gateway-relevant environment variables:")
    interesting = [
        "FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_BOT_TOKEN",
        "WECOM_APP_ID", "WECOM_APP_SECRET", "WECOM_TOKEN", "WECOM_ENCODING_AES_KEY",
        "WEIXIN_TOKEN", "WEIXIN_BASE_URL", "WEIXIN_ACCOUNT_ID",
        "TELEGRAM_BOT_TOKEN", "DISCORD_BOT_TOKEN",
        "SLACK_BOT_TOKEN", "WHATSAPP_CLOUD_ACCESS_TOKEN",
        "GATEWAY_ALLOW_ALL_USERS", "GATEWAY_ALLOWED_USERS",
    ]
    for key in sorted(set(interesting)):
        val = os.getenv(key)
        status = "set" if val else "unset"
        if val and len(val) > 8:
            status = f"set ({val[:4]}…{val[-2:]})"
        print(f"  {key:<44} {status}")

    # Quick check: any enablement signal present?
    any_signal = any(os.getenv(k) for k in interesting if k.endswith("_TOKEN") or k.endswith("_ID"))
    any_signal = any_signal or any(
        (os.getenv(k) for k in interesting if k.endswith("_APP_SECRET"))
    )
    print()
    if any_signal:
        print("→ At least one platform credential env var is present — the channel-gateway")
        print("  should pick up the platform automatically.")
    else:
        print("→ No platform credentials detected in the environment yet.")
        print("  Export the relevant variables or add `gateway.platforms.<name>:` entries")
        print("  in your config.yaml before starting the channel-gateway.")
    return exit_code


# ── Mode entry points ────────────────────────────────────────────────


async def _run_http_mode(args) -> int:
    host = getattr(args, "host", "0.0.0.0") or "0.0.0.0"
    port = int(getattr(args, "port", 8000) or 8000)
    logger = logging.getLogger("gateway.http")

    from agent.agent import create_agent_from_config

    agent = create_agent_from_config()
    if agent is None:
        logger.error("Agent not initialized — check LLM config")
        return 1
    from agent.acp.adapter import run_http_server

    await run_http_server(agent, host=host, port=port)
    return 0


async def _run_channel_gateway_mode() -> int:
    from gateway.run import GatewayRunner

    runner = GatewayRunner()
    return 0 if await runner.start() else 1


# ── Main ─────────────────────────────────────────────────────────────


async def _main_async(argv=None) -> int:
    args = parse_args(argv)
    log_level = logging.DEBUG if getattr(args, "debug", False) else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )

    mode = _mode_from_args(args)
    # 1. Subcommand shortcuts (list/status) don't need the async runtime
    if mode == "channel-gateway" and _cg_action(args) in ("list", "status"):
        return _cmd_list_platforms() if _cg_action(args) == "list" else _cmd_status()

    # 2. Async modes
    if mode == "channel-gateway":
        # Logging: silence noisy platform-import debug lines so the human
        # sees the "Starting Agent-Z Gateway" banner above the fold.
        logging.getLogger("gateway.platforms").setLevel(logging.INFO)
        return await _run_channel_gateway_mode()

    return await _run_http_mode(args)


def main(argv=None) -> int:
    try:
        return asyncio.run(_main_async(argv))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
