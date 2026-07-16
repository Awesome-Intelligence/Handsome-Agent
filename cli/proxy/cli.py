#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proxy CLI - Proxy command line interface.

🚪 Access - 💬 CLI - 代理 CLI
"""

import argparse
from typing import Optional

from .server import create_proxy


def proxy_start(args: argparse.Namespace):
    """Start the proxy server."""
    server = create_proxy(
        host=args.host,
        port=args.port,
        upstream_url=args.upstream,
    )
    server.start()

    print(f"Proxy running on http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop")


def proxy_stop(args: argparse.Namespace):
    """Stop the proxy server."""
    print("Stopping proxy server...")
    # Note: Would need a way to communicate with running server


def proxy_status(args: argparse.Namespace):
    """Show proxy status."""
    print("Proxy status: stopped (placeholder)")


def add_proxy_parser(subparsers) -> argparse.ArgumentParser:
    """Add proxy subparser.

    Args:
        subparsers: ArgumentParser subparsers

    Returns:
        Proxy subparser
    """
    proxy_parser = subparsers.add_parser(
        "proxy",
        help="HTTP proxy management",
        description="Manage the Agent-Z HTTP proxy",
    )

    proxy_subparsers = proxy_parser.add_subparsers(dest="proxy_command", help="Proxy command")

    # Start command
    start_parser = proxy_subparsers.add_parser(
        "start",
        help="Start proxy server",
    )
    start_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to",
    )
    start_parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to listen on",
    )
    start_parser.add_argument(
        "--upstream",
        help="Upstream API URL",
    )
    start_parser.set_defaults(func=proxy_start)

    # Stop command
    stop_parser = proxy_subparsers.add_parser(
        "stop",
        help="Stop proxy server",
    )
    stop_parser.set_defaults(func=proxy_stop)

    # Status command
    status_parser = proxy_subparsers.add_parser(
        "status",
        help="Show proxy status",
    )
    status_parser.set_defaults(func=proxy_status)

    return proxy_parser


def proxy_cli(args: argparse.Namespace):
    """Entry point for proxy CLI.

    Args:
        args: Parsed arguments
    """
    if hasattr(args, 'func'):
        args.func(args)
    else:
        print("Usage: agentz proxy [start|stop|status]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    add_proxy_parser(subparsers)

    args = parser.parse_args()
    proxy_cli(args)