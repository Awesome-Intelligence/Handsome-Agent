#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the Core module exception handling.

These tests cover custom exception classes and error handling functionality.
"""

import unittest
from core.exceptions import (
    AgentError,
    InputValidationError,
    ResponseGenerationError,
    ConfigurationError,
    TimeoutError
)


class TestExceptionClasses(unittest.TestCase):
    """Test custom exception classes."""
    
    def test_agent_error(self):
        """Test AgentError base class."""
        error = AgentError("Test message")
        self.assertEqual(str(error), "Test message")
        self.assertIsInstance(error, Exception)
    
    def test_input_validation_error(self):
        """Test InputValidationError."""
        error = InputValidationError("Test message")
        self.assertEqual(str(error), "Test message")
        self.assertIsInstance(error, AgentError)
    
    def test_response_generation_error(self):
        """Test ResponseGenerationError."""
        error = ResponseGenerationError("Test message")
        self.assertEqual(str(error), "Test message")
        self.assertIsInstance(error, AgentError)
    
    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError("Test message")
        self.assertEqual(str(error), "Test message")
        self.assertIsInstance(error, AgentError)
    
    def test_timeout_error(self):
        """Test TimeoutError."""
        error = TimeoutError(5.0)
        self.assertIn("5.0", str(error))
        self.assertIsInstance(error, AgentError)


if __name__ == "__main__":
    unittest.main(verbosity=2)