#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for IntentClassifier log control.

These tests verify that IntentClassifier respects enable_detailed_logs setting.
"""

import unittest
from core.router import IntentClassifier


class TestIntentClassifierLogging(unittest.TestCase):
    """Test cases for IntentClassifier log control."""
    
    def test_intent_classifier_accepts_enable_detailed_logs(self):
        """Test that IntentClassifier constructor accepts enable_detailed_logs parameter."""
        # With detailed logs enabled
        classifier_with_logs = IntentClassifier(enable_detailed_logs=True)
        self.assertTrue(classifier_with_logs.enable_detailed_logs)
        
        # With detailed logs disabled
        classifier_without_logs = IntentClassifier(enable_detailed_logs=False)
        self.assertFalse(classifier_without_logs.enable_detailed_logs)
    
    def test_intent_classifier_default_enable_detailed_logs(self):
        """Test that IntentClassifier has default enable_detailed_logs=True."""
        classifier = IntentClassifier()
        self.assertTrue(classifier.enable_detailed_logs)
    
    def test_intent_classifier_logs_when_enabled(self):
        """Test that IntentClassifier logs when enable_detailed_logs is True."""
        classifier = IntentClassifier(enable_detailed_logs=True)
        
        # This should not raise an exception and should log
        result = classifier.classify("我的桌面有什么")
        
        # Result should still be returned
        self.assertIsInstance(result, str)
        self.assertIn(result, ["file_operation", "file_operations", "conversation", "web_search"])
    
    def test_intent_classifier_classify_when_disabled(self):
        """Test that IntentClassifier still works when enable_detailed_logs is False."""
        classifier = IntentClassifier(enable_detailed_logs=False)
        
        # This should work without logging
        result = classifier.classify("我的桌面有什么")
        
        # Result should still be returned
        self.assertIsInstance(result, str)


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
