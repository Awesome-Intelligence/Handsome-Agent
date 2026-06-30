#!/usr/bin/env python3
"""测试天气问题 - 使用正确的 LLM Provider"""
import asyncio
import logging
import sys
import os

# 设置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

async def test_weather():
    from agent.agent import Agent
    from agent.llm.providers import DeepSeekProvider
    
    print("=== 开始测试: 今天天气如何？ ===")
    
    # 创建 DeepSeek Provider
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("错误: 未设置 DEEPSEEK_API_KEY 环境变量")
        return
    
    provider = DeepSeekProvider(
        api_key=api_key,
        model="deepseek-chat"
    )
    
    agent = Agent(
        llm_provider=provider,
        session_id='test-weather-loop'
    )
    
    result = await agent.chat('今天天气如何？')
    
    print("=== 测试完成 ===")
    print(f"响应内容: {result.content[:500] if result.content else 'None'}")
    print(f"使用工具: {result.tool_used}")
    print(f"元数据: {result.metadata}")

if __name__ == "__main__":
    asyncio.run(test_weather())