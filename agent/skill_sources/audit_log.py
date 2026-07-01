#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""审计日志模块

记录所有技能操作到审计日志文件。
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 审计日志路径（相对于配置目录）
AUDIT_LOG_FILENAME = Path(".hub") / "audit.log"


def get_audit_log_path() -> Path:
    """获取审计日志文件路径"""
    from common.config import get_config_dir
    config_dir = get_config_dir()
    return config_dir / AUDIT_LOG_FILENAME


def ensure_audit_log_dir() -> None:
    """确保审计日志目录存在"""
    audit_path = get_audit_log_path()
    audit_path.parent.mkdir(parents=True, exist_ok=True)


def append_audit_log(
    action: str,
    skill_name: str,
    source: str,
    trust_level: str,
    verdict: str,
    extra: str = "",
) -> None:
    """
    追加审计日志条目。

    Args:
        action: 操作类型 (INSTALL, UNINSTALL, UPDATE, etc.)
        skill_name: 技能名称
        source: 来源 (github, hermes-index, etc.)
        trust_level: 信任级别 (builtin, trusted, community)
        verdict: 扫描结果 (clean, warn, block, n/a)
        extra: 额外信息（如 content hash）
    """
    try:
        ensure_audit_log_dir()
        audit_path = get_audit_log_path()

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        parts = [timestamp, action, skill_name, f"{source}:{trust_level}", verdict]
        if extra:
            parts.append(extra)

        line = " ".join(parts) + "\n"

        with open(audit_path, "a", encoding="utf-8") as f:
            f.write(line)

        logger.debug("Audit log: %s %s", action, skill_name)

    except Exception as e:
        logger.warning("Could not write audit log: %s", e)


def read_audit_log(limit: int = 100) -> list:
    """
    读取审计日志。

    Args:
        limit: 返回的最大条目数

    Returns:
        审计日志条目列表，每条为 dict
    """
    audit_path = get_audit_log_path()

    if not audit_path.exists():
        return []

    try:
        lines = audit_path.read_text(encoding="utf-8").strip().split("\n")
        entries = []

        for line in reversed(lines):
            if not line.strip():
                continue

            parts = line.split(" ", 4)
            if len(parts) >= 4:
                entry = {
                    "timestamp": parts[0],
                    "action": parts[1],
                    "skill_name": parts[2],
                    "source_trust": parts[3],
                    "verdict": parts[4] if len(parts) > 4 else "",
                }
                entries.append(entry)

                if len(entries) >= limit:
                    break

        return entries

    except Exception as e:
        logger.warning("Could not read audit log: %s", e)
        return []


def clear_audit_log() -> bool:
    """
    清空审计日志。

    Returns:
        是否成功
    """
    try:
        audit_path = get_audit_log_path()
        if audit_path.exists():
            audit_path.unlink()
        return True
    except Exception as e:
        logger.warning("Could not clear audit log: %s", e)
        return False