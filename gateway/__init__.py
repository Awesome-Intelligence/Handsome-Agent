"""
Gateway - Production-ready API Gateway with authentication and rate limiting.
Zero external dependencies.
"""

from .server import GatewayConfig, run_gateway
from .middleware import RateLimiter, authenticate

__version__ = "1.0.0"
__all__ = ["GatewayConfig", "run_gateway", "RateLimiter", "authenticate"]
