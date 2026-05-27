#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for the Handsome Agent.

These tests verify that all modules work together correctly.
"""

import asyncio
import unittest
from core import CustomAgent, AgentConfig, AgentResponse
from advanced_reasoning.integration import enhance_agent_with_advanced_reasoning


class TestIntegration(unittest.TestCase):
    """Test integration between components."""
    
    def test_basic_agent_creation(self):
        """Test basic agent creation."""
        agent = CustomAgent()
        self.assertIsInstance(agent, CustomAgent)
    
    def test_advanced_agent_creation(self):
        """Test advanced agent creation."""
        agent = enhance_agent_with_advanced_reasoning()
        self.assertIsInstance(agent, CustomAgent)
    
    def test_basic_response_integration(self):
        """Test basic response integration."""
        import asyncio
        agent = CustomAgent(AgentConfig(enable_caching=False))
        response = asyncio.run(agent.respond("What is machine learning?"))
        self.assertIsInstance(response, AgentResponse)
        self.assertGreater(len(response.content), 0)
    
    def test_advanced_response_integration(self):
        """Test advanced response integration."""
        import asyncio
        agent = enhance_agent_with_advanced_reasoning(AgentConfig(enable_caching=False))
        response = asyncio.run(agent.respond("How do I optimize Python code?"))
        self.assertIsInstance(response, AgentResponse)
        self.assertGreater(len(response.content), 1000)  # Advanced responses should be detailed
    
    def test_response_truncation(self):
        """Test response truncation functionality."""
        import asyncio
        config = AgentConfig(max_response_length=50, enable_caching=False)
        agent = CustomAgent(config)
        response = asyncio.run(agent.respond("This should be a very long response that gets truncated"))
        self.assertLessEqual(len(response.content), 50 + len("...\n\n[Response truncated for length]"))


def run_integration_tests():
    """Run integration tests that require async/await."""
    
    async def test_basic_response():
        agent = CustomAgent(AgentConfig(enable_caching=False))
        response = await agent.respond("What is machine learning?")
        assert isinstance(response, AgentResponse)
        assert len(response.content) > 0
        print("✅ Basic response integration test passed")
    
    async def test_advanced_response():
        agent = enhance_agent_with_advanced_reasoning(AgentConfig(enable_caching=False))
        response = await agent.respond("How do I optimize Python code?")
        assert isinstance(response, AgentResponse)
        assert len(response.content) > 1000
        print("✅ Advanced response integration test passed")
    
    async def test_input_validation():
        agent = CustomAgent(AgentConfig(enable_caching=False))
        try:
            await agent.respond("")
            assert False, "Should have raised InputValidationError"
        except Exception:
            print("✅ Input validation integration test passed")
    
    async def test_timeout():
        config = AgentConfig(timeout_seconds=0.1, enable_caching=False)
        agent = CustomAgent(config)
        response = await agent.respond("quick query")
        assert isinstance(response, AgentResponse)
        print("✅ Timeout integration test passed")
    
    async def run_all():
        await test_basic_response()
        await test_advanced_response()
        await test_input_validation()
        await test_timeout()
        print("✅ All integration tests passed!")
    
    asyncio.run(run_all())


if __name__ == "__main__":
    print("Running integration tests...")
    print("=" * 50)
    
    # Run unit tests
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run integration tests
    print("\nRunning async integration tests...")
    run_integration_tests()
    
    print("\n" + "=" * 50)
    print("✅ All integration tests completed successfully!")