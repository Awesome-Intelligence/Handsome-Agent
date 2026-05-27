"""
pytest configuration file for the Handsome Agent.

This file contains shared fixtures and configuration for all tests.
"""

import pytest
import asyncio
from core import AgentConfig, CustomAgent
from advanced_reasoning.integration import enhance_agent_with_advanced_reasoning


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def basic_agent():
    """Create a basic agent instance for testing."""
    config = AgentConfig(
        enable_caching=False,  # Disable caching for predictable tests
        timeout_seconds=1.0
    )
    return CustomAgent(config)


@pytest.fixture
def advanced_agent():
    """Create an advanced agent instance for testing."""
    config = AgentConfig(
        enable_caching=False,  # Disable caching for predictable tests
        timeout_seconds=1.0
    )
    return enhance_agent_with_advanced_reasoning(config)


@pytest.fixture
def test_config():
    """Create a test configuration."""
    return AgentConfig(
        enable_caching=False,
        timeout_seconds=1.0,
        max_response_length=2000
    )


@pytest.fixture
def sample_queries():
    """Provide sample queries for testing."""
    return {
        'basic': "What is machine learning?",
        'programming': "How do I optimize Python code?",
        'ml': "Explain neural networks",
        'system_design': "REST vs GraphQL comparison",
        'empty': "",
        'whitespace': "   "
    }