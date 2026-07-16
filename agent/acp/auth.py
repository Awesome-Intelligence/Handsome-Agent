#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACP Authentication Module.

Provides authentication methods for ACP protocol.
"""

# 🧠 Decision - 💾 Memory - ACP Authentication

import logging
from typing import Any, Dict, List, Optional

from common.logging_manager import get_decision_logger

logger = get_decision_logger(__name__)

# Auth method IDs
TERMINAL_SETUP_AUTH_METHOD_ID = "agentz-setup"


def detect_provider() -> Optional[str]:
    """Detect the active runtime provider.

    Returns the provider name (e.g., 'openai', 'anthropic', 'azure')
    if credentials are available, or None if not configured.
    """
    try:
        # Try to import the provider resolver
        from agent.llm.factory import get_default_provider

        provider = get_default_provider()
        if provider:
            return provider.lower()
    except Exception as e:
        logger.debug(f"Could not detect provider: {e}")

    # Fallback: check environment variables
    if _has_openai_key():
        return "openai"
    if _has_anthropic_key():
        return "anthropic"
    if _has_azure_key():
        return "azure"

    return None


def _has_openai_key() -> bool:
    """Check if OpenAI API key is available."""
    import os
    key = os.environ.get("OPENAI_API_KEY", "")
    return bool(key and key.strip())


def _has_anthropic_key() -> bool:
    """Check if Anthropic API key is available."""
    import os
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    return bool(key and key.strip())


def _has_azure_key() -> bool:
    """Check if Azure API key is available."""
    import os
    key = os.environ.get("AZURE_API_KEY", "")
    return bool(key and key.strip())


def has_provider() -> bool:
    """Return True if any runtime provider credentials are available."""
    return detect_provider() is not None


def build_auth_methods() -> List[Dict[str, Any]]:
    """Build ACP-compatible auth methods.

    Returns a list of auth method definitions compatible with the ACP protocol.
    Always includes a terminal setup method for first-time configuration.
    """
    methods = []

    provider = detect_provider()
    if provider:
        methods.append({
            "id": provider,
            "type": "agent",
            "name": f"{provider.title()} Runtime Credentials",
            "description": f"Authenticate using {provider} credentials configured in environment.",
        })

    # Always include terminal setup for first-time users
    methods.append({
        "id": TERMINAL_SETUP_AUTH_METHOD_ID,
        "type": "terminal",
        "name": "Configure Agent-Z",
        "description": "Open interactive setup to configure model/provider. Use when not yet configured.",
        "args": ["--setup"],
    })

    return methods


def validate_api_key(api_key: str, provider: Optional[str] = None) -> bool:
    """Validate an API key.

    Args:
        api_key: The API key to validate
        provider: Optional provider hint for validation

    Returns:
        True if the key appears valid
    """
    if not api_key or not api_key.strip():
        return False

    # Basic length check
    if len(api_key) < 10:
        return False

    # Provider-specific validation
    if provider == "openai" and not api_key.startswith(("sk-", "op-")):
        return False
    if provider == "anthropic" and not api_key.startswith("sk-ant-"):
        return False

    return True


def get_auth_config() -> Dict[str, Any]:
    """Get the current authentication configuration."""
    provider = detect_provider()

    return {
        "has_credentials": provider is not None,
        "provider": provider,
        "auth_methods": build_auth_methods(),
    }
