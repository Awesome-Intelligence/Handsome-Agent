#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the homeassistant_tool module.

Tests cover Home Assistant integration including:
- Entity listing
- State retrieval
- Service listing
- Service calling
"""

import pytest
import json
from unittest.mock import patch, MagicMock


class TestHAListEntities:
    """Test suite for ha_list_entities."""

    def test_list_entities_returns_json(self):
        """Test that list_entities returns valid JSON."""
        from tools.homeassistant_tool import ha_list_entities
        
        # Without HA configured, should return error but valid JSON
        result = ha_list_entities()
        assert isinstance(result, str)
        
        data = json.loads(result)
        assert "success" in data
        assert isinstance(data["success"], bool)


class TestHAGetState:
    """Test suite for ha_get_state."""

    def test_get_state_returns_json(self):
        """Test that get_state returns valid JSON."""
        from tools.homeassistant_tool import ha_get_state
        
        result = ha_get_state(entity_id="light.test")
        assert isinstance(result, str)
        
        data = json.loads(result)
        assert "success" in data
        assert "entity_id" in data


class TestHAListServices:
    """Test suite for ha_list_services."""

    def test_list_services_returns_json(self):
        """Test that list_services returns valid JSON."""
        from tools.homeassistant_tool import ha_list_services
        
        result = ha_list_services()
        assert isinstance(result, str)
        
        data = json.loads(result)
        assert "success" in data


class TestHACallService:
    """Test suite for ha_call_service."""

    def test_call_service_returns_json(self):
        """Test that call_service returns valid JSON."""
        from tools.homeassistant_tool import ha_call_service
        
        result = ha_call_service(domain="light", service="turn_on")
        assert isinstance(result, str)
        
        data = json.loads(result)
        assert "success" in data
        assert data["domain"] == "light"
        assert data["service"] == "turn_on"

    def test_call_service_with_entity(self):
        """Test call_service with entity_id."""
        from tools.homeassistant_tool import ha_call_service
        
        result = ha_call_service(
            domain="light",
            service="turn_on",
            entity_id="light.living_room"
        )
        data = json.loads(result)
        
        assert data["entity_id"] == "light.living_room"


class TestHAConfig:
    """Test Home Assistant configuration."""

    def test_get_ha_config(self):
        """Test getting HA config."""
        from tools.homeassistant_tool import _get_ha_config
        
        config = _get_ha_config()
        # May be None if not configured
        assert config is None or isinstance(config, dict)


class TestHARequest:
    """Test HA request functionality."""

    def test_ha_request_without_config(self):
        """Test HA request without configuration."""
        from tools.homeassistant_tool import _ha_request
        
        with pytest.raises(RuntimeError) as exc_info:
            _ha_request("GET", "/states")
        
        assert "not configured" in str(exc_info.value)


class TestHomeAssistantSchemas:
    """Test tool schemas."""

    def test_list_entities_schema(self):
        """Test ha_list_entities schema structure."""
        from tools.homeassistant_tool import HA_LIST_ENTITIES_SCHEMA
        
        assert "name" in HA_LIST_ENTITIES_SCHEMA
        assert HA_LIST_ENTITIES_SCHEMA["name"] == "ha_list_entities"

    def test_get_state_schema(self):
        """Test ha_get_state schema structure."""
        from tools.homeassistant_tool import HA_GET_STATE_SCHEMA
        
        assert "name" in HA_GET_STATE_SCHEMA
        assert HA_GET_STATE_SCHEMA["name"] == "ha_get_state"
        assert "parameters" in HA_GET_STATE_SCHEMA

    def test_call_service_schema(self):
        """Test ha_call_service schema structure."""
        from tools.homeassistant_tool import HA_CALL_SERVICE_SCHEMA
        
        assert "name" in HA_CALL_SERVICE_SCHEMA
        assert HA_CALL_SERVICE_SCHEMA["name"] == "ha_call_service"


class TestHomeAssistantRegistry:
    """Test tool registry integration."""

    def test_tools_registered(self):
        """Test that all HA tools are registered."""
        from tools.registry import registry
        
        expected_tools = [
            "ha_list_entities",
            "ha_get_state",
            "ha_list_services",
            "ha_call_service"
        ]
        
        for tool_name in expected_tools:
            tool = registry.get(tool_name)
            assert tool is not None, f"Tool {tool_name} should be registered"

    def test_tools_have_handlers(self):
        """Test that all tools have handlers."""
        from tools.registry import registry
        
        tools = registry.get_by_toolset("homeassistant")
        assert len(tools) == 4
        
        for tool in tools:
            assert tool.handler is not None


class TestCheckHAAvailable:
    """Test HA availability checking."""

    def test_check_ha_available(self):
        """Test HA availability check."""
        from tools.homeassistant_tool import _check_ha_available
        
        result = _check_ha_available()
        assert isinstance(result, bool)
        assert result is False  # Should be False without config


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
