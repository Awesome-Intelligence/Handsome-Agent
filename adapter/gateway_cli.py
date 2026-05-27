"""adapter.gateway - Gateway CLI 入口"""

import asyncio
import argparse
import logging
from adapter.gateway import Gateway, GatewayConfig
from adapter.adapters import HTTPAdapter, CLIAdapter
from adapter.message import MessageChannel
from shared.logging import setup_logging


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Handsome Agent Gateway",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m adapter.gateway                  # 启动 HTTP Gateway
  python -m adapter.gateway --cli            # 启动 CLI 模式
  python -m adapter.gateway --port 8080    # 指定端口
  python -m adapter.gateway --debug         # 启用调试模式
        """
    )
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="服务监听地址 (默认: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="服务监听端口 (默认: 8000)"
    )
    parser.add_argument(
        "--brain-url",
        default="http://localhost:8001",
        help="Brain Service 地址 (默认: http://localhost:8001)"
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="启动 CLI 交互模式"
    )
    parser.add_argument(
        "--user-id",
        default="cli_user",
        help="CLI 用户 ID (默认: cli_user)"
    )
    parser.add_argument(
        "--api-key",
        help="API 密钥"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式"
    )
    
    return parser.parse_args()


async def run_cli_mode(gateway: Gateway, user_id: str):
    """运行 CLI 交互模式"""
    cli_adapter = CLIAdapter(gateway, gateway.config, user_id=user_id)
    gateway.register_adapter(MessageChannel.CLI, cli_adapter)
    
    # 创建简单的消息处理器
    async def handle_message(message):
        """处理消息（简单回显）"""
        from adapter.message import StandardMessage
        return StandardMessage(
            message_id=message.message_id,
            channel=message.channel,
            user_id=message.user_id,
            session_id=message.session_id,
            content={"type": "text", "text": f"收到: {message.content.text}"},
        )
    
    gateway.set_message_handler(handle_message)
    await cli_adapter.run_interactive()


async def main():
    """主函数"""
    args = parse_args()
    
    # 设置日志
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(level=log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 50)
    logger.info("Handsome Agent Gateway")
    logger.info("=" * 50)
    
    # 创建配置
    config = GatewayConfig(
        name="HandsomeAgentGateway",
        host=args.host,
        port=args.port,
        brain_service_url=args.brain_url,
        api_key=args.api_key,
    )
    
    # 创建 Gateway
    gateway = Gateway(config)
    
    if args.cli:
        # CLI 模式
        logger.info("启动 CLI 交互模式")
        await run_cli_mode(gateway, args.user_id)
    else:
        # HTTP 模式
        http_adapter = HTTPAdapter(gateway, config)
        gateway.register_adapter(MessageChannel.HTTP, http_adapter)
        
        try:
            await gateway.start()
            logger.info(f"Gateway 已启动: http://{args.host}:{args.port}")
            logger.info(f"Brain Service: {args.brain_url}")
            logger.info("按 Ctrl+C 停止服务")
            
            # 保持运行
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("接收到停止信号")
        finally:
            await gateway.stop()
            logger.info("Gateway 已停止")


if __name__ == "__main__":
    asyncio.run(main())