#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication system for Handsome Agent.

🧠 Decision - 🤖 LLM - 认证管理

支持多 Provider 的 API Key 管理：
- OpenAI
- Anthropic
- DeepSeek
- Ollama
- 自定义 Provider

认证状态保存在 ~/.handsome_agent/auth.json
"""

import json
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# 文件锁（跨进程同步）
_AUTH_LOCK = threading.RLock()

# Auth store 版本
AUTH_STORE_VERSION = 1


@dataclass
class ProviderCredentials:
    """Provider credentials holder."""
    provider: str
    api_key: str
    base_url: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthStore:
    """Auth store holder."""
    version: int = AUTH_STORE_VERSION
    credentials: Dict[str, ProviderCredentials] = field(default_factory=dict)


def get_auth_path() -> Path:
    """Get auth store file path."""
    auth_dir = Path.home() / ".handsome_agent"
    auth_dir.mkdir(parents=True, exist_ok=True)
    return auth_dir / "auth.json"


def _load_auth_store() -> AuthStore:
    """Load auth store from file."""
    auth_path = get_auth_path()
    if auth_path.exists():
        try:
            with open(auth_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                creds = {}
                for provider, cred_data in data.get("credentials", {}).items():
                    creds[provider] = ProviderCredentials(**cred_data)
                return AuthStore(
                    version=data.get("version", AUTH_STORE_VERSION),
                    credentials=creds,
                )
        except Exception as e:
            logger.warning(f"Failed to load auth store: {e}")
    return AuthStore()


def _save_auth_store(store: AuthStore):
    """Save auth store to file."""
    auth_path = get_auth_path()
    with _AUTH_LOCK:
        with open(auth_path, 'w', encoding='utf-8') as f:
            data = {
                "version": store.version,
                "credentials": {
                    name: {
                        "provider": cred.provider,
                        "api_key": cred.api_key,
                        "base_url": cred.base_url,
                        "refresh_token": cred.refresh_token,
                        "expires_at": cred.expires_at,
                        "metadata": cred.metadata,
                    }
                    for name, cred in store.credentials.items()
                },
            }
            json.dump(data, f, indent=2, ensure_ascii=False)
        # 设置文件权限 (Unix)
        try:
            os.chmod(auth_path, 0o600)
        except Exception:
            pass


def list_credentials() -> List[ProviderCredentials]:
    """List all stored credentials."""
    store = _load_auth_store()
    return list(store.credentials.values())


def get_credentials(provider: str) -> Optional[ProviderCredentials]:
    """Get credentials for a provider."""
    store = _load_auth_store()
    return store.credentials.get(provider.lower())


def save_credentials(
    provider: str,
    api_key: str,
    base_url: Optional[str] = None,
    refresh_token: Optional[str] = None,
    expires_at: Optional[datetime] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """Save credentials for a provider."""
    store = _load_auth_store()
    store.credentials[provider.lower()] = ProviderCredentials(
        provider=provider.lower(),
        api_key=api_key,
        base_url=base_url,
        refresh_token=refresh_token,
        expires_at=expires_at.isoformat() if expires_at else None,
        metadata=metadata or {},
    )
    _save_auth_store(store)


def delete_credentials(provider: str):
    """Delete credentials for a provider."""
    store = _load_auth_store()
    provider_key = provider.lower()
    if provider_key in store.credentials:
        del store.credentials[provider_key]
        _save_auth_store(store)


def clear_all_credentials():
    """Clear all stored credentials."""
    _save_auth_store(AuthStore())


# =============================================================================
# Provider Registry
# =============================================================================

# Known providers
PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "env_var": "OPENAI_API_KEY",
        "default_url": "https://api.openai.com/v1",
    },
    "anthropic": {
        "name": "Anthropic",
        "env_var": "ANTHROPIC_API_KEY",
        "default_url": "https://api.anthropic.com",
    },
    "deepseek": {
        "name": "DeepSeek",
        "env_var": "DEEPSEEK_API_KEY",
        "default_url": "https://api.deepseek.com/v1",
    },
    "ollama": {
        "name": "Ollama",
        "env_var": "",
        "default_url": "http://localhost:11434",
    },
    "groq": {
        "name": "Groq",
        "env_var": "GROQ_API_KEY",
        "default_url": "https://api.groq.com",
    },
    "gemini": {
        "name": "Google Gemini",
        "env_var": "GOOGLE_API_KEY",
        "default_url": "https://generativelanguage.googleapis.com",
    },
    "mistral": {
        "name": "Mistral AI",
        "env_var": "MISTRAL_API_KEY",
        "default_url": "https://api.mistral.ai",
    },
    "openrouter": {
        "name": "OpenRouter",
        "env_var": "OPENROUTER_API_KEY",
        "default_url": "https://openrouter.ai/api",
    },
    "azure": {
        "name": "Azure OpenAI",
        "env_var": "AZURE_OPENAI_KEY",
        "default_url": None,
    },
    "custom": {
        "name": "Custom Provider",
        "env_var": "",
        "default_url": None,
    },
}


def get_provider_info(name: str) -> Optional[Dict]:
    """Get provider info."""
    return PROVIDERS.get(name.lower())


def list_providers() -> List[Dict]:
    """List all registered providers."""
    return list(PROVIDERS.values())


# =============================================================================
# API Key Validation
# =============================================================================

def validate_api_key_sync(provider: str, api_key: str, base_url: Optional[str] = None) -> Tuple[bool, str]:
    """Validate API key synchronously.

    Args:
        provider: Provider name
        api_key: API key to validate
        base_url: Optional base URL override

    Returns:
        Tuple of (is_valid, message)
    """
    import httpx

    provider_info = get_provider_info(provider)
    if not provider_info:
        return False, f"Unknown provider: {provider}"

    base_url = base_url or provider_info.get("default_url")
    if not base_url:
        return False, f"No default URL for {provider}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = httpx.get(f"{base_url}/models", headers=headers, timeout=10.0)
        if resp.status_code == 200:
            return True, "Valid"
        elif resp.status_code == 401:
            return False, "Invalid API key"
        else:
            return False, f"Error: {resp.status_code}"
    except httpx.ConnectError:
        return False, "Connection error"
    except Exception as e:
        return False, str(e)


# =============================================================================
# CLI Commands
# =============================================================================

def auth_list():
    """List stored credentials."""
    from cli import ui

    credentials = list_credentials()

    if not credentials:
        ui.print_info("No stored credentials")
        print("\nRun 'handsome auth add <provider>' to add credentials.")
        return

    ui.print_header("Stored Credentials")
    for cred in credentials:
        masked_key = cred.api_key[:8] + "..." if len(cred.api_key) > 8 else "***"
        print(f"\n  {cred.provider}: {masked_key}")
        if cred.base_url:
            print(f"    URL: {cred.base_url}")
        if cred.metadata.get("added_at"):
            print(f"    Added: {cred.metadata.get('added_at')}")


def auth_add(provider: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
    """Add credentials for a provider."""
    from cli import ui

    # Get provider info
    provider_info = get_provider_info(provider)
    if not provider_info:
        ui.print_error(f"Unknown provider: {provider}")
        print(f"Available: {', '.join(PROVIDERS.keys())}")
        return

    # Prompt for API key if not provided
    if not api_key:
        import getpass
        prompt = f"Enter API key for {provider}: "
        api_key = getpass.getpass(prompt)

    if not api_key:
        ui.print_error("API key is required")
        return

    # Validate key
    is_valid, msg = validate_api_key_sync(provider, api_key, base_url)
    if not is_valid:
        ui.print_warning(f"API key validation: {msg}")
        ui.print_info("Saving anyway...")

    # Save credentials
    save_credentials(
        provider,
        api_key,
        base_url=base_url,
        metadata={"added_at": datetime.now().isoformat()},
    )

    ui.print_success(f"Credentials saved for {provider}")


def auth_remove(provider: str):
    """Remove credentials for a provider."""
    from cli import ui

    delete_credentials(provider)
    ui.print_success(f"Credentials removed for {provider}")


def auth_reset(provider: Optional[str] = None):
    """Reset credentials."""
    from cli import ui

    if provider:
        delete_credentials(provider)
        ui.print_success(f"Credentials reset for {provider}")
    else:
        clear_all_credentials()
        ui.print_success("All credentials reset")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "list":
            auth_list()

        elif command == "add" and len(sys.argv) > 2:
            provider = sys.argv[2]
            key = sys.argv[3] if len(sys.argv) > 3 else None
            url = None
            for arg in sys.argv[4:]:
                if arg.startswith("--url="):
                    url = arg[6:]
            auth_add(provider, key, url)

        elif command == "remove" and len(sys.argv) > 2:
            auth_remove(sys.argv[2])

        elif command == "reset":
            provider = sys.argv[2] if len(sys.argv) > 2 else None
            auth_reset(provider)

        else:
            print("Usage:")
            print("  python agent.auth list")
            print("  python agent.auth add <provider> [key]")
            print("  python agent.auth remove <provider>")
            print("  python agent.auth reset [provider]")
    else:
        auth_list()