"""
DM Pairing System (Agent-Z minimal port from Hermes).

Code-based approval flow for authorizing new users on messaging platforms.
Unknown users receive a one-time pairing code that the bot owner approves via
the CLI / settings screen.

Security features:
  - 8-char codes from a 32-char unambiguous alphabet (no 0/O/1/I)
  - Cryptographic randomness via secrets.choice()
  - 1-hour code expiry
  - Max 3 pending codes per platform
  - Rate limiting: 1 request per user per 10 minutes
  - Lockout after 5 failed approval attempts (1 hour)

Storage: ``<agentz_home>/platforms/pairing/`` (falls back to ``<hermes_home>/pairing/``).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from gateway.platforms._hermes_stubs import get_hermes_home

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Unambiguous alphabet -- excludes 0/O, 1/I to prevent user confusion.
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8

CODE_TTL_SECONDS = 3600         # Codes expire after 1 hour
RATE_LIMIT_SECONDS = 600        # 1 code-issue request per user per 10 minutes
LOCKOUT_SECONDS = 3600          # Lockout duration after too many failed approvals
MAX_PENDING_PER_PLATFORM = 3    # Max pending codes per platform
MAX_FAILED_ATTEMPTS = 5         # Failed approvals before lockout kicks in

# Platform -> allowlist env var (mirrored by approve/revoke so the operator's
# list stays a single visible/editable source of truth).  Absent platforms
# keep PairingStore.approved.json as the sole grant, honored by the authz union.
_PLATFORM_ALLOWLIST_ENV: Dict[str, str] = {
    "telegram": "TELEGRAM_ALLOWED_USERS",
    "discord": "DISCORD_ALLOWED_USERS",
    "whatsapp": "WHATSAPP_ALLOWED_USERS",
    "whatsapp_cloud": "WHATSAPP_CLOUD_ALLOWED_USERS",
    "slack": "SLACK_ALLOWED_USERS",
    "signal": "SIGNAL_ALLOWED_USERS",
    "email": "EMAIL_ALLOWED_USERS",
    "sms": "SMS_ALLOWED_USERS",
    "mattermost": "MATTERMOST_ALLOWED_USERS",
    "matrix": "MATRIX_ALLOWED_USERS",
    "dingtalk": "DINGTALK_ALLOWED_USERS",
    "feishu": "FEISHU_ALLOWED_USERS",
    "wecom": "WECOM_ALLOWED_USERS",
    "wecom_callback": "WECOM_CALLBACK_ALLOWED_USERS",
    "weixin": "WEIXIN_ALLOWED_USERS",
    "bluebubbles": "BLUEBUBBLES_ALLOWED_USERS",
    "qqbot": "QQ_ALLOWED_USERS",
    "yuanbao": "YUANBAO_ALLOWED_USERS",
    "line": "LINE_ALLOWED_USERS",
    "irc": "IRC_ALLOWED_USERS",
    "teams": "TEAMS_ALLOWED_USERS",
    "google_chat": "GOOGLE_CHAT_ALLOWED_USERS",
    "homeassistant": "HOMEASSISTANT_ALLOWED_USERS",
    "ntfy": "NTFY_ALLOWED_USERS",
    "simplex": "SIMPLEX_ALLOWED_USERS",
    "raft": "RAFT_ALLOWED_USERS",
    "photon": "PHOTON_ALLOWED_USERS",
}


def _allowlist_env_for_platform(platform: str) -> Optional[str]:
    platform = (platform or "").lower().strip()
    env_var = _PLATFORM_ALLOWLIST_ENV.get(platform)
    if env_var:
        return env_var
    try:
        from gateway.platforms import platform_registry

        entry = platform_registry.get(platform)
        if entry and getattr(entry, "allowed_users_env", None):
            return entry.allowed_users_env
    except Exception:
        pass
    return None


def _split_allowlist(raw: str) -> List[str]:
    return [uid.strip() for uid in raw.split(",") if uid.strip()]


def _sync_allowlist_add(platform: str, user_id: str) -> None:
    """Mirror an approved user into the operator's allowlist env when one is configured.

    Open gateways (no allowlist env set) are intentionally left alone: we never
    silently convert an open gateway into a locked one on the first pairing.
    """
    env_var = _allowlist_env_for_platform(platform)
    if not env_var:
        return
    current = os.getenv(env_var, "").strip()
    if not current:
        return  # Open gateway — do nothing.
    ids = _split_allowlist(current)
    if "*" in ids or str(user_id) in ids:
        return
    ids.append(str(user_id))
    # Best-effort: persist to .env so future restarts keep the grant in sync.
    try:
        from common.env_helpers import save_env_value  # type: ignore
        save_env_value(env_var, ",".join(ids))
    except Exception:
        try:
            from cli.config import save_env_value  # type: ignore
            save_env_value(env_var, ",".join(ids))
        except Exception:
            pass  # The pairing store still authorizes via union — mirror is best effort.


def _sync_allowlist_remove(platform: str, user_id: str) -> None:
    env_var = _allowlist_env_for_platform(platform)
    if not env_var:
        return
    current = os.getenv(env_var, "").strip()
    if not current:
        return
    ids = _split_allowlist(current)
    remaining = [i for i in ids if i != str(user_id)]
    if len(remaining) == len(ids):
        return
    try:
        from common.env_helpers import save_env_value, remove_env_value  # type: ignore
        if remaining:
            save_env_value(env_var, ",".join(remaining))
        else:
            remove_env_value(env_var)
    except Exception:
        try:
            from cli.config import save_env_value, remove_env_value  # type: ignore
            if remaining:
                save_env_value(env_var, ",".join(remaining))
            else:
                remove_env_value(env_var)
        except Exception:
            pass


def _atomic_write_text(path: Path, text: str) -> None:
    """Atomic replace via tempfile + rename; chmod 0600 on POSIX platforms."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path_str = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        tmp_path.replace(path)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass  # Windows / some Docker filesystems don't support POSIX modes.
    except BaseException:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        raise


def _resolve_pairing_root() -> Path:
    try:
        base = Path(get_hermes_home())
    except Exception:
        base = Path.home() / ".agent-z"
    return base / "platforms" / "pairing"


PAIRING_DIR: Path = _resolve_pairing_root()


# ---------------------------------------------------------------------------
# PairingStore
# ---------------------------------------------------------------------------


class PairingStore:
    """Persisted pairing codes + approved-user lists.

    Data files per platform:
      * ``{platform}-pending.json`` — pending pairing requests (code hashed + salted).
      * ``{platform}-approved.json`` — approved (paired) users.
      * ``_rate_limits.json`` — rate-limit tracking + lockout timestamps.
    """

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root: Path = Path(root) if root else PAIRING_DIR
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    # -- Path helpers -------------------------------------------------------

    def _pending_path(self, platform: str) -> Path:
        return self.root / f"{platform}-pending.json"

    def _approved_path(self, platform: str) -> Path:
        return self.root / f"{platform}-approved.json"

    def _rate_limit_path(self) -> Path:
        return self.root / "_rate_limits.json"

    # -- JSON I/O -----------------------------------------------------------

    def _load_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_json(self, path: Path, data: Dict[str, Any]) -> None:
        _atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False))

    # -- User-ID normalisation ---------------------------------------------

    def _normalize_user_id(self, platform: str, user_id: str) -> str:
        return str(user_id or "").strip()

    def _user_id_aliases(self, platform: str, user_id: str) -> Set[str]:
        raw = str(user_id or "").strip()
        if not raw:
            return set()
        return {raw, self._normalize_user_id(platform, raw)}

    def _user_ids_match(self, platform: str, left: str, right: str) -> bool:
        l_alias = self._user_id_aliases(platform, left)
        r_alias = self._user_id_aliases(platform, right)
        return bool(l_alias and r_alias and (l_alias & r_alias))

    # -- Approved users -----------------------------------------------------

    def is_approved(self, platform: str, user_id: str) -> bool:
        if not platform or not user_id:
            return False
        approved = self._load_json(self._approved_path(platform))
        for uid in approved:
            if self._user_ids_match(platform, uid, user_id):
                return True
        return False

    def list_approved(self, platform: Optional[str] = None) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        platforms = [platform] if platform else self._all_platforms("approved")
        for p in platforms:
            approved = self._load_json(self._approved_path(p))
            for uid, info in approved.items():
                if not isinstance(info, dict):
                    info = {}
                results.append({"platform": p, "user_id": uid, **info})
        return results

    def _approve_user(self, platform: str, user_id: str, user_name: str = "") -> None:
        """Caller must hold ``self._lock``."""
        approved = self._load_json(self._approved_path(platform))
        normalized = self._normalize_user_id(platform, user_id)
        duplicates = [u for u in approved if self._user_ids_match(platform, u, normalized)]
        for u in duplicates:
            del approved[u]
        approved[normalized] = {"user_name": user_name, "approved_at": time.time()}
        self._save_json(self._approved_path(platform), approved)
        _sync_allowlist_add(platform, normalized)

    def approve_user(self, platform: str, user_id: str, user_name: str = "") -> None:
        with self._lock:
            self._approve_user(platform, user_id, user_name)

    def revoke(self, platform: str, user_id: str) -> bool:
        path = self._approved_path(platform)
        with self._lock:
            approved = self._load_json(path)
            matching = [u for u in approved if self._user_ids_match(platform, u, user_id)]
            if not matching:
                return False
            for u in matching:
                del approved[u]
            self._save_json(path, approved)
            _sync_allowlist_remove(platform, user_id)
            return True

    # -- Pending codes ------------------------------------------------------

    @staticmethod
    def _hash_code(code: str, salt: bytes) -> str:
        return hashlib.sha256(salt + code.encode("utf-8")).hexdigest()

    def generate_code(self, platform: str, user_id: str, user_name: str = "") -> Optional[str]:
        with self._lock:
            self._cleanup_expired(platform)
            norm = self._normalize_user_id(platform, user_id)
            if self._is_locked_out(platform):
                return None
            if self._is_rate_limited(platform, user_id):
                return None
            pending = self._load_json(self._pending_path(platform))
            if len(pending) >= MAX_PENDING_PER_PLATFORM:
                return None
            code = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
            salt = os.urandom(16)
            code_hash = self._hash_code(code, salt)
            entry_id = secrets.token_hex(8)
            pending[entry_id] = {
                "hash": code_hash,
                "salt": salt.hex(),
                "user_id": norm,
                "user_name": user_name,
                "created_at": time.time(),
            }
            self._save_json(self._pending_path(platform), pending)
            self._record_rate_limit(platform, user_id)
            return code

    def approve_code(self, platform: str, code: str) -> Optional[Dict[str, str]]:
        with self._lock:
            self._cleanup_expired(platform)
            code = code.upper().strip()
            if not code:
                return None
            if self._is_locked_out(platform):
                return None
            pending = self._load_json(self._pending_path(platform))
            matched_key: Optional[str] = None
            matched_entry: Optional[Dict[str, Any]] = None
            for entry_id, entry in pending.items():
                if not isinstance(entry, dict) or "salt" not in entry or "hash" not in entry:
                    continue
                try:
                    salt = bytes.fromhex(entry["salt"])
                except ValueError:
                    continue
                candidate = self._hash_code(code, salt)
                if secrets.compare_digest(candidate, entry["hash"]):
                    matched_key = entry_id
                    matched_entry = entry
                    break
            if matched_key is None or matched_entry is None:
                self._record_failed_attempt(platform)
                return None
            del pending[matched_key]
            self._save_json(self._pending_path(platform), pending)
            self._approve_user(
                platform,
                matched_entry.get("user_id", ""),
                matched_entry.get("user_name", ""),
            )
            return {
                "user_id": str(matched_entry.get("user_id", "")),
                "user_name": str(matched_entry.get("user_name", "")),
            }

    def list_pending(self, platform: Optional[str] = None) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        with self._lock:
            platforms = [platform] if platform else self._all_platforms("pending")
            for p in platforms:
                self._cleanup_expired(p)
                pending = self._load_json(self._pending_path(p))
                for _entry_id, info in pending.items():
                    if not isinstance(info, dict):
                        continue
                    created_at = info.get("created_at")
                    if not isinstance(created_at, (int, float)):
                        continue
                    age_min = int((time.time() - created_at) / 60)
                    h = info.get("hash")
                    display = h[:8] if isinstance(h, str) else "legacy"
                    results.append(
                        {
                            "platform": p,
                            "code": display,
                            "user_id": str(info.get("user_id", "")),
                            "user_name": str(info.get("user_name", "")),
                            "age_minutes": age_min,
                        }
                    )
        return results

    def clear_pending(self, platform: Optional[str] = None) -> int:
        removed = 0
        with self._lock:
            platforms = [platform] if platform else self._all_platforms("pending")
            for p in platforms:
                pending = self._load_json(self._pending_path(p))
                removed += len(pending)
                self._save_json(self._pending_path(p), {})
        return removed

    # -- Rate limiting / lockout -------------------------------------------

    def _is_rate_limited(self, platform: str, user_id: str) -> bool:
        limits = self._load_json(self._rate_limit_path())
        for alias in self._user_id_aliases(platform, user_id):
            last = limits.get(f"{platform}:{alias}", 0)
            if (time.time() - float(last)) < RATE_LIMIT_SECONDS:
                return True
        return False

    def _record_rate_limit(self, platform: str, user_id: str) -> None:
        limits = self._load_json(self._rate_limit_path())
        now = time.time()
        for alias in self._user_id_aliases(platform, user_id):
            limits[f"{platform}:{alias}"] = now
        self._save_json(self._rate_limit_path(), limits)

    def _is_locked_out(self, platform: str) -> bool:
        limits = self._load_json(self._rate_limit_path())
        return time.time() < float(limits.get(f"_lockout:{platform}", 0))

    def _record_failed_attempt(self, platform: str) -> None:
        limits = self._load_json(self._rate_limit_path())
        fail_key = f"_failures:{platform}"
        fails = int(limits.get(fail_key, 0)) + 1
        limits[fail_key] = fails
        if fails >= MAX_FAILED_ATTEMPTS:
            limits[f"_lockout:{platform}"] = time.time() + LOCKOUT_SECONDS
            limits[fail_key] = 0
            logger.warning(
                "Platform %s locked out for %ss after %d failed approval attempts",
                platform,
                LOCKOUT_SECONDS,
                MAX_FAILED_ATTEMPTS,
            )
        self._save_json(self._rate_limit_path(), limits)

    # -- Cleanup ------------------------------------------------------------

    def _cleanup_expired(self, platform: str) -> None:
        path = self._pending_path(platform)
        pending = self._load_json(path)
        now = time.time()
        expired: List[str] = []
        for entry_id, info in pending.items():
            if not isinstance(info, dict):
                expired.append(entry_id)
                continue
            created_at = info.get("created_at")
            if not isinstance(created_at, (int, float)):
                expired.append(entry_id)
                continue
            if (now - float(created_at)) > CODE_TTL_SECONDS:
                expired.append(entry_id)
        if expired:
            for e in expired:
                del pending[e]
            self._save_json(path, pending)

    def _all_platforms(self, suffix: str) -> List[str]:
        platforms: List[str] = []
        if not self.root.exists():
            return platforms
        for f in self.root.iterdir():
            tail = f"-{suffix}.json"
            if f.is_file() and f.name.endswith(tail):
                platforms.append(f.name[: -len(tail)])
        return platforms


# ---------------------------------------------------------------------------
# Default singleton (lazily constructed).
# ---------------------------------------------------------------------------

_store_lock = threading.Lock()
_default_store: Optional[PairingStore] = None


def get_default_pairing_store() -> PairingStore:
    """Return the process-wide default PairingStore singleton."""
    global _default_store
    if _default_store is None:
        with _store_lock:
            if _default_store is None:
                _default_store = PairingStore()
    return _default_store


__all__ = [
    "ALPHABET",
    "CODE_LENGTH",
    "CODE_TTL_SECONDS",
    "RATE_LIMIT_SECONDS",
    "LOCKOUT_SECONDS",
    "MAX_PENDING_PER_PLATFORM",
    "MAX_FAILED_ATTEMPTS",
    "PAIRING_DIR",
    "PairingStore",
    "get_default_pairing_store",
]
