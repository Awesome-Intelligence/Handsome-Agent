#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Environment loader for Handsome Agent.
"""

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

_CREDENTIAL_SUFFIXES = ("_API_KEY", "_TOKEN", "_SECRET", "_KEY")
_WARNED_KEYS: set = set()


def _sanitize_credentials():
    """Strip non-ASCII characters from credential env vars."""
    for key, value in list(os.environ.items()):
        if not any(key.endswith(suffix) for suffix in _CREDENTIAL_SUFFIXES):
            continue

        try:
            value.encode("ascii")
            continue
        except UnicodeEncodeError:
            pass

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


def _get_handsome_home() -> Path:
    """Get the Handsome Agent home directory."""
    return Path.home() / ".handsome_agent"


def load_env(
    project_env: str | os.PathLike | None = None,
    override: bool = True,
) -> list[Path]:
    """Load environment files with user config taking precedence."""
    loaded: list[Path] = []
    home = _get_handsome_home()
    home.mkdir(parents=True, exist_ok=True)

    user_env = home / ".env"

    if user_env.exists():
        if load_dotenv:
            try:
                load_dotenv(dotenv_path=user_env, override=override, encoding="utf-8")
            except UnicodeDecodeError:
                load_dotenv(dotenv_path=user_env, override=override, encoding="latin-1")
        loaded.append(user_env)

    if project_env:
        project_path = Path(project_env)
        if project_path.exists():
            if load_dotenv:
                try:
                    load_dotenv(dotenv_path=project_path, override=not loaded, encoding="utf-8")
                except UnicodeDecodeError:
                    load_dotenv(dotenv_path=project_path, override=False, encoding="latin-1")
            loaded.append(project_path)

    _sanitize_credentials()

    return loaded


def get_env(key: str, default: str = None) -> str | None:
    """Get an environment variable value."""
    return os.getenv(key, default)


def set_env(key: str, value: str):
    """Set an environment variable value."""
    os.environ[key] = value


def has_api_key(provider: str) -> bool:
    """Check if API key exists for a provider."""
    env_vars = [
        f"{provider.upper()}_API_KEY",
        f"OPENAI_API_KEY" if provider == "openai" else None,
        f"ANTHROPIC_API_KEY" if provider == "anthropic" else None,
    ]

    for var in env_vars:
        if var and os.getenv(var):
            return True

    return False


def get_api_key(provider: str) -> str | None:
    """Get API key for a provider."""
    candidates = [
        f"{provider.upper()}_API_KEY",
        f"{provider.upper()}_KEY",
    ]

    for var in candidates:
        value = os.getenv(var)
        if value:
            return value

    if provider == "openai":
        return os.getenv("OPENAI_API_KEY")
    elif provider == "anthropic":
        return os.getenv("ANTHROPIC_API_KEY")

    return None
