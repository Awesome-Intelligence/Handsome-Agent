"""brain.service - Brain Service CLI 入口"""

import asyncio
import argparse
import logging
from brain.service import BrainService, BrainServiceConfig
from brain.agent.agent_loop import AgentConfig
from brain.llm import LLMFactory
from shared.logging import setup_logging


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Handsome Agent Brain Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m brain.service                    # 使用默认配置启动
  python -m brain.service --port 8002      # 指定端口
  python -m brain.service --llm openai --api-key xxx  # 启用 OpenAI LLM
  python -m brain.service --debug           # 启用调试模式
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
        default=8001,
        help="服务监听端口 (默认: 8001)"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=10,
        help="Agent 最大迭代次数 (默认: 10)"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="超时时间（秒）(默认: 60)"
    )
    parser.add_argument(
        "--llm",
        choices=["openai", "claude", "none"],
        default="none",
        help="LLM 提供商 (默认: none)"
    )
    parser.add_argument(
        "--api-key",
        help="LLM API 密钥"
    )
    parser.add_argument(
        "--model",
        help="LLM 模型名称"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式"
    )
    parser.add_argument(
        "--system-prompt",
        default="你是一个智能助手，能够帮助用户完成各种任务。",
        help="系统提示词"
    )
    
    return parser.parse_args()


async def main():
    """主函数"""
    args = parse_args()
    
    # 设置日志
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(level=log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 50)
    logger.info("Handsome Agent Brain Service")
    logger.info("=" * 50)
    
    # 创建配置
    config = BrainServiceConfig(
        name="HandsomeAgentBrain",
        host=args.host,
        port=args.port,
        max_iterations=args.max_iterations,
        timeout_seconds=args.timeout,
    )
    
    # 创建 Brain Service
    brain_service = BrainService(config)
    
    # 配置 LLM Provider
    if args.llm != "none" and args.api_key:
        logger.info(f"配置 LLM Provider: {args.llm}")
        try:
            llm_provider = LLMFactory.create(
                provider=args.llm,
                api_key=args.api_key,
                model=args.model,
            )
            
            # 设置到 Agent Loop
            loop_config = AgentConfig(
                max_iterations=args.max_iterations,
                timeout_seconds=args.timeout,
                system_prompt=args.system_prompt,
            )
            
            # 更新 Agent Loop 配置以使用 LLM
            brain_service._agent_loop = brain_service._agent_loop or None
            if brain_service._agent_loop:
                brain_service._agent_loop.config = loop_config
                brain_service._agent_loop.set_llm_provider(llm_provider)
            
            logger.info(f"LLM Provider 配置成功: {args.llm}")
        except Exception as e:
            logger.warning(f"LLM Provider 配置失败: {e}")
            logger.info("将使用规则匹配模式")
    else:
        logger.info("未配置 LLM，使用规则匹配模式")
    
    # 启动服务
    try:
        await brain_service.start()
        logger.info(f"Brain Service 已启动: http://{args.host}:{args.port}")
        logger.info("按 Ctrl+C 停止服务")
        
        # 保持运行
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("接收到停止信号")
    finally:
        await brain_service.stop()
        logger.info("Brain Service 已停止")


if __name__ == "__main__":
    asyncio.run(main())