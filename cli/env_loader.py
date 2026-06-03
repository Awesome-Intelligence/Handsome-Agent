#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Environment loader for Handsome Agent.

Loads .env files with the following precedence:
1. ~/.handsome_agent/.env (user config, highest priority)
2. Project .env (development fallback)

🚪 Access - 💬 CLI - 环境变量加载

Features:
- .env file loading with python-dotenv
- Credential sanitization (non-ASCII stripping)
- .env file repair (missing newlines)
"""

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# Credential suffixes
_CREDENTIAL_SUFFIXES = ("_API_KEY", "_TOKEN", "_SECRET", "_KEY")

# Env var names we've warned about during this process
_WARNED_KEYS: set = set()


def _sanitize_credentials():
    """Strip non-ASCII characters from credential env vars in os.environ.

    API keys must be pure ASCII since they're sent as HTTP header values.
    Non-ASCII chars typically come from copy-pasting from PDFs or rich-text editors.
    """
    for key, value in list(os.environ.items()):
        if not any(key.endswith(suffix) for suffix in _CREDENTIAL_SUFFIXES):
            continue

        try:
            value.encode("ascii")
            continue
        except UnicodeEncodeError:
            pass

        # Strip non-ASCII
        cleaned = value.encode("ascii", errors="ignore").decode("ascii")
        os.environ[key] = cleaned

        if key in _WARNED_KEYS:
            continue
        _WARNED_KEYS.add(key)

        stripped = len(value) - len(cleaned)
        if stripped > 0:
            print(
                f"  Warning: {key} contained {stripped} non-ASCII character(s) — stripped",
                file=sys.stderr,
            )
            print(
                "  This usually means the key was copy-pasted from a PDF or rich-text editor.",
                file=sys.stderr,
            )


def _get_handsome_home() -> Path:
    """Get the Handsome Agent home directory."""
    return Path.home() / ".handsome_agent"


def load_env(
    project_env: str | os.PathLike | None = None,
    override: bool = True,
) -> list[Path]:
    """Load environment files with user config taking precedence.

    Args:
        project_env: Project .env file path (optional)
        override: Whether to override existing environment variables

    Returns:
        List of loaded .env file paths
    """
    loaded: list[Path] = []
    home = _get_handsome_home()
    home.mkdir(parents=True, exist_ok=True)

    user_env = home / ".env"

    # Load user .env
    if user_env.exists():
        if load_dotenv:
            try:
                load_dotenv(dotenv_path=user_env, override=override, encoding="utf-8")
            except UnicodeDecodeError:
                load_dotenv(dotenv_path=user_env, override=override, encoding="latin-1")
        loaded.append(user_env)

    # Load project .env (only if it exists and user env doesn't)
    if project_env:
        project_path = Path(project_env)
        if project_path.exists():
            if load_dotenv:
                try:
                    load_dotenv(dotenv_path=project_path, override=not loaded, encoding="utf-8")
                except UnicodeDecodeError:
                    load_dotenv(dotenv_path=project_path, override=False, encoding="latin-1")
            loaded.append(project_path)

    # Sanitize credentials after loading
    _sanitize_credentials()

    return loaded


def get_env(key: str, default: str = None) -> str | None:
    """Get an environment variable value.

    Args:
        key: Environment variable name
        default: Default value if not found

    Returns:
        Environment variable value or default
    """
    return os.getenv(key, default)


def set_env(key: str, value: str):
    """Set an environment variable value.

    Args:
        key: Environment variable name
        value: Value to set
    """
    os.environ[key] = value


def has_api_key(provider: str) -> bool:
    """Check if API key exists for a provider.

    Args:
        provider: Provider name (e.g., 'openai', 'anthropic')

    Returns:
        True if API key is set
    """
    # Common API key env vars
    env_vars = [
        f"{provider.upper()}_API_KEY",
        f"OPENAI_API_KEY" if provider == "openai" else None,
        f"ANTHROPIC_API_KEY" if provider == "anthropic" else None,
        f"DEEPSEEK_API_KEY" if provider == "deepseek" else None,
    ]

    for var in env_vars:
        if var and os.getenv(var):
            return True

    return False


def get_api_key(provider: str) -> str | None:
    """Get API key for a provider.

    Args:
        provider: Provider name

    Returns:
        API key or None
    """
    # Try common env var names
    candidates = [
        f"{provider.upper()}_API_KEY",
        f"{provider.upper()}_KEY",
    ]

    for var in candidates:
        value = os.getenv(var)
        if value:
            return value

    # Provider-specific mappings
    if provider == "openai":
        return os.getenv("OPENAI_API_KEY")
    elif provider == "anthropic":
        return os.getenv("ANTHROPIC_API_KEY")
    elif provider == "deepseek":
        return os.getenv("DEEPSEEK_API_KEY")

    return None


if __name__ == "__main__":
    # Test
    print("Loading environment...")
    loaded = load_env()
    print(f"Loaded: {loaded}")

    print(f"\nOPENAI_API_KEY: {get_api_key('openai')}")