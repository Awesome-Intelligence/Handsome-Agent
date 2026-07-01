#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill Environment Collector - 技能环境变量收集系统

支持技能声明所需的环境变量：
- required_environment_variables: 新格式
- prerequisites.env_vars: 旧格式兼容
"""

import os
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EnvVarRequirement:
    """环境变量需求"""
    name: str
    prompt: str
    help: Optional[str] = None
    required_for: Optional[str] = None
    optional: bool = False


def extract_required_env_vars(frontmatter: Dict[str, Any]) -> List[EnvVarRequirement]:
    """从 frontmatter 提取环境变量需求

    支持格式:
    ```yaml
    required_environment_variables:
      - name: OPENAI_API_KEY
        prompt: Enter your OpenAI API key
        help: Get from https://platform.openai.com
    ```

    旧格式:
    ```yaml
    prerequisites:
      env_vars:
        - OPENAI_API_KEY
    ```
    """
    requirements = []

    # 新格式: required_environment_variables
    required_raw = frontmatter.get("required_environment_variables", [])
    if isinstance(required_raw, dict):
        required_raw = [required_raw]
    if not isinstance(required_raw, list):
        required_raw = []

    for item in required_raw:
        if isinstance(item, str):
            requirements.append(EnvVarRequirement(
                name=item,
                prompt=f"Enter value for {item}"
            ))
        elif isinstance(item, dict):
            requirements.append(EnvVarRequirement(
                name=item.get("name", "") or item.get("env_var", ""),
                prompt=item.get("prompt", f"Enter value for {item.get('name', '')}"),
                help=item.get("help"),
                required_for=item.get("required_for"),
                optional=item.get("optional", False)
            ))

    # 旧格式兼容: prerequisites.env_vars
    prereqs = frontmatter.get("prerequisites", {})
    for env_var in prereqs.get("env_vars", []):
        if not any(r.name == env_var for r in requirements):
            requirements.append(EnvVarRequirement(
                name=env_var,
                prompt=f"Enter value for {env_var}"
            ))

    logger.debug(f"Extracted {len(requirements)} env var requirements from frontmatter")
    return requirements


def get_missing_env_vars(requirements: List[EnvVarRequirement]) -> List[str]:
    """获取缺失的环境变量列表"""
    missing = []
    for req in requirements:
        if req.optional:
            continue
        if not os.getenv(req.name):
            missing.append(req.name)

    if missing:
        logger.debug(f"Missing required env vars: {missing}")

    return missing


def is_env_var_set(name: str) -> bool:
    """检查环境变量是否已设置"""
    return bool(os.getenv(name))
