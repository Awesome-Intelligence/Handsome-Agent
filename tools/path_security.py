#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路径安全防护模块

提供路径安全验证功能，防止路径穿越攻击。
兼容 Windows 和 Unix 系统。
"""

import os
from pathlib import Path
from typing import Optional

from common.logging_manager import get_logger

# 获取模块日志记录器
logger = get_logger(__name__)


def has_traversal_component(path: str) -> bool:
    """检测路径是否包含路径穿越组件

    检测给定的路径字符串是否包含：
    - `..` 目录回退组件
    - 绝对路径前缀（如 Windows 的盘符或 Unix 的 /）

    Args:
        path: 要检查的路径字符串

    Returns:
        如果路径包含穿越组件返回 True，否则返回 False
    """
    # 检查是否存在 ".." 目录回退
    if ".." in path:
        logger.debug("检测到路径穿越组件: ..")
        return True

    # 检查是否为绝对路径
    # 在 Windows 上，isabs 会检测盘符路径（如 C:\、D:/）
    # 在 Unix 上，isabs 会检测以 / 开头的路径
    if os.path.isabs(path):
        logger.debug("检测到绝对路径")
        return True

    return False


def validate_within_dir(target: Path, base: Path) -> Optional[str]:
    """验证目标路径是否在基础目录范围内

    使用 pathlib.Path 的 resolve() 和 relative_to() 方法进行安全验证。
    该方法可以正确处理符号链接等复杂路径场景。

    Args:
        target: 目标路径（可以是相对路径或绝对路径）
        base: 基础目录路径（用于限制访问范围）

    Returns:
        如果目标路径在基础目录内返回 None；
        如果检测到路径穿越返回错误消息字符串
    """
    try:
        # 使用 resolve() 获取规范化后的绝对路径
        # resolve() 会解析符号链接并规范化路径
        target_resolved = target.resolve()
        base_resolved = base.resolve()

        # 尝试计算相对路径
        # 如果 target 不在 base 目录下，会抛出 ValueError
        target_resolved.relative_to(base_resolved)

        logger.debug(f"路径验证通过: {target_resolved} 在 {base_resolved} 内")
        return None

    except ValueError:
        error_msg = f"Path traversal detected: {target}"
        logger.warning(error_msg)
        return error_msg
