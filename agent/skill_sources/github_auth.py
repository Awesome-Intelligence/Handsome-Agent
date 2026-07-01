#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub 认证模块

支持多种 GitHub 认证方式，按优先级依次尝试：
1. GITHUB_TOKEN / GH_TOKEN 环境变量（PAT）
2. gh CLI subprocess（自动获取 token）
3. GitHub App JWT + installation token
4. 无认证（60 req/hr 限制）
"""

import logging
import os
import subprocess
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class GitHubAuth:
    """
    GitHub API 认证类。

    按优先级尝试以下认证方式：
    1. GITHUB_TOKEN / GH_TOKEN 环境变量（PAT）
    2. gh CLI subprocess（如果安装）
    3. GitHub App JWT + installation token
    4. 无认证（60 req/hr 限制）
    """

    def __init__(self):
        self._cached_token: Optional[str] = None
        self._cached_method: Optional[str] = None
        self._app_token_expiry: float = 0

    def get_headers(self) -> Dict[str, str]:
        """
        获取 GitHub API 请求头。

        Returns:
            包含认证信息的请求头字典
        """
        token = self._resolve_token()
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"
        return headers

    def is_authenticated(self) -> bool:
        """检查是否已认证（拥有有效 token）"""
        return self._resolve_token() is not None

    def auth_method(self) -> str:
        """
        返回当前使用的认证方式。

        Returns:
            'pat' | 'gh-cli' | 'github-app' | 'anonymous'
        """
        self._resolve_token()
        return self._cached_method or "anonymous"

    def _resolve_token(self) -> Optional[str]:
        """解析并返回 token，优先使用缓存"""
        # 返回缓存的 token（如果仍然有效）
        if self._cached_token:
            # GitHub App token 需要检查过期时间
            if self._cached_method != "github-app" or time.time() < self._app_token_expiry:
                return self._cached_token

        # 1. 环境变量
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            self._cached_token = token
            self._cached_method = "pat"
            return token

        # 2. gh CLI
        token = self._try_gh_cli()
        if token:
            self._cached_token = token
            self._cached_method = "gh-cli"
            return token

        # 3. GitHub App
        token = self._try_github_app()
        if token:
            self._cached_token = token
            self._cached_method = "github-app"
            self._app_token_expiry = time.time() + 3500  # ~58 min (tokens last 1 hour)
            return token

        self._cached_method = "anonymous"
        return None

    def _try_gh_cli(self) -> Optional[str]:
        """尝试从 gh CLI 获取 token"""
        try:
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.debug("gh CLI token lookup failed: %s", e)
        except Exception as e:
            logger.debug("gh CLI token lookup error: %s", e)
        return None

    def _try_github_app(self) -> Optional[str]:
        """尝试 GitHub App JWT 认证"""
        app_id = os.environ.get("GITHUB_APP_ID")
        key_path = os.environ.get("GITHUB_APP_PRIVATE_KEY_PATH")
        installation_id = os.environ.get("GITHUB_APP_INSTALLATION_ID")

        if not all([app_id, key_path, installation_id]):
            return None

        try:
            import jwt  # PyJWT
        except ImportError:
            logger.debug("PyJWT not installed, skipping GitHub App auth")
            return None

        try:
            key_file = os.path.expanduser(key_path)
            if not os.path.exists(key_file):
                return None

            with open(key_file, "r", encoding="utf-8") as f:
                private_key = f.read()

            now = int(time.time())
            payload = {
                "iat": now - 60,
                "exp": now + (10 * 60),
                "iss": app_id,
            }
            encoded_jwt = jwt.encode(payload, private_key, algorithm="RS256")

            # 使用 httpx 获取 installation token
            try:
                import httpx
                resp = httpx.post(
                    f"https://api.github.com/app/installations/{installation_id}/access_tokens",
                    headers={
                        "Authorization": f"Bearer {encoded_jwt}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                    timeout=10,
                )
                if resp.status_code == 201:
                    return resp.json().get("token")
            except Exception as e:
                logger.debug(f"GitHub App auth HTTP request failed: {e}")

        except Exception as e:
            logger.debug(f"GitHub App auth failed: {e}")

        return None

    def clear_cache(self) -> None:
        """清除 token 缓存，强制下次重新认证"""
        self._cached_token = None
        self._cached_method = None
        self._app_token_expiry = 0


# 全局实例
_github_auth_instance: Optional[GitHubAuth] = None


def get_github_auth() -> GitHubAuth:
    """获取全局 GitHubAuth 实例"""
    global _github_auth_instance
    if _github_auth_instance is None:
        _github_auth_instance = GitHubAuth()
    return _github_auth_instance