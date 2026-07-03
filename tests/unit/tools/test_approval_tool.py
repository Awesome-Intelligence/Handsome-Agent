#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Approval Tool module.

Tests cover:
- request_approval() function
- check_approval_requirements() function
- APPROVAL_SCHEMA structure
- Tool registration
"""

import pytest
import json
from unittest.mock import MagicMock, patch


class TestRequestApproval:
    """Tests for request_approval() function."""

    def test_request_approval_returns_json(self):
        """request_approval() returns a JSON string."""
        from tools.approval_tool import request_approval

        result = request_approval(action="delete_file", description="Delete a file")

        assert isinstance(result, str)
        # Should be valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_request_approval_contains_action_and_description(self):
        """request_approval() includes action and description in result."""
        from tools.approval_tool import request_approval

        result = request_approval(
            action="execute_command",
            description="Run a shell command",
            details="ls -la",
        )

        parsed = json.loads(result)
        assert parsed["action"] == "execute_command"
        assert parsed["description"] == "Run a shell command"
        assert parsed["details"] == "ls -la"

    def test_request_approval_with_minimal_args(self):
        """request_approval() works with only required arguments."""
        from tools.approval_tool import request_approval

        result = request_approval(action="test", description="Test action")

        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["approved"] is False
        assert "placeholder" in parsed["message"].lower()

    def test_request_approval_with_all_args(self):
        """request_approval() handles all optional arguments."""
        from tools.approval_tool import request_approval

        result = request_approval(
            action="modify_system",
            description="Modify system configuration",
            details="Change /etc/config",
        )

        parsed = json.loads(result)
        assert parsed["action"] == "modify_system"
        assert parsed["description"] == "Modify system configuration"
        assert parsed["details"] == "Change /etc/config"

    def test_request_approval_always_returns_not_approved(self):
        """request_approval() always returns approved=False (placeholder)."""
        from tools.approval_tool import request_approval

        # Multiple calls should all return not approved
        for _ in range(3):
            result = request_approval(
                action="any_action", description="Any description"
            )
            parsed = json.loads(result)
            assert parsed["approved"] is False


class TestCheckApprovalRequirements:
    """Tests for check_approval_requirements() function."""

    def test_check_approval_requirements_returns_true(self):
        """check_approval_requirements() returns True (no external dependencies)."""
        from tools.approval_tool import check_approval_requirements

        assert check_approval_requirements() is True

    def test_check_approval_requirements_is_callable(self):
        """check_approval_requirements() is a callable function."""
        from tools.approval_tool import check_approval_requirements

        assert callable(check_approval_requirements)


class TestApprovalSchema:
    """Tests for APPROVAL_SCHEMA tool definition."""

    def test_approval_schema_is_defined(self):
        """APPROVAL_SCHEMA is defined."""
        from tools.approval_tool import APPROVAL_SCHEMA

        assert APPROVAL_SCHEMA is not None
        assert isinstance(APPROVAL_SCHEMA, dict)

    def test_approval_schema_has_required_fields(self):
        """APPROVAL_SCHEMA has all required fields."""
        from tools.approval_tool import APPROVAL_SCHEMA

        assert "name" in APPROVAL_SCHEMA
        assert "description" in APPROVAL_SCHEMA
        assert "parameters" in APPROVAL_SCHEMA

    def test_approval_schema_name(self):
        """APPROVAL_SCHEMA has correct tool name."""
        from tools.approval_tool import APPROVAL_SCHEMA

        assert APPROVAL_SCHEMA["name"] == "request_approval"

    def test_approval_schema_parameters_type(self):
        """APPROVAL_SCHEMA parameters is an object type."""
        from tools.approval_tool import APPROVAL_SCHEMA

        assert APPROVAL_SCHEMA["parameters"]["type"] == "object"

    def test_approval_schema_required_fields(self):
        """APPROVAL_SCHEMA has required fields defined."""
        from tools.approval_tool import APPROVAL_SCHEMA

        assert "required" in APPROVAL_SCHEMA["parameters"]
        assert "action" in APPROVAL_SCHEMA["parameters"]["required"]
        assert "description" in APPROVAL_SCHEMA["parameters"]["required"]

    def test_approval_schema_properties(self):
        """APPROVAL_SCHEMA defines all required properties."""
        from tools.approval_tool import APPROVAL_SCHEMA

        props = APPROVAL_SCHEMA["parameters"]["properties"]
        assert "action" in props
        assert "description" in props
        assert "details" in props

    def test_approval_schema_action_property(self):
        """APPROVAL_SCHEMA action property is correctly defined."""
        from tools.approval_tool import APPROVAL_SCHEMA

        action_prop = APPROVAL_SCHEMA["parameters"]["properties"]["action"]
        assert action_prop["type"] == "string"
        assert "description" in action_prop

    def test_approval_schema_description_property(self):
        """APPROVAL_SCHEMA description property is correctly defined."""
        from tools.approval_tool import APPROVAL_SCHEMA

        desc_prop = APPROVAL_SCHEMA["parameters"]["properties"]["description"]
        assert desc_prop["type"] == "string"
        assert "description" in desc_prop

    def test_approval_schema_details_property(self):
        """APPROVAL_SCHEMA details property is correctly defined."""
        from tools.approval_tool import APPROVAL_SCHEMA

        details_prop = APPROVAL_SCHEMA["parameters"]["properties"]["details"]
        assert details_prop["type"] == "string"


class TestApprovalToolRegistration:
    """Tests for tool registration."""

    def test_approval_tool_is_registered(self):
        """The approval tool is registered in the registry."""
        from tools.registry import registry
        from tools.approval_tool import APPROVAL_SCHEMA

        # Check that the tool is registered
        tool = registry.get(APPROVAL_SCHEMA["name"])
        assert tool is not None

    def test_registered_tool_has_schema(self):
        """Registered approval tool has the correct schema."""
        from tools.registry import registry
        from tools.approval_tool import APPROVAL_SCHEMA

        tool = registry.get(APPROVAL_SCHEMA["name"])
        assert tool.schema is not None
        assert tool.schema["name"] == "request_approval"

    def test_registered_tool_has_handler(self):
        """Registered approval tool has a handler."""
        from tools.registry import registry
        from tools.approval_tool import APPROVAL_SCHEMA

        tool = registry.get(APPROVAL_SCHEMA["name"])
        assert tool.handler is not None
        assert callable(tool.handler)

    def test_registered_tool_has_check_function(self):
        """Registered approval tool has a check function."""
        from tools.registry import registry
        from tools.approval_tool import APPROVAL_SCHEMA

        tool = registry.get(APPROVAL_SCHEMA["name"])
        assert tool.check_fn is not None

    def test_registered_tool_has_toolset(self):
        """Registered approval tool has a toolset."""
        from tools.registry import registry
        from tools.approval_tool import APPROVAL_SCHEMA

        tool = registry.get(APPROVAL_SCHEMA["name"])
        assert tool.toolset == "approval"

    def test_registered_tool_has_emoji(self):
        """Registered approval tool has an emoji."""
        from tools.registry import registry
        from tools.approval_tool import APPROVAL_SCHEMA

        tool = registry.get(APPROVAL_SCHEMA["name"])
        assert tool.emoji is not None
        assert len(tool.emoji) > 0


class TestApprovalToolIntegration:
    """Integration tests for approval tool."""

    def test_tool_handler_returns_valid_json(self):
        """Tool handler returns valid JSON string."""
        from tools.registry import registry
        from tools.approval_tool import APPROVAL_SCHEMA

        tool = registry.get(APPROVAL_SCHEMA["name"])
        result = tool.handler(
            {"action": "test_action", "description": "Test description"}
        )

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["success"] is True

    def test_tool_handler_handles_missing_optional_args(self):
        """Tool handler handles missing optional arguments."""
        from tools.registry import registry
        from tools.approval_tool import APPROVAL_SCHEMA

        tool = registry.get(APPROVAL_SCHEMA["name"])
        # Only required args
        result = tool.handler({"action": "test", "description": "Test"})

        parsed = json.loads(result)
        assert parsed["action"] == "test"
        assert parsed["description"] == "Test"
        assert parsed["details"] is None

    def test_check_fn_allows_execution(self):
        """check_fn returns True, allowing tool execution."""
        from tools.registry import registry
        from tools.approval_tool import APPROVAL_SCHEMA

        tool = registry.get(APPROVAL_SCHEMA["name"])
        assert tool.check_fn() is True
