#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the Skill Namespace module.

Tests cover:
- Namespace registration and unregistration
- Skill resolution with namespace:skill-name format
- Same-name conflict detection
- Reserved namespace checking
- Default namespace handling
"""

import pytest
import sys
from pathlib import Path

# 直接从 skill_namespace.py 导入，避免触发其他模块的初始化
import importlib.util
spec = importlib.util.spec_from_file_location(
    "skill_namespace",
    Path(__file__).parent.parent.parent.parent / "agent" / "skill_namespace.py"
)
skill_namespace_module = importlib.util.module_from_spec(spec)
sys.modules["skill_namespace"] = skill_namespace_module
spec.loader.exec_module(skill_namespace_module)

SkillNamespace = skill_namespace_module.SkillNamespace
QualifiedSkill = skill_namespace_module.QualifiedSkill
parse_qualified_name = skill_namespace_module.parse_qualified_name
DEFAULT_NAMESPACE = skill_namespace_module.DEFAULT_NAMESPACE
RESERVED_NAMESPACES = skill_namespace_module.RESERVED_NAMESPACES


class TestQualifiedSkill:
    """Test QualifiedSkill dataclass."""

    def test_creation(self):
        """Test creating a QualifiedSkill."""
        skill = QualifiedSkill(
            namespace="test",
            skill_name="my_skill",
            full_name="test:my_skill",
            source="/path/to/skill"
        )
        assert skill.namespace == "test"
        assert skill.skill_name == "my_skill"
        assert skill.full_name == "test:my_skill"
        assert skill.source == "/path/to/skill"

    def test_default_source(self):
        """Test default source is empty string."""
        skill = QualifiedSkill(
            namespace="test",
            skill_name="my_skill",
            full_name="test:my_skill"
        )
        assert skill.source == ""


class TestSkillNamespaceInit:
    """Test SkillNamespace initialization."""

    def test_init_empty_registry(self):
        """Test initialization creates empty registry."""
        ns = SkillNamespace()
        assert ns.registry.namespace_skills == {}
        assert ns.registry.skill_namespaces == {}
        assert ns._aliases == {}

    def test_default_namespace_constant(self):
        """Test DEFAULT_NAMESPACE is correct."""
        assert DEFAULT_NAMESPACE == "default"

    def test_reserved_namespaces_constant(self):
        """Test RESERVED_NAMESPACES contains expected values."""
        assert "system" in RESERVED_NAMESPACES
        assert "user" in RESERVED_NAMESPACES
        assert "external" in RESERVED_NAMESPACES
        assert "default" in RESERVED_NAMESPACES


class TestSkillRegistration:
    """Test skill registration."""

    def test_register_simple_skill(self):
        """Test registering a skill in default namespace."""
        ns = SkillNamespace()
        qualified = ns.register("my_skill")
        
        assert qualified.namespace == "default"
        assert qualified.skill_name == "my_skill"
        assert qualified.full_name == "default:my_skill"
        
        assert "default" in ns.list_namespaces()
        assert "my_skill" in ns.registry.namespace_skills["default"]

    def test_register_with_custom_namespace(self):
        """Test registering a skill in custom namespace."""
        ns = SkillNamespace()
        qualified = ns.register("my_skill", namespace="custom")
        
        assert qualified.namespace == "custom"
        assert qualified.full_name == "custom:my_skill"

    def test_register_with_path(self):
        """Test registering a skill with path."""
        ns = SkillNamespace()
        path = Path("/skills/my_skill")
        qualified = ns.register("my_skill", skill_path=path)
        
        assert qualified.source == str(path)

    def test_register_normalizes_namespace(self):
        """Test registering normalizes namespace to lowercase."""
        ns = SkillNamespace()
        qualified = ns.register("my_skill", namespace="CustomNamespace")
        
        assert qualified.namespace == "customnamespace"
        assert qualified.full_name == "customnamespace:my_skill"

    def test_register_same_skill_different_namespaces(self):
        """Test registering same skill name in different namespaces."""
        ns = SkillNamespace()
        ns.register("my_skill", namespace="ns1")
        ns.register("my_skill", namespace="ns2")
        
        assert "ns1" in ns.list_namespaces()
        assert "ns2" in ns.list_namespaces()
        assert ns.registry.namespace_skills["ns1"] == {"my_skill"}
        assert ns.registry.namespace_skills["ns2"] == {"my_skill"}


class TestSkillUnregistration:
    """Test skill unregistration."""

    def test_unregister_skill_from_namespace(self):
        """Test unregistering a skill from specific namespace."""
        ns = SkillNamespace()
        ns.register("my_skill", namespace="test")
        result = ns.unregister("my_skill", namespace="test")
        
        assert result is True
        assert "test" not in ns.list_namespaces()

    def test_unregister_nonexistent_returns_false(self):
        """Test unregistering non-existent skill returns False."""
        ns = SkillNamespace()
        result = ns.unregister("nonexistent", namespace="test")
        
        assert result is False

    def test_unregister_from_all_namespaces(self):
        """Test unregistering removes skill from all namespaces."""
        ns = SkillNamespace()
        ns.register("my_skill", namespace="ns1")
        ns.register("my_skill", namespace="ns2")
        
        result = ns.unregister("my_skill")
        
        assert result is True
        assert ns.list_namespaces() == []

    def test_unregister_specific_namespace_preserves_others(self):
        """Test unregistering from one namespace preserves others."""
        ns = SkillNamespace()
        ns.register("my_skill", namespace="ns1")
        ns.register("my_skill", namespace="ns2")
        
        ns.unregister("my_skill", namespace="ns1")
        
        assert "ns1" not in ns.list_namespaces()
        assert "ns2" in ns.list_namespaces()


class TestSkillResolution:
    """Test skill resolution."""

    def test_resolve_simple_name(self):
        """Test resolving simple skill name."""
        ns = SkillNamespace()
        ns.register("my_skill")
        
        qualified = ns.resolve("my_skill")
        
        assert qualified is not None
        assert qualified.full_name == "default:my_skill"

    def test_resolve_qualified_name(self):
        """Test resolving namespace:skill-name format."""
        ns = SkillNamespace()
        ns.register("my_skill", namespace="custom")
        
        qualified = ns.resolve("custom:my_skill")
        
        assert qualified is not None
        assert qualified.namespace == "custom"
        assert qualified.skill_name == "my_skill"

    def test_resolve_nonexistent_returns_none(self):
        """Test resolving non-existent skill returns None."""
        ns = SkillNamespace()
        qualified = ns.resolve("nonexistent")
        
        assert qualified is None

    def test_resolve_returns_none_for_wrong_namespace(self):
        """Test resolving skill with wrong namespace returns None."""
        ns = SkillNamespace()
        ns.register("my_skill", namespace="ns1")
        
        qualified = ns.resolve("ns2:my_skill")
        
        assert qualified is None

    def test_resolve_falls_back_to_default_namespace(self):
        """Test resolving simple name falls back to default namespace."""
        ns = SkillNamespace()
        ns.register("my_skill", namespace="custom")
        ns.register("my_skill", namespace="default")
        
        qualified = ns.resolve("my_skill")
        
        assert qualified is not None
        assert qualified.namespace == "default"


class TestConflictDetection:
    """Test same-name conflict detection."""

    def test_check_conflict_with_conflicts(self):
        """Test detecting conflicts for skill that exists in multiple namespaces."""
        ns = SkillNamespace()
        ns.register("my_skill", namespace="ns1")
        ns.register("my_skill", namespace="ns2")
        ns.register("my_skill", namespace="ns3")
        
        conflicts = ns.check_conflict("my_skill")
        
        assert len(conflicts) == 3
        namespaces = {c.namespace for c in conflicts}
        assert namespaces == {"ns1", "ns2", "ns3"}

    def test_check_conflict_no_conflicts(self):
        """Test detecting no conflicts for unique skill name."""
        ns = SkillNamespace()
        ns.register("unique_skill")
        
        conflicts = ns.check_conflict("unique_skill")
        
        assert len(conflicts) == 1

    def test_check_conflict_nonexistent_returns_empty(self):
        """Test checking conflicts for non-existent skill returns empty."""
        ns = SkillNamespace()
        
        conflicts = ns.check_conflict("nonexistent")
        
        assert conflicts == []


class TestReservedNamespace:
    """Test reserved namespace checking."""

    def test_is_reserved_returns_true_for_reserved(self):
        """Test is_reserved returns True for reserved namespaces."""
        ns = SkillNamespace()
        
        assert ns.is_reserved("system") is True
        assert ns.is_reserved("user") is True
        assert ns.is_reserved("external") is True
        assert ns.is_reserved("default") is True

    def test_is_reserved_returns_false_for_custom(self):
        """Test is_reserved returns False for custom namespaces."""
        ns = SkillNamespace()
        
        assert ns.is_reserved("custom") is False
        assert ns.is_reserved("my-namespace") is False

    def test_is_reserved_case_insensitive(self):
        """Test is_reserved is case insensitive."""
        ns = SkillNamespace()
        
        assert ns.is_reserved("SYSTEM") is True
        assert ns.is_reserved("Default") is True


class TestListNamespaces:
    """Test namespace listing."""

    def test_list_namespaces_empty(self):
        """Test listing namespaces when empty."""
        ns = SkillNamespace()
        namespaces = ns.list_namespaces()
        
        assert namespaces == []

    def test_list_namespaces_returns_all(self):
        """Test listing returns all namespaces."""
        ns = SkillNamespace()
        ns.register("skill1", namespace="ns1")
        ns.register("skill2", namespace="ns2")
        ns.register("skill3", namespace="ns3")
        
        namespaces = ns.list_namespaces()
        
        assert set(namespaces) == {"ns1", "ns2", "ns3"}


class TestListSkills:
    """Test skill listing."""

    def test_list_skills_specific_namespace(self):
        """Test listing skills in specific namespace."""
        ns = SkillNamespace()
        ns.register("skill1", namespace="test")
        ns.register("skill2", namespace="test")
        ns.register("skill3", namespace="other")
        
        skills = ns.list_skills(namespace="test")
        
        assert len(skills) == 2
        skill_names = {s.skill_name for s in skills}
        assert skill_names == {"skill1", "skill2"}

    def test_list_skills_all_namespaces(self):
        """Test listing skills across all namespaces."""
        ns = SkillNamespace()
        ns.register("skill1", namespace="ns1")
        ns.register("skill2", namespace="ns2")
        
        skills = ns.list_skills()
        
        assert len(skills) == 2

    def test_list_skills_empty_namespace(self):
        """Test listing skills in non-existent namespace returns empty."""
        ns = SkillNamespace()
        
        skills = ns.list_skills(namespace="nonexistent")
        
        assert skills == []


class TestGetSkillPath:
    """Test getting skill path."""

    def test_get_skill_path_with_path(self):
        """Test getting path for registered skill with path."""
        ns = SkillNamespace()
        path = Path("/skills/my_skill")
        ns.register("my_skill", skill_path=path)
        
        result = ns.get_skill_path("my_skill")
        
        assert result == path

    def test_get_skill_path_without_path(self):
        """Test getting path for skill registered without path."""
        ns = SkillNamespace()
        ns.register("my_skill")
        
        result = ns.get_skill_path("my_skill")
        
        assert result is None

    def test_get_skill_path_with_namespace(self):
        """Test getting path with specific namespace."""
        ns = SkillNamespace()
        path = Path("/skills/my_skill")
        ns.register("my_skill", namespace="custom", skill_path=path)
        
        result = ns.get_skill_path("my_skill", namespace="custom")
        
        assert result == path


class TestParseQualifiedName:
    """Test parse_qualified_name function."""

    def test_parse_with_namespace(self):
        """Test parsing qualified name with namespace."""
        namespace, name = parse_qualified_name("custom:my_skill")
        
        assert namespace == "custom"
        assert name == "my_skill"

    def test_parse_without_namespace(self):
        """Test parsing name without namespace uses default."""
        namespace, name = parse_qualified_name("my_skill")
        
        assert namespace == DEFAULT_NAMESPACE
        assert name == "my_skill"

    def test_parse_with_hyphen_in_name(self):
        """Test parsing name with hyphens."""
        namespace, name = parse_qualified_name("ns:my-skill-name")
        
        assert namespace == "ns"
        assert name == "my-skill-name"

    def test_parse_with_underscore_in_name(self):
        """Test parsing name with underscores."""
        namespace, name = parse_qualified_name("ns:my_skill_name")
        
        assert namespace == "ns"
        assert name == "my_skill_name"

    def test_parse_invalid_format_uses_default(self):
        """Test parsing invalid format falls back to default namespace."""
        namespace, name = parse_qualified_name("invalid:format:test")
        
        # First colon wins
        assert namespace == "invalid"
        assert name == "format:test"


class TestNamespaceNormalization:
    """Test namespace normalization."""

    def test_normalize_lowercase(self):
        """Test normalization converts to lowercase."""
        ns = SkillNamespace()
        qualified = ns.register("skill", namespace="UPPERCASE")
        
        assert qualified.namespace == "uppercase"

    def test_normalize_trim_whitespace(self):
        """Test normalization trims whitespace."""
        ns = SkillNamespace()
        qualified = ns.register("skill", namespace="  trim  ")
        
        assert qualified.namespace == "trim"


class TestIntegration:
    """Integration tests for namespace operations."""

    def test_full_workflow(self):
        """Test complete registration-resolution-unregistration workflow."""
        ns = SkillNamespace()
        
        # Register skills in multiple namespaces
        ns.register("weather", namespace="builtin", skill_path=Path("/skills/builtin/weather"))
        ns.register("weather", namespace="custom", skill_path=Path("/skills/custom/weather"))
        
        # Check for conflicts
        conflicts = ns.check_conflict("weather")
        assert len(conflicts) == 2
        
        # Resolve with namespace
        skill = ns.resolve("custom:weather")
        assert skill is not None
        assert skill.source == str(Path("/skills/custom/weather"))
        
        # Unregister from one namespace
        ns.unregister("weather", namespace="builtin")
        
        # Still accessible in other namespace
        skill = ns.resolve("custom:weather")
        assert skill is not None
        
        # No conflict anymore
        conflicts = ns.check_conflict("weather")
        assert len(conflicts) == 1

    def test_default_vs_explicit_namespace(self):
        """Test that default namespace is used when no namespace specified."""
        ns = SkillNamespace()
        
        ns.register("skill", namespace="default")
        ns.register("skill", namespace="other")
        
        # Simple name resolves to default
        resolved = ns.resolve("skill")
        assert resolved.namespace == "default"
        
        # Explicit namespace works
        resolved = ns.resolve("other:skill")
        assert resolved.namespace == "other"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])