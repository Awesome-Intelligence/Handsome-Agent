#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Credential Manager Module - Handsome Agent

凭证管理器模块，提供密钥的安全存储和验证功能。

功能：
- 支持密钥的安全输入和存储
- 验证环境变量是否已设置
- 支持凭证文件路径注册
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from common.logging_manager import get_system_logger

logger = get_system_logger("CredentialManager")


@dataclass
class SecretMetadata:
    """密钥元数据"""
    source: str = "manual"
    label: str = ""
    description: str = ""
    provider: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecretCaptureResult:
    """密钥捕获结果"""
    success: bool
    env_var: str
    value: Optional[str] = None
    message: str = ""
    already_set: bool = False


@dataclass
class CredentialFileRegistrationResult:
    """凭证文件注册结果"""
    success: bool
    path: str
    exists: bool = False
    missing_files: List[str] = field(default_factory=list)
    message: str = ""


class CredentialManager:
    """凭证管理器
    
    提供凭证的安全管理功能，包括：
    - 密钥的安全输入和环境变量验证
    - 凭证文件的路径注册和安全检查
    """
    
    def __init__(self, home_dir: Optional[str] = None):
        """初始化凭证管理器
        
        Args:
            home_dir: 凭证存储根目录，默认使用用户主目录
        """
        self._home_dir = Path(home_dir) if home_dir else Path.home()
        self._registered_files: Dict[str, str] = {}
        self._required_env_vars: List[str] = []
        
        logger.debug("初始化凭证管理器，home_dir: %s", self._home_dir)
    
    @property
    def home_dir(self) -> Path:
        """获取凭证存储根目录"""
        return self._home_dir
    
    def capture_secret(
        self,
        env_var: str,
        prompt: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SecretCaptureResult:
        """捕获用户输入的密钥
        
        验证环境变量是否已设置，如果未设置则返回提示信息。
        
        Args:
            env_var: 环境变量名
            prompt: 当密钥未设置时显示的提示信息
            metadata: 密钥元数据
            
        Returns:
            SecretCaptureResult: 包含捕获结果的字典
        """
        if metadata is None:
            metadata = {}
        
        meta = SecretMetadata(
            source=metadata.get("source", "manual"),
            label=metadata.get("label", env_var),
            description=metadata.get("description", ""),
            provider=metadata.get("provider", ""),
            extra=metadata.get("extra", {}),
        )
        
        # 检查环境变量是否已设置
        current_value = os.environ.get(env_var)
        
        if current_value:
            logger.debug("环境变量 %s 已设置 (source: %s)", env_var, meta.source)
            return SecretCaptureResult(
                success=True,
                env_var=env_var,
                value=current_value,
                message=f"环境变量 {env_var} 已设置",
                already_set=True,
            )
        
        # 环境变量未设置，返回提示信息
        logger.info("环境变量 %s 未设置，需要用户输入", env_var)
        return SecretCaptureResult(
            success=False,
            env_var=env_var,
            value=None,
            message=prompt,
            already_set=False,
        )
    
    def validate_env_var(self, env_var: str) -> Tuple[bool, Optional[str]]:
        """验证环境变量是否已设置
        
        Args:
            env_var: 环境变量名
            
        Returns:
            Tuple[bool, Optional[str]]: (是否已设置, 当前值)
        """
        value = os.environ.get(env_var)
        is_set = value is not None and value != ""
        
        if is_set:
            logger.debug("环境变量 %s 已设置", env_var)
        else:
            logger.debug("环境变量 %s 未设置", env_var)
        
        return is_set, value
    
    def validate_required_env_vars(self) -> Tuple[bool, List[str]]:
        """验证所有必需的环境变量是否已设置
        
        Returns:
            Tuple[bool, List[str]]: (是否全部设置, 缺失的环境变量列表)
        """
        missing = []
        for env_var in self._required_env_vars:
            is_set, _ = self.validate_env_var(env_var)
            if not is_set:
                missing.append(env_var)
        
        all_set = len(missing) == 0
        if all_set:
            logger.debug("所有必需环境变量已设置")
        else:
            logger.info("缺失必需环境变量: %s", missing)
        
        return all_set, missing
    
    def add_required_env_var(self, env_var: str) -> None:
        """添加必需的环境变量
        
        Args:
            env_var: 环境变量名
        """
        if env_var not in self._required_env_vars:
            self._required_env_vars.append(env_var)
            logger.debug("添加必需环境变量: %s", env_var)
    
    def remove_required_env_var(self, env_var: str) -> None:
        """移除必需的环境变量
        
        Args:
            env_var: 环境变量名
        """
        if env_var in self._required_env_vars:
            self._required_env_vars.remove(env_var)
            logger.debug("移除必需环境变量: %s", env_var)
    
    def register_credential_file(self, path: str) -> Tuple[bool, List[str]]:
        """注册凭证文件
        
        注册一个凭证文件路径，验证其安全性（不能是绝对路径或路径遍历）
        并检查文件是否存在。
        
        Args:
            path: 凭证文件路径（相对路径，相对于 home_dir）
            
        Returns:
            Tuple[bool, List[str]]: (是否成功, 缺失文件列表)
        """
        missing_files: List[str] = []
        
        # 拒绝绝对路径
        if os.path.isabs(path):
            logger.warning(
                "credential_files: 拒绝绝对路径 %r (必须相对于 home_dir)",
                path,
            )
            return False, [path]
        
        # 检查路径遍历
        resolved_path = (self._home_dir / path).resolve()
        try:
            resolved_path.relative_to(self._home_dir.resolve())
        except ValueError:
            logger.warning(
                "credential_files: 拒绝路径遍历 %r (会超出 home_dir)",
                path,
            )
            return False, [path]
        
        # 检查文件是否存在
        if not resolved_path.is_file():
            logger.debug("credential_files: 文件不存在 %s", resolved_path)
            missing_files.append(path)
            return False, missing_files
        
        # 注册文件
        container_path = f"{str(self._home_dir)}/{path}"
        self._registered_files[container_path] = str(resolved_path)
        logger.debug("credential_files: 注册成功 %s -> %s", resolved_path, container_path)
        
        return True, []
    
    def register_credential_files(
        self,
        paths: List[str]
    ) -> Tuple[bool, List[str]]:
        """批量注册凭证文件
        
        Args:
            paths: 凭证文件路径列表
            
        Returns:
            Tuple[bool, List[str]]: (是否全部成功, 缺失文件列表)
        """
        all_missing: List[str] = []
        all_success = True
        
        for path in paths:
            success, missing = self.register_credential_file(path)
            if not success:
                all_success = False
                all_missing.extend(missing)
        
        return all_success, all_missing
    
    def get_registered_files(self) -> Dict[str, str]:
        """获取已注册的凭证文件映射
        
        Returns:
            Dict[str, str]: {容器路径: 主机路径}
        """
        return self._registered_files.copy()
    
    def clear_registered_files(self) -> None:
        """清除所有已注册的凭证文件"""
        self._registered_files.clear()
        logger.debug("已清除所有注册的凭证文件")
    
    def get_credential_file_mounts(self) -> List[Dict[str, str]]:
        """获取凭证文件挂载信息（用于远程沙箱）
        
        Returns:
            List[Dict[str, str]]: 包含 host_path 和 container_path 的列表
        """
        mounts = []
        for container_path, host_path in self._registered_files.items():
            if Path(host_path).is_file():
                mounts.append({
                    "host_path": host_path,
                    "container_path": container_path,
                })
        return mounts


# 模块级单例
_credential_manager: Optional[CredentialManager] = None


def get_credential_manager() -> CredentialManager:
    """获取凭证管理器单例
    
    Returns:
        CredentialManager: 凭证管理器实例
    """
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = CredentialManager()
    return _credential_manager


def reset_credential_manager() -> None:
    """重置凭证管理器单例"""
    global _credential_manager
    _credential_manager = None
