#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Agent Collaboration System
参考: MetaGPT, ChatDev, AutoGen

功能:
- 多Agent角色分配
- Agent间通信
- 共享工作区
- 协作决策
"""

import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class AgentRole(Enum):
    """Agent角色"""
    COORDINATOR = "coordinator"
    RESEARCHER = "researcher"
    CODER = "coder"
    REVIEWER = "reviewer"
    PLANNER = "planner"
    EXECUTOR = "executor"
    CRITIC = "critic"


@dataclass
class Message:
    """Agent间通信消息"""
    sender: str
    receiver: str
    content: str
    message_type: str = "text"
    metadata: Dict[str, Any] = field(default_factory=dict)


class Agent:
    """基础Agent类"""
    
    def __init__(
        self,
        name: str,
        role: AgentRole,
        system_prompt: str = ""
    ):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.memory: List[Dict] = []
    
    async def think(self, context: Dict[str, Any]) -> str:
        """Agent思考过程"""
        return f"[{self.role.value}] {self.name}思考中..."
    
    async def act(self, context: Dict[str, Any]) -> str:
        """Agent行动"""
        return f"[{self.role.value}] {self.name}执行中..."
    
    def receive(self, message: Message):
        """接收消息"""
        self.memory.append({
            "sender": message.sender,
            "content": message.content,
            "type": message.message_type
        })


class MultiAgentSystem:
    """
    多Agent协作系统
    参考: MetaGPT, ChatDev
    """
    
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.message_queue: List[Message] = []
        self.shared_context: Dict[str, Any] = {}
        self.conversation_history: List[Dict] = []
    
    def register_agent(self, agent: Agent):
        """注册Agent"""
        self.agents[agent.name] = agent
        print(f"✅ Agent {agent.name} ({agent.role.value}) 已注册")
    
    async def broadcast(self, sender: str, content: str, msg_type: str = "broadcast"):
        """广播消息给所有Agent"""
        message = Message(
            sender=sender,
            receiver="all",
            content=content,
            message_type=msg_type
        )
        self.message_queue.append(message)
        
        # 分发消息
        for name, agent in self.agents.items():
            if name != sender:
                agent.receive(message)
    
    async def send_message(
        self,
        sender: str,
        receiver: str,
        content: str
    ):
        """发送消息"""
        message = Message(sender=sender, receiver=receiver, content=content)
        
        if receiver in self.agents:
            self.agents[receiver].receive(message)
            self.message_queue.append(message)
    
    async def collaborate(
        self,
        task: str,
        rounds: int = 3
    ) -> Dict[str, Any]:
        """多Agent协作完成任务"""
        print(f"\n{'='*60}")
        print(f"🎯 开始协作任务: {task}")
        print(f"{'='*60}\n")
        
        # 1. 广播任务
        await self.broadcast("system", f"新任务: {task}", "task")
        
        # 2. 多轮讨论
        for round_num in range(rounds):
            print(f"\n📋 第 {round_num + 1} 轮讨论:")
            print("-" * 60)
            
            for name, agent in self.agents.items():
                # Agent思考
                context = {
                    "task": task,
                    "round": round_num,
                    "all_agents": list(self.agents.keys())
                }
                
                thought = await agent.think(context)
                print(f"\n🤔 {agent.name} ({agent.role.value}): {thought}")
                
                # Agent行动
                action = await agent.act(context)
                print(f"⚡ {agent.name}: {action}")
                
                # 广播行动
                await self.broadcast(name, action, "action")
                
                # 记录
                self.conversation_history.append({
                    "round": round_num,
                    "agent": name,
                    "thought": thought,
                    "action": action
                })
        
        # 3. 综合决策
        decision = self._synthesize_decision()
        
        return {
            "task": task,
            "rounds": rounds,
            "agents": [a.name for a in self.agents.values()],
            "decision": decision,
            "history": self.conversation_history
        }
    
    def _synthesize_decision(self) -> str:
        """综合决策"""
        return f"基于 {len(self.agents)} 个Agent的讨论，达成共识: 任务完成"
    
    def get_agent_status(self) -> Dict[str, str]:
        """获取所有Agent状态"""
        return {name: agent.role.value for name, agent in self.agents.items()}


class SoftwareTeam(MultiAgentSystem):
    """软件团队Agent系统 (参考MetaGPT)"""
    
    def __init__(self):
        super().__init__()
        
        # 创建团队成员
        self._create_team()
    
    def _create_team(self):
        """创建团队成员"""
        # 产品经理
        pm = Agent(
            name="产品经理",
            role=AgentRole.PLANNER,
            system_prompt="你负责产品规划和需求分析"
        )
        self.register_agent(pm)
        
        # 架构师
        architect = Agent(
            name="架构师",
            role=AgentRole.COORDINATOR,
            system_prompt="你负责系统架构设计"
        )
        self.register_agent(architect)
        
        # 开发者
        developer = Agent(
            name="开发者",
            role=AgentRole.CODER,
            system_prompt="你负责代码实现"
        )
        self.register_agent(developer)
        
        # 测试工程师
        tester = Agent(
            name="测试工程师",
            role=AgentRole.REVIEWER,
            system_prompt="你负责代码审查和测试"
        )
        self.register_agent(tester)


async def demo_multi_agent():
    """演示多Agent协作"""
    print("="*60)
    print("🤖 Multi-Agent Collaboration System Demo")
    print("参考: MetaGPT, ChatDev, AutoGen")
    print("="*60)
    
    # 创建团队
    team = SoftwareTeam()
    
    # 分配任务
    result = await team.collaborate("开发一个用户管理系统", rounds=2)
    
    print(f"\n{'='*60}")
    print("📊 最终决策:")
    print(f"{'='*60}")
    print(result["decision"])
    print(f"\n参与Agent: {', '.join(result['agents'])}")


if __name__ == "__main__":
    asyncio.run(demo_multi_agent())
