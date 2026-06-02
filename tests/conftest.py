"""
pytest configuration file for the Handsome Agent.

This file contains shared fixtures and configuration for all tests.
"""

import pytest
import asyncio
from agent.agent import Agent, AgentResponse


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def basic_agent():
    """Create a basic Agent instance for testing."""
    return Agent(llm_provider=None)


@pytest.fixture
def test_config():
    """Create a test configuration."""
    return {"timeout_seconds": 1.0}
