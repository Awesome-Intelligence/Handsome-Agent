#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""审计日志单元测试"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch


class TestAuditLog:
    """审计日志测试"""

    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """创建临时配置目录"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        return config_dir

    def test_append_audit_log(self, temp_config_dir):
        """测试追加审计日志"""
        with patch("common.config.get_config_dir", return_value=temp_config_dir):
            from agent.skill_sources.audit_log import append_audit_log, get_audit_log_path

            append_audit_log("INSTALL", "test-skill", "github", "trusted", "clean", "sha256:abc123")

            log_path = get_audit_log_path()
            assert log_path.exists()

            content = log_path.read_text(encoding="utf-8")
            assert "INSTALL" in content
            assert "test-skill" in content
            assert "github:trusted" in content

    def test_read_audit_log(self, temp_config_dir):
        """测试读取审计日志"""
        with patch("common.config.get_config_dir", return_value=temp_config_dir):
            from agent.skill_sources.audit_log import append_audit_log, read_audit_log

            append_audit_log("INSTALL", "skill-1", "github", "trusted", "clean")
            append_audit_log("INSTALL", "skill-2", "index", "builtin", "clean")
            append_audit_log("UNINSTALL", "skill-1", "github", "trusted", "n/a")

            entries = read_audit_log(limit=10)

            assert len(entries) == 3
            # 最新条目在前
            assert entries[0]["skill_name"] == "skill-1"
            assert entries[0]["action"] == "UNINSTALL"

    def test_read_audit_log_limit(self, temp_config_dir):
        """测试读取限制"""
        with patch("common.config.get_config_dir", return_value=temp_config_dir):
            from agent.skill_sources.audit_log import append_audit_log, read_audit_log

            for i in range(10):
                append_audit_log("INSTALL", f"skill-{i}", "github", "trusted", "clean")

            entries = read_audit_log(limit=3)

            assert len(entries) == 3

    def test_read_audit_log_empty(self, temp_config_dir):
        """测试读取空日志"""
        with patch("common.config.get_config_dir", return_value=temp_config_dir):
            from agent.skill_sources.audit_log import read_audit_log

            entries = read_audit_log()

            assert entries == []

    def test_clear_audit_log(self, temp_config_dir):
        """测试清空审计日志"""
        with patch("common.config.get_config_dir", return_value=temp_config_dir):
            from agent.skill_sources.audit_log import append_audit_log, read_audit_log, clear_audit_log

            append_audit_log("INSTALL", "test-skill", "github", "trusted", "clean")

            result = clear_audit_log()

            assert result is True
            assert read_audit_log() == []

    def test_ensure_audit_log_dir(self, temp_config_dir):
        """测试确保目录存在"""
        with patch("common.config.get_config_dir", return_value=temp_config_dir):
            from agent.skill_sources.audit_log import ensure_audit_log_dir, get_audit_log_path

            ensure_audit_log_dir()

            log_path = get_audit_log_path()
            assert log_path.parent.exists()