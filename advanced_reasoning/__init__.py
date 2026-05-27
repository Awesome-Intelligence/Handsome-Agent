"""
Advanced Reasoning module for the Handsome Agent.

这个包包含智能响应生成系统，具有以下特性:
- 领域知识库和上下文感知处理
- Chain of Thought推理
- Multi-Agent协作系统
- 分层记忆系统
- 自我反思机制
"""

from .module import AdvancedReasoningModule
from .integration import enhance_agent_with_advanced_reasoning
from .multi_agent import AgentRole, Message, MultiAgentSystem, SoftwareTeam
from .memory import HierarchicalMemory, SelfReflectiveAgent

__version__ = "1.0.0"
__author__ = "Handsome Agent Team"

__all__ = [
    "AdvancedReasoningModule",
    "enhance_agent_with_advanced_reasoning",
    "AgentRole",
    "Message",
    "MultiAgentSystem",
    "SoftwareTeam",
    "HierarchicalMemory",
    "SelfReflectiveAgent"
]
