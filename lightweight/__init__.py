"""
Lightweight Agent - Minimal agent for mobile backend deployment.
Standard library only, zero dependencies.
"""

from .agent import LightweightAgent, AgentConfig, AgentResponse
from .server import run_server

__version__ = "1.0.0"
__all__ = ["LightweightAgent", "AgentConfig", "AgentResponse", "run_server"]
