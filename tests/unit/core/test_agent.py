#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the Core module.

These tests cover the basic agent functionality, configuration management,
and core response generation capabilities.
"""

import asyncio
import unittest
from core import CustomAgent, AgentConfig, AgentResponse


class TestCustomAgent(unittest.TestCase):
    """Test cases for the CustomAgent class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.agent = CustomAgent(AgentConfig(
            name="TestAgent",
            explanation_depth="brief",
            response_format="plain"
        ))
    
    def test_agent_initialization(self):
        """Test that agent initializes correctly."""
        self.assertIsNotNone(self.agent.config)
        self.assertIsNotNone(self.agent.explanation_module)
        self.assertIsNotNone(self.agent.logger)
    
    def test_config_creation(self):
        """Test AgentConfig creation."""
        config = AgentConfig()
        self.assertEqual(config.name, "CustomAgent")
        self.assertEqual(config.explanation_depth, "detailed")
        self.assertTrue(config.enable_caching)
    
    def test_basic_response(self):
        """Test basic response generation."""
        import asyncio
        response = asyncio.run(self.agent.respond("Hello, world!"))
        self.assertIsInstance(response, AgentResponse)
        self.assertIsInstance(response.content, str)
        self.assertGreater(len(response.content), 0)
        self.assertGreaterEqual(response.confidence_score, 0.0)
        self.assertLessEqual(response.confidence_score, 1.0)
    
    def test_input_classification(self):
        """Test input classification logic."""
        from core import ExplanationModule
        
        module = ExplanationModule(self.agent.config)
        
        # Test different input types
        code_input = "How do I write a Python function?"
        conceptual_input = "What is machine learning?"
        problem_input = "How can I solve this debugging issue?"
        general_input = "Hello, how are you today?"
        
        self.assertEqual(module._classify_input(code_input), 'code_request')
        self.assertEqual(module._classify_input(conceptual_input), 'conceptual_question')
        self.assertEqual(module._classify_input(problem_input), 'problem_solving')
        self.assertEqual(module._classify_input(general_input), 'general_inquiry')
    
    def test_complexity_assessment(self):
        """Test complexity assessment."""
        from core import ExplanationModule
        
        module = ExplanationModule(self.agent.config)
        
        simple_input = "Hi"
        complex_input = "Can you explain how neural networks work with backpropagation and gradient descent in detail?"
        
        simple_complexity = module._assess_complexity(simple_input)
        complex_complexity = module._assess_complexity(complex_input)
        
        self.assertGreaterEqual(simple_complexity, 0)
        self.assertLessEqual(simple_complexity, 3)
        self.assertGreaterEqual(complex_complexity, 0)
        self.assertLessEqual(complex_complexity, 3)


def run_async_test():
    """Helper to run async tests."""
    async def run_tests():
        agent = CustomAgent()
        response = await agent.respond("Test query")
        assert isinstance(response, AgentResponse)
        assert len(response.content) > 0
        print("Async test passed!")
    
    asyncio.run(run_tests())


if __name__ == "__main__":
    # Run basic tests
    print("Running basic tests...")
    
    # Test async functionality
    run_async_test()
    
    # Run unit tests
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    print("All tests completed!")