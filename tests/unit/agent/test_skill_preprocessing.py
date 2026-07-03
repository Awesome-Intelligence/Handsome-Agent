#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Skill Preprocessing module.

Tests cover:
- Template variable substitution patterns
- Inline shell execution patterns
- ShellResult dataclass
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

from agent.skill_preprocessing import (
    BUILTIN_VAR_PATTERN,
    ENV_VAR_PATTERN,
    CONFIG_VAR_PATTERN,
    INLINE_SHELL_PATTERN,
    ShellResult,
    substitute_template_vars,
    preprocess_skill_content,
)


class TestPatterns:
    """Tests for regex patterns."""

    def test_builtin_var_pattern_matches_double_braces(self):
        """BUILTIN_VAR_PATTERN matches {{VAR}} format."""
        assert BUILTIN_VAR_PATTERN.search("{{SKILL_DIR}}") is not None
        assert BUILTIN_VAR_PATTERN.search("{{CWD}}") is not None
        assert BUILTIN_VAR_PATTERN.search("{{USER}}") is not None

    def test_env_var_pattern_matches_dollar_brace(self):
        """ENV_VAR_PATTERN matches ${VAR_NAME} format."""
        assert ENV_VAR_PATTERN.search("${HOME}") is not None
        assert ENV_VAR_PATTERN.search("${PATH}") is not None
        assert ENV_VAR_PATTERN.search("${MY_VAR}") is not None

    def test_config_var_pattern_matches_config_brace(self):
        """CONFIG_VAR_PATTERN matches ${config:key.path} format."""
        assert CONFIG_VAR_PATTERN.search("${config:skills.dir}") is not None

    def test_inline_shell_pattern_matches_backtick(self):
        """INLINE_SHELL_PATTERN matches `!command` format."""
        assert INLINE_SHELL_PATTERN.search("`!echo hello`") is not None


class TestShellResult:
    """Tests for ShellResult dataclass."""

    def test_shell_result_has_required_fields(self):
        """ShellResult has success, stdout, stderr, returncode, execution_time fields."""
        result = ShellResult(success=True, stdout="hello", stderr="", returncode=0, execution_time=0.1)
        assert hasattr(result, 'success')
        assert hasattr(result, 'stdout')
        assert hasattr(result, 'stderr')
        assert hasattr(result, 'returncode')
        assert hasattr(result, 'execution_time')

    def test_shell_result_success(self):
        """ShellResult with success=True has correct values."""
        result = ShellResult(success=True, stdout="hello", stderr="", returncode=0, execution_time=0.1)
        assert result.success is True
        assert result.stdout == "hello"
        assert result.stderr == ""
        assert result.returncode == 0

    def test_shell_result_failure(self):
        """ShellResult with success=False has correct values."""
        result = ShellResult(success=False, stdout="", stderr="command not found", returncode=1, execution_time=0.05)
        assert result.success is False
        assert result.stderr == "command not found"
        assert result.returncode == 1


class TestSubstituteTemplateVars:
    """Tests for substitute_template_vars()."""

    def test_substitutes_skill_dir(self):
        """Substitutes {{SKILL_DIR}} with skill directory."""
        skill_dir = Path("/path/to/skills")
        result = substitute_template_vars("Skill dir: {{SKILL_DIR}}", skill_dir=skill_dir)
        assert str(skill_dir) in result

    def test_substitutes_cwd(self):
        """Substitutes {{CWD}} with current working directory."""
        result = substitute_template_vars("CWD: {{CWD}}")
        assert "{{CWD}}" not in result

    def test_substitutes_home(self):
        """Substitutes {{HOME}} with home directory."""
        result = substitute_template_vars("Home: {{HOME}}")
        assert "{{HOME}}" not in result

    def test_substitutes_user(self):
        """Substitutes {{USER}} with current user."""
        result = substitute_template_vars("User: {{USER}}")
        assert "{{USER}}" not in result

    def test_substitutes_date(self):
        """Substitutes {{DATE}} with current date."""
        result = substitute_template_vars("Date: {{DATE}}")
        assert "{{DATE}}" not in result

    def test_leaves_unknown_builtin_unchanged(self):
        """Unknown builtin variables are left unchanged."""
        result = substitute_template_vars("Unknown: {{UNKNOWN_VAR}}")
        assert "{{UNKNOWN_VAR}}" in result

    def test_empty_template(self):
        """Empty template returns empty string."""
        result = substitute_template_vars("")
        assert result == ""

    def test_mixed_builtin_and_env_vars(self):
        """Handles both builtin and env vars in one template."""
        with patch.dict(os.environ, {"MYENV": "env_value"}):
            result = substitute_template_vars("{{CWD}} and ${MYENV}")
            assert "{{CWD}}" not in result
            assert "env_value" in result


class TestPreprocessSkillContent:
    """Tests for preprocess_skill_content()."""

    def test_preprocess_returns_tuple(self):
        """preprocess_skill_content() returns a tuple of (content, errors)."""
        result = preprocess_skill_content("test content", Path("/tmp"))
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], list)

    def test_preprocess_with_no_variables(self):
        """preprocess_skill_content() returns content unchanged when no vars."""
        content = "This is plain text with no variables."
        result = preprocess_skill_content(content, Path("/tmp"))
        assert result[0] == content

    def test_preprocess_handles_builtin_vars(self):
        """preprocess_skill_content() substitutes builtin variables."""
        content = "Skill at {{SKILL_DIR}}"
        result = preprocess_skill_content(content, Path("/my/skills"))
        assert "{{SKILL_DIR}}" not in result[0]
        # Path may be normalized (forward/back slashes)
        assert "my" in result[0] and "skills" in result[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
