#!/usr/bin/env python3
"""Copy and patch hermes base.py to Agent-Z."""

import re

src = r'E:\hermes-agent-study\gateway\platforms\base.py'
dst = r'E:\Awesome Intelligence\Agent-Z\gateway\platforms\base.py'

with open(src, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove the 'from utils import normalize_proxy_url' line
content = content.replace('from utils import normalize_proxy_url\n', '')

# 2. Insert normalize_proxy_url function after _PROXY_ENV_KEYS definition
normalize_fn = '''

def normalize_proxy_url(proxy_url: str | None) -> str | None:
    """Normalize proxy URLs for httpx/aiohttp compatibility.

    WSL/Clash-style environments often export SOCKS proxies as
    ``socks://127.0.0.1:PORT``. httpx rejects that alias and expects the
    explicit ``socks5://`` scheme instead.
    """
    candidate = str(proxy_url or "").strip()
    if not candidate:
        return None
    if candidate.lower().startswith("socks://"):
        return f"socks5://{candidate[len('socks://'):]}"
    return candidate

'''

# Insert after _PROXY_ENV_KEYS definition
proxy_env_pos = content.find('_PROXY_ENV_KEYS = (')
if proxy_env_pos != -1:
    end = content.find(')', proxy_env_pos) + 2
    content = content[:end] + normalize_fn + content[end:]

# 3. Fix hermes_constants imports - replace with stubs
old_hermes = "from hermes_constants import get_default_hermes_root, get_hermes_dir, get_hermes_home"
new_hermes = """try:
    from hermes_constants import get_default_hermes_root, get_hermes_dir, get_hermes_home
except ImportError:
    def _hermes_home_fallback():
        from pathlib import Path
        return Path.home() / ".hermes"
    def _hermes_root_fallback():
        from pathlib import Path
        return Path.home() / ".hermes"
    def get_hermes_home():
        return _hermes_home_fallback()
    def get_default_hermes_root():
        return _hermes_root_fallback()
    def get_hermes_dir(subpath, old_name=None):
        return get_hermes_home() / subpath"""
content = content.replace(old_hermes, new_hermes)

# 4. Fix hermes_cli.config import
old_cfg = "from hermes_cli.config import load_config as _load_config"
new_cfg = """try:
    from hermes_cli.config import load_config as _load_config
except ImportError:
    def _load_config():
        return {}"""
content = content.replace(old_cfg, new_cfg)

# 5. Fix hermes_cli.commands import
old_cmds = "from hermes_cli.commands import should_bypass_active_session"
new_cmds = """try:
    from hermes_cli.commands import should_bypass_active_session
except ImportError:
    def should_bypass_active_session(cmd):
        return cmd in {"stop", "new", "reset", "approve", "deny", "status", "background", "restart"}"""
content = content.replace(old_cmds, new_cmds)

# 6. Fix tools.url_safety imports in _ssrf_redirect_guard and cache functions
old_url_safety = "from tools.url_safety import is_safe_url, redirect_target_from_response"
new_url_safety = """try:
    from tools.url_safety import is_safe_url, redirect_target_from_response
except ImportError:
    is_safe_url = None
    redirect_target_from_response = None"""
content = content.replace(old_url_safety, new_url_safety)

# 7. Fix tools.clarify_gateway import
old_clarify = "from tools.clarify_gateway import mark_awaiting_text"
new_clarify = """try:
    from tools.clarify_gateway import mark_awaiting_text
except ImportError:
    def mark_awaiting_text(clarify_id):
        pass"""
content = content.replace(old_clarify, new_clarify)

# 8. Fix tools.tts_tool imports
old_tts = "from tools.tts_tool import text_to_speech_tool, check_tts_requirements"
new_tts = """try:
    from tools.tts_tool import text_to_speech_tool, check_tts_requirements
except ImportError:
    text_to_speech_tool = None
    check_tts_requirements = None"""
content = content.replace(old_tts, new_tts)

# 9. Fix tools.credential_files import
old_cred = "from tools.credential_files import to_agent_visible_cache_path"
new_cred = """try:
    from tools.credential_files import to_agent_visible_cache_path
except ImportError:
    def to_agent_visible_cache_path(path):
        return path"""
content = content.replace(old_cred, new_cred)

# 10. Fix gateway.status imports (write_runtime_status, acquire_scoped_lock, release_scoped_lock)
old_status = "from gateway.status import write_runtime_status"
new_status = """try:
    from gateway.status import write_runtime_status
except ImportError:
    def write_runtime_status(**kwargs):
        pass"""
content = content.replace(old_status, new_status)

old_lock = "from gateway.status import acquire_scoped_lock"
new_lock = """try:
    from gateway.status import acquire_scoped_lock
except ImportError:
    def acquire_scoped_lock(scope, identity, metadata=None):
        return True, None"""
content = content.replace(old_lock, new_lock)

old_rel_lock = "from gateway.status import release_scoped_lock"
new_rel_lock = """try:
    from gateway.status import release_scoped_lock
except ImportError:
    def release_scoped_lock(scope, identity):
        pass"""
content = content.replace(old_rel_lock, new_rel_lock)

# 11. Fix gateway.stream_events imports (MessageChunk, MessageStop, ToolCallChunk, Commentary)
old_stream = "from gateway.stream_events import MessageChunk, MessageStop, Commentary"
new_stream = """try:
    from gateway.stream_events import MessageChunk, MessageStop, Commentary
except ImportError:
    @dataclass
    class MessageChunk:
        text: str = ""
    @dataclass
    class MessageStop:
        final: bool = False
    @dataclass
    class Commentary:
        text: str = \""""
content = content.replace(old_stream, new_stream)

old_tool_chunk = "from gateway.stream_events import ToolCallChunk"
new_tool_chunk = """try:
    from gateway.stream_events import ToolCallChunk
except ImportError:
    @dataclass
    class ToolCallChunk:
        tool_name: str = ""
        args: dict = field(default_factory=dict)
        preview: str = \""""
content = content.replace(old_tool_chunk, new_tool_chunk)

# 12. Fix agent.display import
old_display = "from agent.display import get_tool_emoji"
new_display = """try:
    from agent.display import get_tool_emoji
except ImportError:
    def get_tool_emoji(tool_name, default="⚙️"):
        return default"""
content = content.replace(old_display, new_display)

# 13. Add pathlib import for fallback functions
if 'from pathlib import Path' not in content:
    content = content.replace('import dataclasses\n', 'import dataclasses\nfrom pathlib import Path\n')

# Write output
with open(dst, 'w', encoding='utf-8') as f:
    f.write(content)

print(f'Done! Output: {content.count(chr(10))} lines')
