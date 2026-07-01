# Copyright (c) 2026 Handsome Agent Contributors
#
# 本项目采用 MIT 许可证开源
# 详细信息请参见 LICENSE 文件

"""
审计日志模块
记录所有技能相关操作的安全审计信息
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from common.logging_manager import get_logger

logger = get_logger(__name__)

# 审计日志路径 - 放在项目根目录的 .handsome-agent 目录
_HANDSOME_AGENT_DIR = Path.home() / ".handsome-agent"
_AUDIT_LOG_DIR = _HANDSOME_AGENT_DIR / "security"
AUDIT_LOG = _AUDIT_LOG_DIR / "audit.log"
AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)


def ensure_audit_dirs() -> None:
    """确保审计目录存在"""
    _AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    if not AUDIT_LOG.exists():
        AUDIT_LOG.touch()


def append_audit_log(
    action: str,
    skill_name: str,
    source: str,
    trust_level: str,
    verdict: str,
    extra: str = "",
) -> None:
    """
    追加审计日志条目

    Args:
        action: 操作类型 (scan, install, block, quarantine, etc.)
        skill_name: 技能名称
        source: 技能来源
        trust_level: 信任级别 (builtin, trusted, community)
        verdict: 扫描判决结果 (safe, caution, dangerous)
        extra: 额外信息
    """
    ensure_audit_dirs()

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    parts = [
        timestamp,
        action,
        skill_name,
        f"{source}:{trust_level}",
        verdict,
    ]
    if extra:
        parts.append(extra)

    line = " ".join(parts) + "\n"

    try:
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(line)
        logger.debug("Audit log entry added: %s %s", action, skill_name)
    except OSError as e:
        logger.warning("Could not write audit log: %s", e)


def get_audit_log(limit: Optional[int] = None) -> str:
    """
    获取审计日志内容

    Args:
        limit: 最多返回的行数

    Returns:
        审计日志内容
    """
    ensure_audit_dirs()

    try:
        with open(AUDIT_LOG, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if limit:
            lines = lines[-limit:]

        return "".join(lines)
    except OSError as e:
        logger.warning("Could not read audit log: %s", e)
        return ""


def clear_audit_log() -> bool:
    """
    清空审计日志

    Returns:
        是否成功清空
    """
    try:
        ensure_audit_dirs()
        with open(AUDIT_LOG, "w", encoding="utf-8") as f:
            f.write("")
        return True
    except OSError as e:
        logger.warning("Could not clear audit log: %s", e)
        return False