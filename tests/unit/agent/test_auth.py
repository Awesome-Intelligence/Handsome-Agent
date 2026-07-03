#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Auth module.

Tests cover:
- ProviderCredentials dataclass
- AuthStore class
- Credentials management functions
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from agent.auth import (
    ProviderCredentials,
    AuthStore,
    get_auth_path,
    list_credentials,
    get_credentials,
    save_credentials,
    delete_credentials,
)


class TestProviderCredentials:
    """Tests for ProviderCredentials dataclass."""

    def test_provider_credentials_has_name(self):
        """ProviderCredentials has provider name attribute."""
        cred = ProviderCredentials(provider="github", api_key="test_key")
        assert cred.provider == "github"
        assert cred.api_key == "test_key"


class TestAuthStore:
    """Tests for AuthStore class."""

    def test_auth_store_init(self):
        """AuthStore initializes with empty credentials dict."""
        store = AuthStore()
        assert store.credentials == {}


class TestGetAuthPath:
    """Tests for get_auth_path() function."""

    def test_get_auth_path_returns_path(self):
        """get_auth_path() returns a Path object."""
        result = get_auth_path()
        assert isinstance(result, Path)


class TestListCredentials:
    """Tests for list_credentials() function."""

    def test_list_credentials_returns_list(self):
        """list_credentials() returns a list."""
        result = list_credentials()
        assert isinstance(result, list)


class TestGetCredentials:
    """Tests for get_credentials() function."""

    def test_get_credentials_returns_none_for_unknown(self):
        """get_credentials() returns None for unknown provider."""
        result = get_credentials("nonexistent_provider_12345")
        assert result is None


class TestSaveCredentials:
    """Tests for save_credentials() function."""

    def test_save_credentials_accepts_params(self):
        """save_credentials() accepts provider and api_key."""
        # Should not raise
        save_credentials(provider="test_provider", api_key="test_key")


class TestDeleteCredentials:
    """Tests for delete_credentials() function."""

    def test_delete_credentials_accepts_provider(self):
        """delete_credentials() accepts provider name."""
        # Should not raise even if provider doesn't exist
        delete_credentials("nonexistent_provider_12345")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
