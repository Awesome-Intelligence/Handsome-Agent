#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHubAuth 单元测试"""

import pytest
import os
from unittest.mock import patch, MagicMock


class TestGitHubAuth:
    """GitHubAuth 测试"""

    def test_get_headers_no_auth(self):
        """测试无认证时返回基本 headers"""
        from agent.skill_sources.github_auth import GitHubAuth

        auth = GitHubAuth()
        headers = auth.get_headers()

        assert "Accept" in headers
        assert headers["Accept"] == "application/vnd.github.v3+json"
        assert "Authorization" not in headers

    def test_auth_method_anonymous(self):
        """测试无认证方法"""
        from agent.skill_sources.github_auth import GitHubAuth

        auth = GitHubAuth()
        method = auth.auth_method()

        assert method == "anonymous"

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-token-123"})
    def test_get_headers_with_pat(self):
        """测试 PAT 环境变量认证"""
        from agent.skill_sources.github_auth import GitHubAuth

        auth = GitHubAuth()
        headers = auth.get_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == "token test-token-123"

    @patch.dict(os.environ, {"GH_TOKEN": "gh-token-456"})
    def test_get_headers_with_gh_token(self):
        """测试 GH_TOKEN 环境变量认证"""
        from agent.skill_sources.github_auth import GitHubAuth

        auth = GitHubAuth()
        headers = auth.get_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == "token gh-token-456"

    @patch.dict(os.environ, {"GITHUB_TOKEN": "pat-token"})
    def test_auth_method_pat(self):
        """测试 PAT 认证方法"""
        from agent.skill_sources.github_auth import GitHubAuth

        auth = GitHubAuth()
        method = auth.auth_method()

        assert method == "pat"

    def test_clear_cache(self):
        """测试清除缓存"""
        from agent.skill_sources.github_auth import GitHubAuth

        auth = GitHubAuth()
        auth._cached_token = "cached-token"
        auth._cached_method = "pat"

        auth.clear_cache()

        assert auth._cached_token is None
        assert auth._cached_method is None

    def test_is_authenticated_without_token(self):
        """测试无 token 时未认证"""
        from agent.skill_sources.github_auth import GitHubAuth

        auth = GitHubAuth()
        assert not auth.is_authenticated()

    @patch.dict(os.environ, {"GITHUB_TOKEN": "valid-token"})
    def test_is_authenticated_with_token(self):
        """测试有 token 时已认证"""
        from agent.skill_sources.github_auth import GitHubAuth

        auth = GitHubAuth()
        assert auth.is_authenticated()


class TestGitHubAuthGhCli:
    """GitHubAuth gh CLI 测试"""

    @patch("subprocess.run")
    def test_gh_cli_success(self, mock_run):
        """测试 gh CLI 获取 token 成功"""
        from agent.skill_sources.github_auth import GitHubAuth

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="gh-token-from-cli\n",
        )

        auth = GitHubAuth()
        headers = auth.get_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == "token gh-token-from-cli"
        assert auth.auth_method() == "gh-cli"

    @patch("subprocess.run")
    def test_gh_cli_not_installed(self, mock_run):
        """测试 gh CLI 未安装"""
        from agent.skill_sources.github_auth import GitHubAuth

        mock_run.side_effect = FileNotFoundError()

        auth = GitHubAuth()
        method = auth.auth_method()

        assert method == "anonymous"


class TestGitHubAuthGitHubApp:
    """GitHubAuth GitHub App 测试"""

    @pytest.mark.skip(reason="GitHub App auth requires full environment setup")
    def test_github_app_success(self):
        """测试 GitHub App 认证成功"""
        # 此测试需要完整的环境变量设置，包括私钥文件
        # 在 CI 环境中跳过
        pass