#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for IntentClassifier log control.

DEPRECATED: This module has been removed.
IntentClassifier is no longer part of the architecture.
Please use the new LLM-driven architecture instead.
See: core/llm_tool_selector.py and docs/MIGRATION_GUIDE.md
"""

import unittest
import warnings


class TestIntentClassifierLogging(unittest.TestCase):
    """Test cases for IntentClassifier log control - DEPRECATED."""

    def test_intent_classifier_deprecated(self):
        """Test that IntentClassifier raises DeprecationWarning."""
        with self.assertWarns(DeprecationWarning):
            from core.router import IntentClassifier
            # This should raise DeprecationWarning
            try:
                classifier = IntentClassifier()
            except Exception:
                pass  # Expected to fail with deprecation warning


class TestSessionLogging(unittest.TestCase):
    """Test cases for Session log control."""
    
    def test_session_accepts_enable_detailed_logs(self):
        """Test that SessionConfig accepts enable_detailed_logs parameter."""
        from core.session import SessionConfig, Session
        
        config = SessionConfig(enable_detailed_logs=False)
        self.assertFalse(config.enable_detailed_logs)
    
    def test_session_default_enable_detailed_logs(self):
        """Test that SessionConfig has default enable_detailed_logs=True."""
        from core.session import SessionConfig
        
        config = SessionConfig()
        self.assertTrue(config.enable_detailed_logs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
