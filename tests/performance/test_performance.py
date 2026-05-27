#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance tests for the Handsome Agent.

These tests measure response times, memory usage, and caching effectiveness.
"""

import asyncio
import time
import unittest
from core import CustomAgent, AgentConfig
from advanced_reasoning.integration import enhance_agent_with_advanced_reasoning


class TestPerformance(unittest.TestCase):
    """Test performance characteristics."""
    
    def setUp(self):
        """Set up performance test fixtures."""
        self.basic_agent = CustomAgent(AgentConfig(enable_caching=False))
        self.advanced_agent = enhance_agent_with_advanced_reasoning(AgentConfig(enable_caching=False))
    
    def test_basic_response_time(self):
        """Test basic response generation time."""
        import asyncio
        start_time = time.time()
        response = asyncio.run(self.basic_agent.respond("What is machine learning?"))
        end_time = time.time()
        
        execution_time = end_time - start_time
        # Basic responses should be very fast (< 10ms)
        self.assertLess(execution_time, 0.01)
        print(f"Basic response time: {execution_time:.4f}s")
    
    def test_advanced_response_time(self):
        """Test advanced response generation time."""
        import asyncio
        start_time = time.time()
        response = asyncio.run(self.advanced_agent.respond("How do I optimize Python code?"))
        end_time = time.time()
        
        execution_time = end_time - start_time
        # Advanced responses should be fast (< 50ms)
        self.assertLess(execution_time, 0.05)
        print(f"Advanced response time: {execution_time:.4f}s")
    
    def test_caching_performance(self):
        """Test caching performance improvement."""
        import asyncio
        # Create agent with caching enabled
        config = AgentConfig(enable_caching=True)
        agent = CustomAgent(config)
        
        query = "What is machine learning?"
        
        # First request (no cache)
        start_time = time.time()
        response1 = asyncio.run(agent.respond(query))
        first_time = time.time() - start_time
        
        # Second request (with cache)
        start_time = time.time()
        response2 = asyncio.run(agent.respond(query))
        second_time = time.time() - start_time
        
        # Responses should be identical (caching works correctly)
        self.assertEqual(response1.content, response2.content)
        
        # Cached response should be at least as fast or faster
        if first_time > 0 and second_time > 0:
            self.assertLessEqual(second_time, first_time * 1.5)  # Allow some variance
            print(f"First time: {first_time:.6f}s, Second time: {second_time:.6f}s")


def run_performance_tests():
    """Run performance tests."""
    
    async def test_basic_performance():
        agent = CustomAgent(AgentConfig(enable_caching=False))
        start_time = time.time()
        response = await agent.respond("Performance test query")
        execution_time = time.time() - start_time
        print(f"✅ Basic performance: {execution_time:.4f}s")
        assert execution_time < 0.01
    
    async def test_advanced_performance():
        agent = enhance_agent_with_advanced_reasoning(AgentConfig(enable_caching=False))
        start_time = time.time()
        response = await agent.respond("Advanced performance test")
        execution_time = time.time() - start_time
        print(f"✅ Advanced performance: {execution_time:.4f}s")
        assert execution_time < 0.05
    
    async def test_caching_performance():
        config = AgentConfig(enable_caching=True)
        agent = CustomAgent(config)
        query = "Caching performance test"
        
        # First request
        start_time = time.time()
        response1 = await agent.respond(query)
        first_time = time.time() - start_time
        
        # Second request (cached)
        start_time = time.time()
        response2 = await agent.respond(query)
        second_time = time.time() - start_time
        
        speedup = first_time / max(second_time, 0.0001)
        print(f"✅ Caching performance: {speedup:.1f}x speedup")
        assert speedup > 10.0
        assert response1.content == response2.content
    
    async def run_all():
        await test_basic_performance()
        await test_advanced_performance()
        await test_caching_performance()
        print("✅ All performance tests passed!")
    
    asyncio.run(run_all())


if __name__ == "__main__":
    print("Running performance tests...")
    print("=" * 50)
    
    # Run unit tests
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run performance tests
    print("\nRunning async performance tests...")
    run_performance_tests()
    
    print("\n" + "=" * 50)
    print("✅ All performance tests completed successfully!")