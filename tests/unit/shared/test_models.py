#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the shared module data models.

Tests cover BaseResponse, SessionInfo, HealthCheck, ErrorResponse models.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError


class TestBaseResponse:
    """Test BaseResponse model."""
    
    def test_default_values(self):
        """Test default values for BaseResponse."""
        from shared.models import BaseResponse
        
        response = BaseResponse()
        
        assert response.success is True
        assert response.message is None
        assert response.error_code is None
    
    def test_with_message(self):
        """Test BaseResponse with message."""
        from shared.models import BaseResponse
        
        response = BaseResponse(
            success=True,
            message="Operation completed"
        )
        
        assert response.success is True
        assert response.message == "Operation completed"
    
    def test_error_response(self):
        """Test BaseResponse for error case."""
        from shared.models import BaseResponse
        
        response = BaseResponse(
            success=False,
            message="Operation failed",
            error_code=1001
        )
        
        assert response.success is False
        assert response.message == "Operation failed"
        assert response.error_code == 1001


class TestSessionInfo:
    """Test SessionInfo model."""
    
    def test_auto_generated_fields(self):
        """Test auto-generated session_id and timestamps."""
        from shared.models import SessionInfo
        
        session = SessionInfo(user_id="user_001")
        
        assert session.session_id is not None
        assert len(session.session_id) > 0
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.last_active, datetime)
        assert isinstance(session.metadata, dict)
    
    def test_custom_session_id(self):
        """Test custom session ID."""
        from shared.models import SessionInfo
        
        session = SessionInfo(
            session_id="custom_session_123",
            user_id="user_001"
        )
        
        assert session.session_id == "custom_session_123"
    
    def test_with_metadata(self):
        """Test SessionInfo with metadata."""
        from shared.models import SessionInfo
        
        metadata = {
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
            "platform": "windows"
        }
        
        session = SessionInfo(
            user_id="user_001",
            metadata=metadata
        )
        
        assert session.metadata["ip_address"] == "192.168.1.1"
        assert session.metadata["user_agent"] == "Mozilla/5.0"
        assert session.metadata["platform"] == "windows"
    
    def test_update_last_active(self):
        """Test updating last_active timestamp."""
        from shared.models import SessionInfo
        import time
        
        session = SessionInfo(user_id="user_001")
        original_last_active = session.last_active
        
        time.sleep(0.01)  # Small delay
        session.last_active = datetime.now()
        
        assert session.last_active >= original_last_active


class TestHealthCheck:
    """Test HealthCheck model."""
    
    def test_default_health_check(self):
        """Test default health check values."""
        from shared.models import HealthCheck
        
        health = HealthCheck()
        
        assert health.status == "healthy"
        assert health.version == "1.0.0"
        assert isinstance(health.timestamp, datetime)
        assert isinstance(health.services, dict)
    
    def test_custom_status(self):
        """Test custom health check status."""
        from shared.models import HealthCheck
        
        health = HealthCheck(
            status="degraded",
            services={
                "brain": "healthy",
                "executor": "unhealthy"
            }
        )
        
        assert health.status == "degraded"
        assert health.services["brain"] == "healthy"
        assert health.services["executor"] == "unhealthy"
    
    def test_healthy_status(self):
        """Test healthy status."""
        from shared.models import HealthCheck
        
        health = HealthCheck(
            status="healthy",
            services={
                "brain": "healthy",
                "executor": "healthy"
            }
        )
        
        assert health.status == "healthy"
        assert all(s == "healthy" for s in health.services.values())


class TestErrorResponse:
    """Test ErrorResponse model."""
    
    def test_error_response_required_fields(self):
        """Test required fields for ErrorResponse."""
        from shared.models import ErrorResponse
        
        error = ErrorResponse(
            error="Something went wrong",
            code=500
        )
        
        assert error.error == "Something went wrong"
        assert error.code == 500
        assert isinstance(error.timestamp, datetime)
    
    def test_error_response_with_details(self):
        """Test ErrorResponse with details."""
        from shared.models import ErrorResponse
        
        details = {
            "field": "username",
            "reason": "too_short",
            "min_length": 3
        }
        
        error = ErrorResponse(
            error="Validation failed",
            code=400,
            details=details
        )
        
        assert error.details["field"] == "username"
        assert error.details["reason"] == "too_short"
        assert error.details["min_length"] == 3
    
    def test_error_response_various_codes(self):
        """Test various error codes."""
        from shared.models import ErrorResponse
        
        # 400 Bad Request
        error_400 = ErrorResponse(error="Bad request", code=400)
        assert error_400.code == 400
        
        # 401 Unauthorized
        error_401 = ErrorResponse(error="Unauthorized", code=401)
        assert error_401.code == 401
        
        # 404 Not Found
        error_404 = ErrorResponse(error="Not found", code=404)
        assert error_404.code == 404
        
        # 500 Internal Server Error
        error_500 = ErrorResponse(error="Internal error", code=500)
        assert error_500.code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
