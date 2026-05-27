#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Custom exceptions for the Handsome Agent.

This module defines specific exception types that provide more granular
error handling and better error messages for different failure scenarios.

Each exception includes a standardized error code for programmatic error handling.

Error Codes:
    1001: Input validation failed
    1002: Response generation failed
    1003: Configuration error
    1004: Timeout error
    1005: Module not found

Author: Handsome Agent Team
Version: 1.0.0
"""

from typing import Optional


class AgentError(Exception):
    """Base exception class for all agent-related errors.
    
    Attributes:
        message: Descriptive error message.
        error_code: Unique error code for programmatic handling.
        original_exception: The original exception that caused this error (if any).
    """
    
    error_code: int = 1000
    
    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        """Initialize the agent error.
        
        Args:
            message: Descriptive error message.
            original_exception: The original exception that caused this error (if any).
        """
        super().__init__(message)
        self.original_exception = original_exception


class InputValidationError(AgentError):
    """Raised when user input fails validation.
    
    Error Code: 1001
    """
    
    error_code = 1001
    
    def __init__(self, message: str = "Invalid input provided"):
        """Initialize input validation error.
        
        Args:
            message: Specific validation error message.
        """
        super().__init__(message)


class ResponseGenerationError(AgentError):
    """Raised when response generation fails.
    
    Error Code: 1002
    """
    
    error_code = 1002
    
    def __init__(self, message: str = "Failed to generate response", original_exception: Optional[Exception] = None):
        """Initialize response generation error.
        
        Args:
            message: Specific generation error message.
            original_exception: The underlying exception that caused the failure.
        """
        super().__init__(message, original_exception)


class ConfigurationError(AgentError):
    """Raised when agent configuration is invalid.
    
    Error Code: 1003
    """
    
    error_code = 1003
    
    def __init__(self, message: str = "Invalid configuration"):
        """Initialize configuration error.
        
        Args:
            message: Specific configuration error message.
        """
        super().__init__(message)


class TimeoutError(AgentError):
    """Raised when response generation exceeds timeout limit.
    
    Error Code: 1004
    """
    
    error_code = 1004
    
    def __init__(self, timeout_seconds: float):
        """Initialize timeout error.
        
        Args:
            timeout_seconds: The timeout limit that was exceeded.
        """
        message = f"Response generation timed out after {timeout_seconds} seconds"
        super().__init__(message)


class ModuleNotFoundError(AgentError):
    """Raised when a required agent module cannot be found or loaded.
    
    Error Code: 1005
    """
    
    error_code = 1005
    
    def __init__(self, module_name: str):
        """Initialize module not found error.
        
        Args:
            module_name: The name of the missing module.
        """
        message = f"Required module '{module_name}' not found"
        super().__init__(message)