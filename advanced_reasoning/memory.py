#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory System with Self-Reflection
参考: MemGPT, AutoGPT, Claude

功能:
- 分层记忆管理
- 自我反思机制
- 经验总结
"""

import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Memory:
    """单条记忆"""
    content: str
    importance: float = 0.5
    timestamp: float = field(default_factory=time.time)
    memory_type: str = "general"
    
    def __repr__(self):
        return "[{0}] {1}...".format(self.memory_type, self.content[:50])


class HierarchicalMemory:
    """
    分层记忆系统
    参考: MemGPT, GPT-4-Turbo Memory
    """
    
    def __init__(self):
        self.working_memory: List[Memory] = []  # 当前上下文
        self.short_term: List[Memory] = []      # 短期记忆
        self.long_term: List[Memory] = []       # 长期记忆
        
        # 容量限制
        self.working_limit = 10
        self.short_term_limit = 50
        self.consolidation_threshold = 0.7
    
    def add(self, content: str, importance: float = 0.5, mem_type: str = "general"):
        """添加记忆"""
        memory = Memory(content=content, importance=importance, memory_type=mem_type)
        self.working_memory.append(memory)
        
        # 检查是否需要整合
        if len(self.working_memory) > self.working_limit:
            self.consolidate()
    
    def consolidate(self):
        """记忆整合"""
        print("\n🧠 执行记忆整合...")
        
        # 筛选重要记忆
        important = [m for m in self.working_memory if m.importance >= self.consolidation_threshold]
        
        # 转移到短期记忆
        self.short_term.extend(important)
        
        # 清理工作记忆
        self.working_memory = []
        
        print(f"✅ 整合了 {len(important)} 条重要记忆到短期记忆")
    
    def retrieve(self, query: str) -> List[Memory]:
        """记忆检索"""
        results = []
        
        # 优先检索工作记忆
        for mem in self.working_memory:
            if query.lower() in mem.content.lower():
                results.append(mem)
        
        # 检索短期记忆
        for mem in self.short_term:
            if query.lower() in mem.content.lower():
                results.append(mem)
        
        return results
    
    def reflect(self) -> str:
        """自我反思 (参考Claude)"""
        if not self.short_term:
            return "反思: 经验不足，需要更多实践"
        
        # 统计记忆类型分布
        type_stats = {}
        for mem in self.short_term:
            type_stats[mem.memory_type] = type_stats.get(mem.memory_type, 0) + 1
        
        return f"""反思总结:
- 短期记忆: {len(self.short_term)} 条
- 最重要经验: {max([m.content[:30] for m in self.short_term[:3]]) if self.short_term else 'N/A'}
- 经验分布: {type_stats}"""


class SelfReflectiveAgent:
    """
    自我反思Agent
    参考: AutoGPT, Claude
    """
    
    def __init__(self):
        self.memory = HierarchicalMemory()
        self.feedback_history: List[Dict] = []
        self.performance_metrics: Dict[str, Any] = {
            "success_count": 0,
            "failure_count": 0,
            "total_interactions": 0
        }
    
    async def think_and_act(
        self,
        task: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """思考和行动"""
        self.performance_metrics["total_interactions"] += 1
        
        # 1. 检索记忆
        relevant_memories = self.memory.retrieve(task)
        
        # 2. 基于记忆和任务生成响应
        response = f"基于 {len(relevant_memories)} 条相关记忆，我分析: {task}"
        
        # 3. 添加到工作记忆
        self.memory.add(
            content=f"任务: {task}, 响应: {response}",
            importance=0.8
        )
        
        return {
            "task": task,
            "response": response,
            "relevant_memories": len(relevant_memories),
            "metrics": self.performance_metrics
        }
    
    async def reflect_on_result(
        self,
        result: Dict[str, Any],
        success: bool
    ):
        """反思结果 (AutoGPT风格)"""
        # 更新指标
        if success:
            self.performance_metrics["success_count"] += 1
            importance = 0.9
        else:
            self.performance_metrics["failure_count"] += 1
            importance = 0.3
        
        # 添加反思记忆
        reflection = f"任务: {result['task']}, 成功: {success}"
        self.memory.add(reflection, importance=importance, mem_type="reflection")
        
        # 检查是否需要记忆整合
        if len(self.memory.working_memory) > 5:
            self.memory.consolidate()
    
    def get_performance_report(self) -> Dict[str, Any]:
        """性能报告"""
        total = self.performance_metrics["total_interactions"]
        if total == 0:
            return {"status": "No interactions yet"}
        
        success_rate = self.performance_metrics["success_count"] / total
        
        return {
            "total_interactions": total,
            "success_count": self.performance_metrics["success_count"],
            "failure_count": self.performance_metrics["failure_count"],
            "success_rate": f"{success_rate:.1%}",
            "short_term_memory": len(self.memory.short_term),
            "reflection": self.memory.reflect()
        }


async def demo_memory_system():
    """演示记忆系统"""
    print("="*60)
    print("🧠 Memory System with Self-Reflection")
    print("参考: MemGPT, AutoGPT, Claude")
    print("="*60)
    
    agent = SelfReflectiveAgent()
    
    # 任务1
    result1 = await agent.think_and_act("Python编程", {"domain": "programming"})
    print(f"\n任务1结果: {result1['response']}")
    await agent.reflect_on_result(result1, success=True)
    
    # 任务2
    result2 = await agent.think_and_act("机器学习应用", {"domain": "ai"})
    print(f"\n任务2结果: {result2['response']}")
    await agent.reflect_on_result(result2, success=True)
    
    # 性能报告
    report = agent.get_performance_report()
    print(f"\n📊 性能报告: {report}")


if __name__ == "__main__":
    asyncio.run(demo_memory_system())
