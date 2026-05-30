#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the shared module logging.

Tests cover logging configuration and logger creation.
"""

import pytest
import logging


class TestLoggingSetup:
    """Test logging configuration."""
    
    def test_setup_logging_default(self):
        """Test default logging setup."""
        from shared.logging import setup_logging
        
        # Should not raise
        setup_logging()
    
    def test_setup_logging_with_level(self):
        """Test logging setup with custom level."""
        from shared.logging import setup_logging
        
        # Should not raise
        setup_logging(level=logging.DEBUG)
    
    def test_setup_logging_with_file(self):
        """Test logging setup with file handler."""
        import tempfile
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            
            from shared.logging import setup_logging
            setup_logging(log_file=str(log_file))
            
            # Check that file was created
            assert log_file.exists()


class TestLoggerCreation:
    """Test logger creation utilities."""
    
    def test_get_logger_with_name(self):
        """Test creating a logger with a specific name."""
        from shared.logging import get_logger
        
        logger = get_logger("test_module")
        
        assert logger.name == "test_module"
        assert isinstance(logger, logging.Logger)
    
    def test_get_logger_returns_logger(self):
        """Test that get_logger returns proper logger instance."""
        from shared.logging import get_logger
        
        logger = get_logger("test")
        
        assert isinstance(logger, logging.Logger)
        assert hasattr(logger, 'debug')
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'error')


class TestLogConfiguration:
    """Test logging configuration side effects."""
    
    def test_setup_logging_configures_uvicorn(self):
        """Test that setup_logging configures uvicorn logger."""
        from shared.logging import setup_logging
        
        setup_logging()
        
        uvicorn_logger = logging.getLogger("uvicorn")
        assert uvicorn_logger.level <= logging.WARNING
    
    def test_setup_logging_configures_fastapi(self):
        """Test that setup_logging configures fastapi logger."""
        from shared.logging import setup_logging
        
        setup_logging()
        
        fastapi_logger = logging.getLogger("fastapi")
        assert fastapi_logger.level <= logging.WARNING
    
    def test_setup_logging_configures_brain_loggers(self):
        """Test that setup_logging configures brain module loggers."""
        from shared.logging import setup_logging
        
        setup_logging()
        
        brain_loggers = [
            "brain_trajectory",
            "brain_curator",
            "brain.agent",
            "brain.service"
        ]
        
        for logger_name in brain_loggers:
            logger = logging.getLogger(logger_name)
            assert logger.level <= logging.INFO


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
