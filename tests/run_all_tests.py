#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test runner script for Handsome Agent.

This script runs all unit tests and generates a coverage report.
"""

import pytest
import sys
from pathlib import Path


def run_tests():
    """Run all tests with coverage."""
    
    # Add project root to path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    
    # Test arguments
    args = [
        "tests/",
        "-v",                          # Verbose output
        "--tb=short",                   # Short traceback format
        "--strict-markers",             # Strict marker checking
        "--disable-warnings",           # Disable warnings in output
        "-p", "no:warnings",           # Don't capture warnings
    ]
    
    # Add coverage if pytest-cov is available
    try:
        import pytest_cov
        args.extend([
            "--cov=.",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-report=xml",
        ])
    except ImportError:
        print("Warning: pytest-cov not installed, skipping coverage")
    
    # Run tests
    exit_code = pytest.main(args)
    
    return exit_code


if __name__ == "__main__":
    print("=" * 80)
    print("Handsome Agent - Test Suite")
    print("=" * 80)
    print()
    
    exit_code = run_tests()
    
    print()
    print("=" * 80)
    if exit_code == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    print("=" * 80)
    
    sys.exit(exit_code)
