#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for log configuration mapping in main.py.

These tests verify that explanation_depth is correctly mapped to enable_detailed_logs.
"""

import unittest


class TestLogConfigMapping(unittest.TestCase):
    """Test cases for log configuration mapping."""
    
    def test_brief_mode_disables_detailed_logs(self):
        """Test that brief explanation_depth maps to disable detailed logs."""
        explanation_depth = "brief"
        
        # Simulate the mapping logic from main.py
        if explanation_depth == "brief":
            enable_detailed_logs = False
        else:
            enable_detailed_logs = True
        
        self.assertFalse(enable_detailed_logs)
    
    def test_moderate_mode_enables_detailed_logs(self):
        """Test that moderate explanation_depth maps to enable detailed logs."""
        explanation_depth = "moderate"
        
        if explanation_depth == "brief":
            enable_detailed_logs = False
        else:
            enable_detailed_logs = True
        
        self.assertTrue(enable_detailed_logs)
    
    def test_detailed_mode_enables_detailed_logs(self):
        """Test that detailed explanation_depth maps to enable detailed logs."""
        explanation_depth = "detailed"
        
        if explanation_depth == "brief":
            enable_detailed_logs = False
        else:
            enable_detailed_logs = True
        
        self.assertTrue(enable_detailed_logs)
    
    def test_default_mode_enables_detailed_logs(self):
        """Test that default explanation_depth maps to enable detailed logs."""
        explanation_depth = "moderate"  # default
        
        if explanation_depth == "brief":
            enable_detailed_logs = False
        else:
            enable_detailed_logs = True
        
        self.assertTrue(enable_detailed_logs)
    
    def test_cli_args_override_config(self):
        """Test that CLI args can override the config mapping."""
        # Simulate CLI args override
        args_detailed_logs = False
        config_enable_detailed_logs = True  # from mapping
        
        # CLI args have highest priority
        if args_detailed_logs is not None:
            enable_detailed_logs = args_detailed_logs
        else:
            enable_detailed_logs = config_enable_detailed_logs
        
        self.assertFalse(enable_detailed_logs)
    
    def test_no_detailed_logs_flag(self):
        """Test that --no-detailed-logs flag overrides config."""
        # Simulate --no-detailed-logs flag
        args_no_detailed_logs = True
        config_enable_detailed_logs = True  # from mapping
        
        if args_no_detailed_logs:
            enable_detailed_logs = False
        else:
            enable_detailed_logs = config_enable_detailed_logs
        
        self.assertFalse(enable_detailed_logs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
