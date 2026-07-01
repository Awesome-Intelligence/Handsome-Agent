# Copyright (c) 2026 Handsome Agent Contributors
#
# 本项目采用 MIT 许可证开源
# 详细信息请参见 LICENSE 文件

"""
隔离区管理模块
将可疑技能隔离到专用目录进行安全扫描
"""

import re
import shutil
from pathlib import Path
from typing import List, Tuple, Union

from common.logging_manager import get_logger

logger = get_logger(__name__)

# 隔离目录路径
_HANDSOME_AGENT_DIR = Path.home() / ".handsome-agent"
QUARANTINE_DIR = _HANDSOME_AGENT_DIR / "security" / "quarantine"


def ensure_quarantine_dir() -> None:
    """确保隔离目录存在"""
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)


def validate_skill_name(name: str) -> str:
    """
    验证并规范化技能名称

    Args:
        name: 原始技能名称

    Returns:
        规范化后的技能名称

    Raises:
        ValueError: 如果名称不安全
    """
    if not isinstance(name, str):
        raise ValueError(f"Unsafe skill name: expected a string, got {type(name)}")

    name = name.strip()
    if not name:
        raise ValueError("Unsafe skill name: empty name")

    # 只允许字母、数字、连字符和下划线
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        raise ValueError(f"Unsafe skill name: {name}")

    return name


def validate_bundle_rel_path(path_value: str, allow_nested: bool = True) -> str:
    """
    验证并规范化技能包内的相对路径

    Args:
        path_value: 原始路径
        allow_nested: 是否允许嵌套目录

    Returns:
        规范化后的相对路径

    Raises:
        ValueError: 如果路径不安全
    """
    if not isinstance(path_value, str):
        raise ValueError(f"Unsafe bundle path: expected a string")

    raw = path_value.strip()
    if not raw:
        raise ValueError("Unsafe bundle path: empty path")

    # 标准化路径分隔符
    normalized = raw.replace("\\", "/")

    # 检查绝对路径
    if normalized.startswith("/"):
        raise ValueError(f"Unsafe bundle path: absolute path not allowed: {path_value}")

    # 检查路径遍历
    parts = [p for p in normalized.split("/") if p and p != "."]
    if ".." in parts:
        raise ValueError(f"Unsafe bundle path: path traversal not allowed: {path_value}")

    # 检查嵌套级别
    if not allow_nested and len(parts) != 1:
        raise ValueError(f"Unsafe bundle path: nested paths not allowed: {path_value}")

    return "/".join(parts)


def quarantine_bundle(
    bundle_name: str,
    files: List[Tuple[str, Union[str, bytes]]],
) -> Path:
    """
    将技能包隔离到隔离目录

    Args:
        bundle_name: 技能包名称
        files: 文件列表，每项为 (相对路径, 内容)

    Returns:
        隔离目录的路径

    Raises:
        ValueError: 如果包内容不安全
    """
    ensure_quarantine_dir()

    # 验证技能名称
    skill_name = validate_skill_name(bundle_name)
    validated_files: List[Tuple[str, Union[str, bytes]]] = []

    for rel_path, file_content in files:
        safe_rel_path = validate_bundle_rel_path(rel_path)
        validated_files.append((safe_rel_path, file_content))

    # 创建隔离目录
    dest = QUARANTINE_DIR / skill_name
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    # 写入文件
    for rel_path, file_content in validated_files:
        file_dest = dest.joinpath(*rel_path.split("/"))
        file_dest.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(file_content, bytes):
            file_dest.write_bytes(file_content)
        else:
            file_dest.write_text(file_content, encoding="utf-8")

    logger.info("Bundle '%s' quarantined to %s", skill_name, dest)
    return dest


def get_quarantined_skills() -> List[str]:
    """
    获取所有被隔离的技能列表

    Returns:
        被隔离的技能名称列表
    """
    ensure_quarantine_dir()
    return [d.name for d in QUARANTINE_DIR.iterdir() if d.is_dir()]


def delete_quarantined_skill(skill_name: str) -> bool:
    """
    删除被隔离的技能

    Args:
        skill_name: 技能名称

    Returns:
        是否成功删除
    """
    try:
        skill_path = QUARANTINE_DIR / validate_skill_name(skill_name)
        if skill_path.exists() and skill_path.is_dir():
            shutil.rmtree(skill_path)
            logger.info("Deleted quarantined skill: %s", skill_name)
            return True
        return False
    except (ValueError, OSError) as e:
        logger.warning("Could not delete quarantined skill %s: %s", skill_name, e)
        return False