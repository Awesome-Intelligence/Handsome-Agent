"""adapter.gateway - Gateway CLI 入口"""

import asyncio
import argparse
import logging
from gateway.gateway import Gateway, GatewayConfig
from gateway.adapters import HTTPAdapter, CLIAdapter
from gateway.message import MessageChannel
from gateway.memory_monitor import start_memory_monitoring, stop_memory_monitoring
from common.logging import setup_logging
from common.logging_manager import get_access_logger


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Handsome Agent Gateway",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m gateway.gateway_cli              # Start HTTP Gateway
  python -m gateway.gateway_cli --cli        # Start CLI mode
  python -m gateway.gateway_cli --port 8080  # Specify port
  python -m gateway.gateway_cli --debug       # Enable debug mode
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
        "--brain-url",
        default="http://localhost:8000",
        help="Brain Service address (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Start CLI interactive mode"
    )
    parser.add_argument(
        "--user-id",
        default="cli_user",
        help="CLI user ID (default: cli_user)"
    )
    parser.add_argument(
        "--api-key",
        help="API key"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    
    return parser.parse_args()


async def run_cli_mode(gateway: Gateway, user_id: str):
    """Run CLI interactive mode"""
    cli_adapter = CLIAdapter(gateway, gateway.config, user_id=user_id)
    gateway.register_adapter(MessageChannel.CLI, cli_adapter)
    
    async def handle_message(message):
        """Handle message (simple echo)"""
        from gateway.message import StandardMessage
        return StandardMessage(
            message_id=message.message_id,
            channel=message.channel,
            user_id=message.user_id,
            session_id=message.session_id,
            content={"type": "text", "text": f"Received: {message.content.text}"},
        )
    
    gateway.set_message_handler(handle_message)
    await cli_adapter.run_interactive()


async def main():
    """Main function"""
    args = parse_args()
    
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(level=log_level)
    logger = get_access_logger(__name__)
    
    logger.info("=" * 50)
    logger.info("Handsome Agent Gateway")
    logger.info("=" * 50)
    
    # 启动内存监控
    memory_monitor_enabled = start_memory_monitoring(interval_seconds=300)
    if memory_monitor_enabled:
        logger.info("Memory monitoring enabled")
    
    config = GatewayConfig(
        name="HandsomeAgentGateway",
        host=args.host,
        port=args.port,
        brain_service_url=args.brain_url,
        api_key=args.api_key,
    )
    
    gateway = Gateway(config)
    
    try:
        if args.cli:
            logger.info("Starting CLI interactive mode")
            await run_cli_mode(gateway, args.user_id)
        else:
            http_adapter = HTTPAdapter(gateway, config)
            gateway.register_adapter(MessageChannel.HTTP, http_adapter)
            
            await gateway.start()
            logger.info(f"Gateway started: http://{args.host}:{args.port}")
            logger.info(f"Brain Service: {args.brain_url}")
            logger.info("Press Ctrl+C to stop service")
            
            while True:
                await asyncio.sleep(1)
                
    except KeyboardInterrupt:
        logger.info("Received stop signal")
    finally:
        await gateway.stop()
        stop_memory_monitoring()
        logger.info("Gateway stopped")


if __name__ == "__main__":
    asyncio.run(main())