#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Collaborative Planning module.

Tests cover:
- CollaborationStrategy enum
- TechnicalDomain enum
- CollaborativeTaskPlanner class
"""

import pytest
from unittest.mock import patch, MagicMock

from agent.collaborative_planning import (
    CollaborationStrategy,
    TechnicalDomain,
    CollaborativeTaskPlanner,
    create_collaborative_planner,
)


class TestCollaborationStrategy:
    """Tests for CollaborationStrategy enum."""

    def test_collaboration_strategy_values(self):
        """CollaborationStrategy enum has values."""
        assert CollaborationStrategy is not None
        # Check it's an enum with string values
        for strategy in CollaborationStrategy:
            assert isinstance(strategy.value, str)


class TestTechnicalDomain:
    """Tests for TechnicalDomain enum."""

    def test_technical_domain_values(self):
        """TechnicalDomain enum has values."""
        assert TechnicalDomain is not None
        for domain in TechnicalDomain:
            assert isinstance(domain.value, str)


class TestCreateCollaborativePlanner:
    """Tests for create_collaborative_planner() function."""

    def test_create_collaborative_planner_returns_planner(self):
        """create_collaborative_planner() returns a CollaborativeTaskPlanner."""
        result = create_collaborative_planner()
        assert isinstance(result, CollaborativeTaskPlanner)


class TestCollaborativeTaskPlanner:
    """Tests for CollaborativeTaskPlanner class."""

    def test_init(self):
        """CollaborativeTaskPlanner initializes."""
        planner = CollaborativeTaskPlanner()
        assert planner is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
