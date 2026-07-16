"""🚪 Access - 🚪Gateway - Gateway CLI 入口"""

import argparse
import asyncio
import logging
import sys


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Agent-Z Gateway",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m gateway.gateway_cli              # Start HTTP Gateway
  python -m gateway.gateway_cli --port 8080   # Specify port
  python -m gateway.gateway_cli --debug      # Enable debug mode
        """
    )

    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Service listen address (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Service listen port (default: 8000)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )

    return parser.parse_args()


async def main():
    args = parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)]
    )
    logger = logging.getLogger("gateway")

    from agent.agent import create_agent_from_config
    agent = create_agent_from_config()
    if agent is None:
        logger.error("Agent not initialized — check LLM config")
        sys.exit(1)

    from agent.acp.adapter import run_http_server
    await run_http_server(agent, host=args.host, port=args.port)


if __name__ == "__main__":
    asyncio.run(main())
