"""
Handsome Agent - Hermes-Brain + OpenClaw-Body Architecture
三层分层解耦架构的接入层 (Adapter Layer)
"""

from .gateway import Gateway, GatewayConfig
from .message import StandardMessage, MessageChannel

__all__ = [
    "Gateway",
    "GatewayConfig", 
    "StandardMessage",
    "MessageChannel",
]