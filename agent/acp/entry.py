#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACP Entry Point.

CLI entry point for the Handsome Agent ACP adapter.

Usage::

    python -m agent.acp.entry
    handsome-acp
"""

# 🧠 Decision - 💾 Memory - ACP Entry Point

import argparse
import asyncio
import logging
import sys
from pathlib import Path


def _setup_logging() -> None:
    """Route all logging to stderr so stdout stays clean for ACP stdio."""
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # Quiet down noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)


def _load_env() -> None:
    """Load .env from config directory."""
    try:
        from common.config import get_config_dir
        config_dir = get_config_dir()
        env_file = config_dir / ".env"
        if env_file.exists():
            from dotenv import load_dotenv
            load_dotenv(env_file)
            logging.getLogger(__name__).info(f"Loaded env from {env_file}")
    except Exception as e:
        logging.getLogger(__name__).debug(f"Could not load .env: {e}")


def _parse_args(argv: list = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="handsome-acp",
        description="Run Handsome Agent as an ACP stdio server.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print Handsome Agent version and exit"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify ACP dependencies and adapter imports, then exit"
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run interactive setup for ACP terminal auth"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to for HTTP transport"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8002,
        help="Port to listen on for HTTP transport"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport type"
    )
    return parser.parse_args(argv)


def _print_version() -> None:
    """Print the version."""
    try:
        from common import __version__
        print(__version__)
    except Exception:
        print("1.0.0")


def _run_check() -> None:
    """Verify ACP dependencies and imports."""
    try:
        from agent.acp import ACPServer
        from agent.acp.session import SessionManager
        from agent.acp.auth import build_auth_methods
        from agent.acp.permissions import PermissionManager
        from agent.acp.tools import get_tool_registry
        print("ACP check OK")
    except Exception as e:
        print(f"ACP check FAILED: {e}")
        sys.exit(1)


def _run_setup() -> None:
    """Run interactive setup."""
    try:
        from cli.setup.setup_wizard import run_setup_wizard
        run_setup_wizard()
    except Exception as e:
        print(f"Setup failed: {e}")
        sys.exit(1)


async def _run_stdio_server() -> None:
    """Run ACP server with stdio transport."""
    from agent.acp.adapter import run_stdio_server

    try:
        await run_stdio_server()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.getLogger(__name__).error(f"Stdio server error: {e}")
        sys.exit(1)


async def _run_http_server(host: str, port: int) -> None:
    """Run ACP server with HTTP transport."""
    from agent.acp.adapter import run_http_server

    try:
        await run_http_server(host=host, port=port)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.getLogger(__name__).error(f"HTTP server error: {e}")
        sys.exit(1)


async def _async_main(args: argparse.Namespace) -> None:
    """Async main entry point."""
    if args.transport == "stdio":
        await _run_stdio_server()
    else:
        await _run_http_server(args.host, args.port)


def main(argv: list = None) -> None:
    """Main entry point."""
    _setup_logging()
    _load_env()

    args = _parse_args(argv)

    if args.version:
        _print_version()
        return

    if args.check:
        _run_check()
        return

    if args.setup:
        _run_setup()
        return

    try:
        asyncio.run(_async_main(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
