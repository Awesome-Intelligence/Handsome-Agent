#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task Router Module - DEPRECATED

WARNING: This module is deprecated and will be removed in future versions.
Please use the new LLM-driven tool selection architecture instead.

迁移指南：
- 新架构: core/llm_tool_selector.py
- 简化版: core/simplified_agent.py
- 文档: docs/MIGRATION_GUIDE.md

This module provides basic route matching without intent classification.
For LLM-driven decision making, please use the new architecture.
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
import warnings


@dataclass
class RouteConfig:
    """Configuration for a route."""
    id: str
    name: str
    description: str
    handler: Callable
    keywords: List[str] = field(default_factory=list)
    priority: int = 1


@dataclass
class RouteMatch:
    """Result of route matching."""
    route_id: str
    handler: Callable
    confidence: float
    context: Dict[str, Any] = field(default_factory=dict)


def route_handler(route_id: str, name: str, description: str, keywords: List[str] = None,
                  priority: int = 1):
    """Decorator to register a route handler (DEPRECATED)."""
    warnings.warn(
        "route_handler is deprecated. Please use the new LLM-driven architecture. "
        "See core/llm_tool_selector.py",
        DeprecationWarning,
        stacklevel=2
    )

    def decorator(func: Callable) -> Callable:
        config = RouteConfig(
            id=route_id,
            name=name,
            description=description,
            handler=func,
            keywords=keywords or [],
            priority=priority
        )
        router.register_route(config)
        return func
    return decorator


class TaskRouter:
    """
    Basic task router (DEPRECATED).

    WARNING: This class is deprecated. Please use LLMDrivenDecisionEngine
    from core.llm_tool_selector instead.

    This class only provides basic keyword-based routing without intent classification.
    """

    def __init__(self):
        warnings.warn(
            "TaskRouter is deprecated. Please use LLMDrivenDecisionEngine "
            "from core.llm_tool_selector instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self.routes: List[RouteConfig] = []
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.propagate = False

    def register_route(self, config: RouteConfig):
        """Register a route configuration."""
        self.routes.append(config)
        self.routes.sort(key=lambda x: -x.priority)
        self.logger.info(f"Registered route: {config.id} (priority: {config.priority})")

    def route(self, input_text: str) -> Optional[RouteMatch]:
        """
        Route input to appropriate handler (DEPRECATED).

        WARNING: This method is deprecated. Use LLMDrivenDecisionEngine instead.
        """
        matches = self._find_matches(input_text)

        if matches:
            best_match = matches[0]
            self.logger.info(f"Routing to {best_match.route_id} with confidence {best_match.confidence:.2f}")
            return best_match
        return None

    def _find_matches(self, input_text: str) -> List[RouteMatch]:
        """Find all matching routes based on keywords only."""
        matches = []
        input_lower = input_text.lower()

        for route in self.routes:
            confidence = 0.0

            keyword_matches = sum(1 for kw in route.keywords if kw.lower() in input_lower)
            if route.keywords:
                # 降低置信度阈值，使关键词匹配更容易触发
                confidence = keyword_matches * 0.2  # 每个匹配得 0.2 分

            # 只要有一个关键词匹配就考虑路由（降低阈值）
            if confidence > 0.05:
                matches.append(RouteMatch(
                    route_id=route.id,
                    handler=route.handler,
                    confidence=confidence,
                    context={"route": route.name}
                ))

        matches.sort(key=lambda x: -x.confidence)
        return matches

    def list_routes(self) -> List[RouteConfig]:
        return self.routes


router = TaskRouter()


def _import_handlers():
    """Import all route handlers after router is initialized."""
    from . import router_handlers
    return router_handlers


_handlers = None

def get_handlers():
    """Get route handlers module."""
    global _handlers
    if _handlers is None:
        _handlers = _import_handlers()
    return _handlers


try:
    _handlers = _import_handlers()
except ImportError as e:
    pass
