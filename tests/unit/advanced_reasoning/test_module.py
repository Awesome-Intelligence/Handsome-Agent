#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the Advanced Reasoning module.

These tests cover knowledge base loading, input classification, and response generation.
"""

import unittest
from core import AgentConfig
from advanced_reasoning.module import AdvancedReasoningModule


class TestAdvancedReasoningModule(unittest.TestCase):
    """Test AdvancedReasoningModule functionality."""
    
    def setUp(self):
        """Set up advanced reasoning module."""
        self.module = AdvancedReasoningModule(AgentConfig(enable_caching=False))
    
    def test_knowledge_base_loading(self):
        """Test that knowledge base loads correctly."""
        kb = self.module._load_knowledge_base()
        self.assertIsInstance(kb, dict)
        self.assertIn("programming", kb)
        self.assertIn("machine_learning", kb)
        self.assertIn("system_design", kb)
    
    def test_input_classification(self):
        """Test advanced input classification."""
        # Programming queries
        self.assertEqual(self.module._classify_input("How do I optimize Python code?"), 'programming')
        self.assertEqual(self.module._classify_input("Write a function to sort a list"), 'programming')
        
        # Machine learning queries
        self.assertEqual(self.module._classify_input("What is neural network?"), 'machine_learning')
        self.assertEqual(self.module._classify_input("Explain deep learning concepts"), 'machine_learning')
        self.assertEqual(self.module._classify_input("What is artificial intelligence?"), 'machine_learning')
        self.assertEqual(self.module._classify_input("AI models are important"), 'machine_learning')
        
        # System design queries
        self.assertEqual(self.module._classify_input("REST vs GraphQL comparison"), 'system_design')
        self.assertEqual(self.module._classify_input("API architecture best practices"), 'system_design')
        
        # Conceptual queries
        self.assertEqual(self.module._classify_input("Explain how computers work"), 'conceptual')
        self.assertEqual(self.module._classify_input("How does the internet work?"), 'conceptual')
    
    def test_complexity_assessment(self):
        """Test complexity assessment in advanced module."""
        simple_query = "Hi"
        complex_query = "Can you explain neural networks with backpropagation and gradient descent in detail?"
        
        simple_complexity = self.module._assess_complexity(simple_query)
        complex_complexity = self.module._assess_complexity(complex_query)
        
        self.assertGreaterEqual(simple_complexity, 0)
        self.assertLessEqual(simple_complexity, 3)
        self.assertGreaterEqual(complex_complexity, 0)
        self.assertLessEqual(complex_complexity, 3)
        self.assertGreaterEqual(complex_complexity, simple_complexity)
    
    def test_specific_query_responses(self):
        """Test that specific queries generate appropriate responses."""
        # Fibonacci query
        fib_response = self.module._generate_intelligent_response(
            "How do I implement Fibonacci in Python?", 
            'programming', 
            2
        )
        self.assertIn("Fibonacci", fib_response)
        self.assertIn("def fibonacci", fib_response)
        
        # Python optimization query
        opt_response = self.module._generate_intelligent_response(
            "How can I optimize my Python code?",
            'programming',
            2
        )
        self.assertIn("optimization", opt_response.lower())
        self.assertIn("performance", opt_response.lower())
        
        # ML comparison query
        ml_response = self.module._generate_intelligent_response(
            "What's the difference between supervised and unsupervised learning?",
            'machine_learning',
            2
        )
        self.assertIn("supervised", ml_response.lower())
        self.assertIn("unsupervised", ml_response.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)