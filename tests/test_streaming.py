"""测试流式输出功能"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import asyncio

# 设置测试环境
os.environ.setdefault("OPENAI_API_KEY", "your-api-key-here")
os.environ.setdefault("OPENAI_BASE_URL", "https://api.openai.com/v1")

from agent.llm import LLMClient, LLMAuxConfig
from agent.context import ContextBuilder, ContextManager
from agent.llm.providers.base import ProviderConfig
from agent.llm.providers.openai import OpenAIProvider
from common.streaming import ConsoleConsumer, StreamEmitter, ConsumerRegistry


async def test_streaming():
    """测试流式输出"""
    print("=" * 60)
    print("测试流式输出功能")
    print("=" * 60)
    
    # 1. 初始化 LLM Provider
    config = ProviderConfig(
        model="gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL")
    )
    provider = OpenAIProvider(config)
    
    # 2. 初始化组件
    tools_dict = {}  # 简单模式不需要工具
    context_builder = ContextBuilder(tools=tools_dict)
    from agent.context_compressor import SummaryCompressor
    context_compressor = SummaryCompressor(recent_messages=10)
    context_manager = ContextManager(
        context_compressor=context_compressor,
        context_builder=context_builder
    )
    
    llm_client = LLMClient(
        llm_provider=provider,
        context_manager=context_manager,
        aux_config=LLMAuxConfig()
    )
    
    # 3. 创建流式发射器（带控制台消费者）
    registry = ConsumerRegistry()
    registry.register(ConsoleConsumer())
    emitter = StreamEmitter(registry)
    emitter.start()
    
    print("\n开始流式测试...")
    print("-" * 40)
    
    # 4. 执行流式调用
    accumulated = ""
    try:
        print(f"API Key: {config.api_key[:10] if config.api_key else 'None'}...")
        print(f"Base URL: {config.base_url}")
        
        async for chunk in provider.generate_stream(
            "请用一句话介绍一下自己",
            system_prompt="你是一个友好的AI助手"
        ):
            delta = chunk.delta if hasattr(chunk, 'delta') else ""
            if delta:
                # 发射到控制台
                emitter.emit_delta(delta)
                accumulated += delta
        
        emitter.emit_complete(accumulated)
        
    except Exception as e:
        import traceback
        print(f"\n错误: {e}")
        traceback.print_exc()
    finally:
        emitter.stop()
    
    print("\n" + "-" * 40)
    print(f"累积内容: {accumulated[:100]}...")
    print("=" * 60)
    print("测试完成!")


async def test_agent_streaming():
    """测试 Agent 流式输出"""
    print("\n" + "=" * 60)
    print("测试 Agent 流式输出功能")
    print("=" * 60)
    
    from agent.agent import Agent
    
    # 1. 初始化 LLM Provider
    config = ProviderConfig(
        model="gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL")
    )
    provider = OpenAIProvider(config)
    
    # 2. 创建 Agent（启用流式）
    agent = Agent(
        llm_provider=provider,
        enable_session=False,
        enable_curator=False
    )
    
    # 3. 使用流式输出
    print("\n开始 Agent 流式测试...")
    print("-" * 40)
    
    try:
        response = await agent.chat(
            "请用一段话介绍一下Python语言",
            use_react=False,
            enable_stream=True
        )
        
        print("\n" + "-" * 40)
        print(f"最终响应: {response.content[:200]}...")
        
    except Exception as e:
        print(f"\n错误: {e}")
    
    # 清理
    agent._cleanup_stream()
    
    print("\n" + "=" * 60)
    print("Agent 测试完成!")


if __name__ == "__main__":
    print("选择测试:")
    print("1. 测试基础流式输出")
    print("2. 测试 Agent 流式输出")
    
    choice = input("请选择 (1/2): ").strip()
    
    if choice == "1":
        asyncio.run(test_streaming())
    elif choice == "2":
        asyncio.run(test_agent_streaming())
    else:
        print("无效选择，运行基础测试")
        asyncio.run(test_streaming())