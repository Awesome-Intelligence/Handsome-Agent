#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Constants Module - Inspired by Hermes Agent's hermes_constants.py

Defines constants, paths, and profile-aware configuration.
"""

import os
from pathlib import Path


# Agent information
AGENT_NAME = "Handsome Agent"
AGENT_VERSION = "1.0.0"
AGENT_AUTHOR = "Handsome Agent Team"

# Environment variables
ENV_HERMES_HOME = "HERMES_HOME"
ENV_HERMES_PROFILE = "HERMES_PROFILE"

# Default paths
def get_default_hermes_home() -> Path:
    """Get the default HERMES_HOME directory."""
    home = os.environ.get('HOME') or os.environ.get('USERPROFILE')
    if home:
        return Path(home) / ".hermes"
    return Path(".") / ".hermes"

HERMES_HOME = Path(os.environ.get(ENV_HERMES_HOME, get_default_hermes_home()))

# Subdirectories
CONFIG_DIR = HERMES_HOME / "config"
SESSIONS_DIR = HERMES_HOME / "sessions"
MEMORIES_DIR = HERMES_HOME / "memories"
TRAJECTORIES_DIR = HERMES_HOME / "trajectories"
LOGS_DIR = HERMES_HOME / "logs"
PLUGINS_DIR = HERMES_HOME / "plugins"

# Configuration files
CONFIG_FILE = CONFIG_DIR / "config.json"
SECRETS_FILE = CONFIG_DIR / "secrets.json"
PROFILE_DIR = CONFIG_DIR / "profiles"

# Database
STATE_DB_FILE = HERMES_HOME / "hermes_state.db"

# Default configuration values
DEFAULT_MAX_CONTEXT_TOKENS = 8192
DEFAULT_MAX_HISTORY_LENGTH = 50
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_CACHE_SIZE = 100

# Profile-related
DEFAULT_PROFILE_NAME = "default"

# Ensure directories exist
def ensure_directories():
    """Ensure all required directories exist."""
    for dir_path in [
        HERMES_HOME,
        CONFIG_DIR,
        SESSIONS_DIR,
        MEMORIES_DIR,
        TRAJECTORIES_DIR,
        LOGS_DIR,
        PLUGINS_DIR,
        PROFILE_DIR
    ]:
        dir_path.mkdir(parents=True, exist_ok=True)


# Tool categories
TOOL_CATEGORIES = [
    "files",
    "terminal",
    "web",
    "code",
    "system",
    "ai",
    "memory",
    "utilities"
]

# Platforms
PLATFORMS = ["linux", "windows", "macos"]


# Version check
def get_version() -> str:
    """Get the agent version."""
    return AGENT_VERSION


def get_agent_info() -> dict:
    """Get agent information as a dictionary."""
    return {
        "name": AGENT_NAME,
        "version": AGENT_VERSION,
        "author": AGENT_AUTHOR,
        "hermes_home": str(HERMES_HOME)
    }
