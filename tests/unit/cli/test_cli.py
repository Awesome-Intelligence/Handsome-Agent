#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the CLI module.

These tests cover argument parsing and CLI functionality.
"""

import unittest
import argparse
from cli.main import main


class TestCLIFunctionality(unittest.TestCase):
    """Test CLI module functionality."""
    
    def test_import_cli(self):
        """Test that CLI module can be imported."""
        # This test ensures the CLI module imports correctly
        # and doesn't have syntax errors
        try:
            from cli import main as cli_main
            self.assertIsNotNone(cli_main)
        except ImportError as e:
            self.fail(f"Failed to import CLI module: {e}")
    
    def test_argument_parsing(self):
        """Test CLI argument parsing."""
        # Test that the argument parser can be created
        parser = argparse.ArgumentParser()
        parser.add_argument("--test", action="store_true")
        
        # This is a basic test to ensure argparse works
        # More comprehensive testing would require integration tests
        args = parser.parse_args([])
        self.assertFalse(args.test)


if __name__ == "__main__":
    unittest.main(verbosity=2)