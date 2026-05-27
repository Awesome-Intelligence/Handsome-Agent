#!/usr/bin/env python3
"""
Advanced Agent Features Demo
Showcasing: Lightweight, Enhanced, Multi-Agent, Memory, Self-Reflection
"""

import asyncio
import time


async def demo():
    # 1. Lightweight Agent
    print("="*60)
    print("1. Lightweight Agent")
    print("="*60)
    from lightweight.agent import LightweightAgent, AgentConfig
    agent = LightweightAgent(AgentConfig(enable_caching=True))
    result = await agent.respond("What is AI?")
    print(f"Response: {result.content[:80]}...")
    print(f"Time: {result.execution_time*1000:.2f}ms")
    
    # 2. Enhanced Agent
    print("\n" + "="*60)
    print("2. Enhanced Agent (CoT)")
    print("="*60)
    from lightweight.agent_v2 import EnhancedAgent, ReasoningLevel
    agent2 = EnhancedAgent(reasoning_level=ReasoningLevel.CHAIN_OF_THOUGHT)
    result2 = await agent2.respond("What is Python?", include_reasoning=True, use_tools=True)
    print(f"Response: {result2['response'][:80]}...")
    
    # 3. Multi-Agent
    print("\n" + "="*60)
    print("3. Multi-Agent System")
    print("="*60)
    from advanced_reasoning.multi_agent import MultiAgentSystem, Agent, AgentRole
    team = MultiAgentSystem()
    team.register_agent(Agent("Planner", AgentRole.PLANNER))
    team.register_agent(Agent("Developer", AgentRole.CODER))
    print("Agents registered successfully")
    
    print("\n✅ All Advanced Features Demo Completed!")
    print("Reference: AutoGPT, Claude, LangChain, MetaGPT, MemGPT")


if __name__ == "__main__":
    asyncio.run(demo())
