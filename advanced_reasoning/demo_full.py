#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Agent System Demo - 完整功能演示
展示所有高级Agent能力
"""

import asyncio
import time
from typing import Dict, Any


async def demo_lightweight_agent():
    """轻量级Agent演示"""
    from lightweight.agent import LightweightAgent, AgentConfig
    
    print("\n" + "="*60)
    print("1. Lightweight Agent (Zero Claw风格)")
    print("="*60)
    
    agent = LightweightAgent(AgentConfig(enable_caching=True))
    
    queries = [
        "What is Python?",
        "Explain machine learning",
        "API design principles"
    ]
    
    for q in queries:
        result = await agent.respond(q)
        print(f"\n❓ {q}")
        print(f"✅ {result.content[:100]}...")
        print(f"⏱️  {result.execution_time*1000:.2f}ms")


async def demo_enhanced_agent():
    """增强版Agent演示 (Chain of Thought)"""
    from lightweight.agent_v2 import EnhancedAgent, ReasoningLevel
    
    print("\n" + "="*60)
    print("2. Enhanced Agent (Claude + AutoGPT风格)")
    print("="*60)
    
    agent = EnhancedAgent(reasoning_level=ReasoningLevel.CHAIN_OF_THOUGHT)
    
    result = await agent.respond(
        "Explain neural networks",
        include_reasoning=True,
        use_tools=True
    )
    
    print(f"\n📝 Response:\n{result['response']}")
    print(f"\n⏱️  Execution time: {result['execution_time']*1000:.2f}ms")
    print(f"🎯 Confidence: {result['confidence']:.2f}")


async def demo_multi_agent():
    """Multi-Agent协作演示 (MetaGPT风格)"""
    from advanced_reasoning.multi_agent import MultiAgentSystem, Agent, AgentRole
    
    print("\n" + "="*60)
    print("3. Multi-Agent Collaboration (MetaGPT风格)")
    print("="*60)
    
    team = MultiAgentSystem()
    
    # 添加Agent
    team.register_agent(Agent("Architect", AgentRole.COORDINATOR))
    team.register_agent(Agent("Developer", AgentRole.CODER))
    
    # 协作
    result = await team.collaborate("Build a web app", rounds=2)
    print(f"\n✅ Final decision: {result['decision']}")


async def demo_memory_system():
    """记忆系统演示 (MemGPT风格)"""
    from advanced_reasoning import SelfReflectiveAgent
    
    print("\n" + "="*60)
    print("4. Memory System (MemGPT风格)
    print("="*60)
    
    agent = SelfReflectiveAgent()
    
    # 交互
    for i in range(3):
        result = await agent.think_and_act(
            f"Task {i+1}",
            {"context": f"Task {i+1} completed"}
        )
        await agent.reflect_on_result(result, success=True)
    
    # 性能报告
    report = agent.get_performance_report()
    print(f"\n📊 Performance Report:")
    print(f"   - Success Rate: {report.get('success_rate', 'N/A')}")
    print(f"   - Short-term Memory: {report.get('short_term_memory', 'N/A')} items")


async def demo_all_features():
    """所有功能演示"""
    print("\n" + "🎯"*20)
    print("\n🎯 Handsome Agent - Complete Feature Demo")
    print("参考: AutoGPT, Claude, LangChain, MetaGPT, MemGPT")
    print("🎯"*20)
    
    # 1. Lightweight
    await demo_lightweight_agent()
    await asyncio.sleep(0.5)
    
    # 2. Enhanced
    await demo_enhanced_agent()
    await asyncio.sleep(0.5)
    
    # 3. Multi-Agent
    await demo_multi_agent()
    await asyncio.sleep(0.5)
    
    # 4. Memory
    await demo_memory_system()
    
    print("\n" + "="*60)
    print("✅ All demos completed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(demo_all_features())
