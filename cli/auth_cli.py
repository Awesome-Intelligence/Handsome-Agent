#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auth CLI - Authentication CLI commands.

🚪 Access - 💬 CLI - 认证 CLI

参考 Hermes 的 auth_commands.py 设计，增强版。
"""

import getpass
import os
from typing import Optional

from agent.auth import (
    resolve_api_key,
    save_api_key,
    delete_api_key,
    list_providers,
    get_provider_info,
    list_available_providers,
    validate_api_key,
    register_provider,
    PROVIDER_REGISTRY,
)


def get_auth_dir() -> "Path":
    """Get the authentication directory."""
    from pathlib import Path
    return Path.home() / ".handsome_agent" / "auth"


def get_provider_key_path(provider: str) -> "Path":
    """Get the key file path for a provider."""
    return get_auth_dir() / f"{provider}.key"


def save_credential_file(provider: str, api_key: str):
    """Save an API key to file."""
    key_path = get_provider_key_path(provider)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_text(api_key, encoding='utf-8')
    # Set file permissions (Unix only)
    try:
        os.chmod(key_path, 0o600)  # Owner read/write only
    except Exception:
        pass


def load_credential_file(provider: str) -> Optional[str]:
    """Load API key from file."""
    key_path = get_provider_key_path(provider)
    if key_path.exists():
        return key_path.read_text(encoding='utf-8').strip()
    return None


def remove_credential_file(provider: str):
    """Remove API key file."""
    key_path = get_provider_key_path(provider)
    if key_path.exists():
        key_path.unlink()


def mask_key(key: str) -> str:
    """Mask an API key for display."""
    if len(key) <= 8:
        return key[:2] + "..." + key[-2:]
    return key[:6] + "..." + key[-4:]


def get_env_key_for_provider(provider: str) -> Optional[str]:
    """Get API key from environment variable."""
    config = get_provider_info(provider)
    if config and config.api_key_env_vars:
        for var in config.api_key_env_vars:
            value = os.getenv(var)
            if value:
                return value
    return os.getenv(f"{provider.upper()}_API_KEY")


def prompt_for_credential(provider: str) -> Optional[str]:
    """Prompt user for API key."""
    from cli import ui

    # Try environment variable first
    env_key = get_env_key_for_provider(provider)
    if env_key:
        return env_key

    # Try stored credential
    stored = load_credential_file(provider)
    if stored:
        return stored

    # Try agent.auth store
    resolved, source = resolve_api_key(provider)
    if resolved:
        return resolved

    # Prompt interactively
    ui.print_info(f"Enter API key for {provider}:")
    try:
        api_key = getpass.getpass("> ")
        return api_key.strip() or None
    except EOFError:
        pass
    return None


# =============================================================================
# CLI Commands
# =============================================================================

def auth_list():
    """List all stored credentials."""
    from cli import ui

    providers = list_providers()

    if not providers:
        ui.print_info("No stored credentials")
        print("\nRun 'handsome auth add <provider>' to add a credential.")
        return

    ui.print_header("Stored Credentials")

    for provider_id, info in providers.items():
        name = info.get("name", provider_id)
        source = info.get("source", "")
        has_key = info.get("has_key", False)

        if has_key:
            status = ui.Colors.GREEN + "✓" + ui.Colors.RESET
        else:
            status = ui.Colors.YELLOW + "○" + ui.Colors.RESET

        print(f"  {status} {provider_id}: {name}")
        if source:
            print(f"      Source: {source}")

    # Check env vars too
    print("\n  Environment variables:")
    for provider_id in list_available_providers():
        env_key = os.getenv(f"{provider_id.upper()}_API_KEY")
        if env_key:
            print(f"    {provider_id}: {mask_key(env_key)} (env)")

    # Check agent/auth.py store
    for provider_id in list_providers():
        key, source = resolve_api_key(provider_id)
        if key and source.startswith("env:"):
            print(f"    {provider_id}: {mask_key(key)} ({source})")


def auth_add(provider: str, api_key: str = None, interactive: bool = True):
    """Add a credential.

    Args:
        provider: Provider name
        api_key: API key (optional)
        interactive: Prompt if key not provided
    """
    from cli import ui

    # Validate provider
    if provider not in PROVIDER_REGISTRY:
        ui.print_error(f"Unknown provider: {provider}")
        print(f"Available providers: {', '.join(list_available_providers())}")
        return False

    config = get_provider_info(provider)
    if not config:
        ui.print_error(f"Provider {provider} not configured for API key auth")
        return False

    # Get API key
    if not api_key:
        api_key = prompt_for_credential(provider)

    if not api_key:
        ui.print_error("No API key provided")
        return False

    # Validate key
    from agent.auth import validate_api_key
    is_valid, message = validate_api_key(provider, api_key)

    if not is_valid:
        ui.print_warning(f"Validation failed: {message}")
        response = input("Save anyway? (yes/no): ")
        if response.lower() not in ("yes", "y"):
            return False

    # Save to agent.auth
    from agent.auth import save_api_key as auth_save
    auth_save(provider, api_key)

    # Save to file (backup)
    save_credential_file(provider, api_key)

    ui.print_success(f"Credential saved for {provider}")

    # Also save to env for immediate use
    os.environ[f"{provider.upper()}_API_KEY"] = api_key

    return True


def auth_remove(provider: str):
    """Remove a credential."""
    from cli import ui

    from agent.auth import delete_api_key
    from agent.auth import resolve_api_key

    # Check if exists
    key, _ = resolve_api_key(provider)
    if not key:
        ui.print_error(f"No credential found for {provider}")
        return

    # Remove from all sources
    delete_api_key(provider)
    remove_credential_file(provider)
    ui.print_success(f"Credential removed for {provider}")

    # Remove from env
    env_key = f"{provider.upper()}_API_KEY"
    if env_key in os.environ:
        del os.environ[env_key]


def auth_reset(provider: str = None):
    """Reset authentication.

    Args:
        provider: Provider name (all if None)
    """
    from cli import ui

    if provider:
        auth_remove(provider)
    else:
        # Reset all
        for provider_id in list_providers():
            auth_remove(provider_id)
        ui.print_success("All credentials removed")


def auth_status(provider: str = None) -> dict:
    """Show auth status.

    Args:
        provider: Provider name (all if None

    Returns:
        Status dict
    """
    from agent.auth import resolve_api_key, list_providers

    if provider:
        key, source = resolve_api_key(provider)
        return {"provider": provider, "has_key": bool(key), "source": source}

    return list_providers()


# CLI entry point
def main():
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "list":
            auth_list()

        elif command == "add" and len(sys.argv) > 2:
            key = sys.argv[3] if len(sys.argv) > 3 else None
            auth_add(sys.argv[2], key)

        elif command == "remove" and len(sys.argv) > 2:
            auth_remove(sys.argv[2])

        elif command == "reset":
            provider = sys.argv[2] if len(sys.argv) > 2 else None
            auth_reset(provider)

        elif command == "status":
            provider = sys.argv[2] if len(sys.argv) > 2 else None
            result = auth_status(provider)
            print(result)

        else:
            print("Usage:")
            print("  handsome auth list")
            print("  handsome auth add <provider> [key]")
            print("  handsome auth remove <provider>")
            print("  handsome auth reset [provider]")
            print("  handsome auth status [provider]")


if __name__ == "__main__":
    main()