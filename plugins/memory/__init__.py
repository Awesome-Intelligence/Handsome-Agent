#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Provider Plugin System - 外部记忆 Provider 插件

参考 Hermes Agent 的插件架构设计，支持：
- 插件发现机制 (discover_memory_providers)
- 动态加载 (load_memory_provider)
- 配置校验 (validate_provider_config)
- 错误处理和诊断 (ProviderDiagnostics)

目录结构：
    plugins/memory/<name>/
    ├── __init__.py      # Provider 实现 + register() 入口点
    ├── plugin.yaml      # 清单文件（可选）
    └── *.py             # 辅助模块

标准插件需要导出：
    def register(ctx: "PluginContext") -> None:
        ctx.register_memory_provider(<MemoryProviderInstance>())

Usage:
    from plugins.memory import discover_memory_providers, load_memory_provider
    
    # 发现可用插件
    providers = discover_memory_providers()
    
    # 加载插件
    provider = load_memory_provider("honcho")
    
    # 配置校验
    from plugins.memory import validate_provider_config, ProviderDiagnostics
    result = validate_provider_config("honcho", config)
    if not result.is_valid:
        print(result.errors)
"""

import importlib
import importlib.util
import logging
import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, TYPE_CHECKING

from common.config import AGENT_Z_HOME
from common.logging_manager import get_system_logger

if TYPE_CHECKING:
    from agent.memory.memory_provider import MemoryProvider

logger = get_system_logger("MemoryPlugin")

# 插件目录
_PLUGINS_DIR = Path(__file__).parent  # plugins/memory/
_USER_PLUGINS_DIR = AGENT_Z_HOME / "plugins" / "memory"

# 发现状态缓存
_discovered: Optional[List[Tuple[str, Path]]] = None
_loaded_providers: Dict[str, "MemoryProvider"] = {}
_diagnostics_cache: Dict[str, "ProviderDiagnostics"] = {}


# ============================================================================
# Provider Status & Diagnostics
# ============================================================================

class ProviderStatus(str, Enum):
    """Provider 状态枚举"""
    NOT_FOUND = "not_found"           # 未找到
    FOUND_BUT_UNAVAILABLE = "found_but_unavailable"  # 找到但不可用
    AVAILABLE = "available"           # 可用
    LOADED = "loaded"                 # 已加载
    ERROR = "error"                   # 加载错误
    CONFIG_INVALID = "config_invalid" # 配置无效


@dataclass
class ProviderDiagnostics:
    """Provider 诊断信息"""
    name: str
    status: ProviderStatus
    path: Optional[str] = None
    is_available: bool = False
    error: Optional[str] = None
    error_type: Optional[str] = None
    config_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    available_tools: List[str] = field(default_factory=list)
    config_schema: List[Dict[str, Any]] = field(default_factory=list)
    last_check: Optional[float] = None

    @property
    def is_valid(self) -> bool:
        """是否有效（可用于生产）"""
        return self.status in (ProviderStatus.AVAILABLE, ProviderStatus.LOADED)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "status": self.status.value,
            "path": self.path,
            "is_available": self.is_available,
            "is_valid": self.is_valid,
            "error": self.error,
            "error_type": self.error_type,
            "config_errors": self.config_errors,
            "warnings": self.warnings,
            "available_tools": self.available_tools,
            "config_schema": self.config_schema,
        }


# ============================================================================
# Provider Validation Result
# ============================================================================

@dataclass
class ProviderValidationResult:
    """Provider 配置校验结果"""
    provider_name: str
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.is_valid

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "provider_name": self.provider_name,
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
        }


# ============================================================================
# Plugin Context (插件注册上下文)
# ============================================================================

class PluginContext:
    """插件注册上下文 - 提供 register_* 方法供插件使用"""
    
    def __init__(self, name: str):
        self._name = name
        self._provider: Optional["MemoryProvider"] = None
        self._hooks: List[Tuple[str, callable]] = []
    
    @property
    def name(self) -> str:
        """插件名称"""
        return self._name
    
    def register_memory_provider(self, provider: "MemoryProvider") -> None:
        """注册记忆 Provider"""
        self._provider = provider
    
    @property
    def provider(self) -> Optional["MemoryProvider"]:
        """获取注册的 Provider"""
        return self._provider


# ============================================================================
# Plugin Discovery (插件发现)
# ============================================================================

def _iter_provider_dirs() -> List[Tuple[str, Path]]:
    """
    迭代所有发现的 Provider 目录。
    
    顺序：
    1. Bundled plugins: <repo>/plugins/memory/<name>/
    2. User plugins: $AGENT_Z_HOME/plugins/<name>/
    
    Yields:
        Tuple of (name, path)
    """
    dirs: List[Tuple[str, Path]] = []
    seen: set = set()
    
    # 1. Bundled providers
    if _PLUGINS_DIR.is_dir():
        for child in sorted(_PLUGINS_DIR.iterdir()):
            if not child.is_dir():
                continue
            if child.name.startswith(("_", ".")):
                continue
            if child.name == "__pycache__":
                continue
            if not (child / "__init__.py").exists():
                continue
            seen.add(child.name)
            dirs.append((child.name, child))
    
    # 2. User-installed providers
    if _USER_PLUGINS_DIR.is_dir():
        for child in sorted(_USER_PLUGINS_DIR.iterdir()):
            if not child.is_dir():
                continue
            if child.name.startswith(("_", ".")):
                continue
            if child.name in seen:
                continue  # Bundled takes precedence
            if not (child / "__init__.py").exists():
                continue
            dirs.append((child.name, child))
    
    return dirs


def _is_memory_provider_dir(path: Path) -> bool:
    """
    检查目录是否看起来像记忆 Provider。
    
    启发式检查 __init__.py 中是否包含 register_memory_provider 或 MemoryProvider。
    """
    init_file = path / "__init__.py"
    if not init_file.exists():
        return False
    try:
        source = init_file.read_text(errors="replace")[:8192]
        return "register_memory_provider" in source or "MemoryProvider" in source
    except Exception:
        return False


def discover_memory_providers() -> List[Tuple[str, bool, str]]:
    """
    发现所有已安装的记忆 Provider。
    
    Returns:
        List of (name, is_available, error_message) tuples
    """
    global _discovered
    
    if _discovered is not None:
        return [(n, p.exists(), str(p)) for n, p in _discovered]
    
    _discovered = []
    results: List[Tuple[str, bool, str]] = []
    
    for name, path in _iter_provider_dirs():
        _discovered.append((name, path))
        
        # 检查 is_available() 方法
        provider = _load_provider_from_dir(name, path)
        if provider:
            try:
                available = provider.is_available()
            except Exception as e:
                available = False
                logger.debug(f"Provider {name} is_available() failed: {e}")
        else:
            available = False
        
        results.append((name, available, str(path)))
    
    return results


def find_provider_dir(name: str) -> Optional[Path]:
    """
    查找指定名称的 Provider 目录。
    
    Args:
        name: Provider 名称
    
    Returns:
        Provider 目录路径，或 None
    """
    global _discovered
    
    if _discovered is None:
        discover_memory_providers()
    
    for n, path in _discovered or []:
        if n == name:
            return path
    
    return None


# ============================================================================
# Plugin Loading (插件加载)
# ============================================================================

def _load_provider_from_dir(name: str, path: Optional[Path] = None) -> Optional["MemoryProvider"]:
    """
    从目录加载 Provider 实例。
    
    支持两种注册模式：
    1. register(ctx) 模式 - 插件导出 register 函数
    2. MemoryProvider 子类 - 直接实例化
    
    Args:
        name: Provider 名称
        path: Provider 目录路径（如果已知）
    
    Returns:
        MemoryProvider 实例，或 None
    """
    if path is None:
        path = find_provider_dir(name)
    if not path:
        return None
    
    # 确定模块名
    is_bundled = str(_PLUGINS_DIR) in str(path) or path.parent == _PLUGINS_DIR
    module_name = f"plugins.memory.{name}" if is_bundled else f"_agentz_user_memory.{name}"
    
    try:
        # 尝试 import
        if module_name in sys.modules:
            mod = sys.modules[module_name]
        else:
            spec = importlib.util.spec_from_file_location(
                module_name,
                path / "__init__.py"
            )
            if spec is None or spec.loader is None:
                return None
            mod = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = mod
            spec.loader.exec_module(mod)
        
        # 模式 1: register(ctx) 函数
        if hasattr(mod, "register"):
            ctx = PluginContext(name)
            mod.register(ctx)
            if ctx.provider:
                return ctx.provider
        
        # 模式 2: 查找 MemoryProvider 子类
        from agent.memory.memory_provider import MemoryProvider
        
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name, None)
            if (isinstance(attr, type) and 
                issubclass(attr, MemoryProvider) and 
                attr is not MemoryProvider):
                return attr()  # 实例化
        
        return None
        
    except Exception as e:
        logger.warning(f"Failed to load memory provider '{name}': {e}")
        return None


def load_memory_provider(name: str) -> Optional["MemoryProvider"]:
    """
    加载并返回指定名称的 MemoryProvider 实例。
    
    Args:
        name: Provider 名称
    
    Returns:
        MemoryProvider 实例，或 None
    """
    # 缓存检查
    if name in _loaded_providers:
        return _loaded_providers[name]
    
    path = find_provider_dir(name)
    if not path:
        logger.debug(f"Provider '{name}' not found")
        return None
    
    provider = _load_provider_from_dir(name, path)
    if provider:
        _loaded_providers[name] = provider
        logger.info(f"Loaded memory provider: {name}")
    
    return provider


def reload_memory_providers() -> None:
    """重新加载所有 Provider（清除缓存）"""
    global _discovered, _loaded_providers
    _discovered = None
    _loaded_providers = {}
    discover_memory_providers()


def is_provider_available(name: str) -> bool:
    """
    检查 Provider 是否已安装且可用。
    
    Args:
        name: Provider 名称
    
    Returns:
        True 如果 Provider 可用
    """
    provider = load_memory_provider(name)
    if not provider:
        return False
    try:
        return provider.is_available()
    except Exception:
        return False


# ============================================================================
# Provider Diagnostics (Provider 诊断)
# ============================================================================

def diagnose_provider(name: str, force_refresh: bool = False) -> ProviderDiagnostics:
    """
    对 Provider 进行全面诊断。
    
    诊断项目：
    1. 发现状态（是否找到）
    2. 可用性检查
    3. 加载测试
    4. 配置校验
    5. 工具发现
    
    Args:
        name: Provider 名称
        force_refresh: 强制刷新缓存
    
    Returns:
        ProviderDiagnostics 诊断结果
    """
    global _diagnostics_cache
    
    import time
    
    # 缓存检查
    if not force_refresh and name in _diagnostics_cache:
        cached = _diagnostics_cache[name]
        if cached.last_check and (time.time() - cached.last_check) < 60:
            return cached
    
    diagnostics = ProviderDiagnostics(
        name=name,
        status=ProviderStatus.NOT_FOUND,
        last_check=time.time(),
    )
    
    try:
        # 1. 发现检查
        path = find_provider_dir(name)
        if not path:
            diagnostics.status = ProviderStatus.NOT_FOUND
            diagnostics.error = f"Provider '{name}' not found in plugin directories"
            _diagnostics_cache[name] = diagnostics
            return diagnostics
        
        diagnostics.path = str(path)
        
        # 2. 加载 Provider
        provider = _load_provider_from_dir(name, path)
        if not provider:
            diagnostics.status = ProviderStatus.ERROR
            diagnostics.error = f"Failed to load Provider from {path}"
            diagnostics.error_type = "load_error"
            _diagnostics_cache[name] = diagnostics
            return diagnostics
        
        diagnostics.status = ProviderStatus.LOADED
        
        # 3. 可用性检查
        try:
            diagnostics.is_available = provider.is_available()
            if diagnostics.is_available:
                diagnostics.status = ProviderStatus.AVAILABLE
            else:
                diagnostics.status = ProviderStatus.FOUND_BUT_UNAVAILABLE
                diagnostics.warnings.append("Provider reported itself as unavailable")
        except Exception as e:
            diagnostics.status = ProviderStatus.FOUND_BUT_UNAVAILABLE
            diagnostics.error = str(e)
            diagnostics.error_type = "availability_check_failed"
        
        # 4. 工具发现
        try:
            for schema in provider.get_tool_schemas():
                tool_name = schema.get("name")
                if tool_name:
                    diagnostics.available_tools.append(tool_name)
        except Exception as e:
            diagnostics.warnings.append(f"Failed to get tool schemas: {e}")
        
        # 5. 配置模式发现
        try:
            diagnostics.config_schema = provider.get_config_schema()
        except Exception as e:
            diagnostics.warnings.append(f"Failed to get config schema: {e}")
        
        # 6. 警告检查
        _check_provider_warnings(provider, diagnostics)
        
    except Exception as e:
        diagnostics.status = ProviderStatus.ERROR
        diagnostics.error = str(e)
        diagnostics.error_type = type(e).__name__
    
    _diagnostics_cache[name] = diagnostics
    return diagnostics


def diagnose_all_providers(force_refresh: bool = False) -> Dict[str, ProviderDiagnostics]:
    """
    对所有发现的 Provider 进行诊断。
    
    Args:
        force_refresh: 强制刷新缓存
    
    Returns:
        Dict of name -> ProviderDiagnostics
    """
    results = {}
    
    # 内置 Provider
    results["builtin"] = ProviderDiagnostics(
        name="builtin",
        status=ProviderStatus.AVAILABLE,
        path="built-in",
        is_available=True,
        available_tools=["memory"],
        last_check=None,
    )
    
    # 发现所有插件 Provider
    for name, _, path in discover_memory_providers():
        results[name] = diagnose_provider(name, force_refresh=force_refresh)
    
    return results


def _check_provider_warnings(provider: "MemoryProvider", diagnostics: ProviderDiagnostics) -> None:
    """
    检查 Provider 潜在问题并生成警告。
    
    Args:
        provider: Provider 实例
        diagnostics: 诊断结果
    """
    from agent.memory.memory_provider import MemoryProvider
    
    # 检查 name 属性
    if not hasattr(provider, 'name') or not provider.name:
        diagnostics.warnings.append("Provider missing or empty 'name' property")
    
    # 检查必需的接口方法
    required_methods = ['is_available', 'initialize', 'get_tool_schemas', 'system_prompt_block']
    for method in required_methods:
        if not hasattr(provider, method):
            diagnostics.warnings.append(f"Provider missing required method: {method}")
    
    # 检查工具 schema 格式
    try:
        schemas = provider.get_tool_schemas()
        for schema in schemas:
            if not isinstance(schema, dict):
                diagnostics.warnings.append("Tool schema is not a dict")
                continue
            if 'name' not in schema:
                diagnostics.warnings.append("Tool schema missing 'name' field")
    except Exception as e:
        diagnostics.warnings.append(f"Error checking tool schemas: {e}")


# ============================================================================
# Provider Configuration Validation (Provider 配置校验)
# ============================================================================

def validate_provider_config(
    provider_name: str,
    config: Dict[str, Any],
    strict: bool = True,
) -> ProviderValidationResult:
    """
    校验 Provider 配置。
    
    检查：
    1. Provider 是否存在
    2. 配置字段是否完整
    3. 配置值是否有效
    4. 是否满足必需的环境要求
    
    Args:
        provider_name: Provider 名称
        config: 配置字典
        strict: 严格模式（缺少可选字段也报警）
    
    Returns:
        ProviderValidationResult 校验结果
    """
    result = ProviderValidationResult(provider_name=provider_name, is_valid=True)
    
    # 内置 Provider 不需要校验
    if provider_name == "builtin":
        return result
    
    # 1. 检查 Provider 是否存在
    provider = load_memory_provider(provider_name)
    if not provider:
        result.is_valid = False
        result.errors.append(f"Provider '{provider_name}' not found or failed to load")
        
        # 查找建议
        available = discover_memory_providers()
        if available:
            names = [n for n, _, _ in available]
            result.suggestions.append(f"Available providers: {', '.join(names)}")
        return result
    
    # 2. 获取配置模式
    try:
        schema = provider.get_config_schema()
    except Exception as e:
        result.warnings.append(f"Failed to get config schema: {e}")
        schema = []
    
    if not schema:
        # 无配置模式，任何配置都有效
        return result
    
    # 3. 校验必需字段
    required_fields = [f.get('key') for f in schema if f.get('required')]
    for field_name in required_fields:
        if field_name not in config or config.get(field_name) is None:
            result.is_valid = False
            result.errors.append(f"Missing required field: '{field_name}'")
            
            # 查找字段描述
            for f in schema:
                if f.get('key') == field_name:
                    desc = f.get('description', 'No description')
                    result.suggestions.append(f"'{field_name}': {desc}")
                    break
    
    # 4. 校验字段类型和值
    for field_def in schema:
        key = field_def.get('key')
        if key not in config:
            if not field_def.get('required') and strict:
                result.warnings.append(f"Optional field missing: '{key}'")
            continue
        
        value = config.get(key)
        
        # 类型校验
        if 'choices' in field_def:
            choices = field_def['choices']
            if value not in choices:
                result.is_valid = False
                result.errors.append(
                    f"Invalid value for '{key}': '{value}'. Must be one of: {choices}"
                )
        
        # URL 格式校验
        if field_def.get('url') and value:
            if not _is_valid_url(str(value)):
                result.errors.append(f"'{key}' is not a valid URL")
        
        # 布尔值校验
        if isinstance(value, str) and value.lower() in ('true', 'false'):
            result.warnings.append(f"'{key}' should be boolean, not string")
    
    # 5. 额外校验（Provider 特定）
    _validate_provider_specific(provider_name, config, result)
    
    return result


def _validate_provider_specific(
    provider_name: str,
    config: Dict[str, Any],
    result: ProviderValidationResult,
) -> None:
    """
    Provider 特定的校验逻辑。
    
    可以通过插件注册自定义校验器。
    """
    # Honcho 特定校验
    if provider_name == "honcho":
        if 'api_key' in config and config['api_key']:
            key = config['api_key']
            if len(key) < 20:
                result.warnings.append("API key appears to be too short")
            if key.startswith('sk-') or key.startswith('hk-'):
                pass  # 合理格式
            else:
                result.warnings.append("API key format not recognized")
    
    # Mem0 特定校验
    if provider_name == "mem0":
        if 'api_key' in config and not config['api_key']:
            result.errors.append("Mem0 requires an API key")
        if 'organization_id' not in config:
            result.warnings.append("Consider setting organization_id for better tracking")


def _is_valid_url(url: str) -> bool:
    """简单 URL 格式校验"""
    import re
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(url_pattern.match(url))


def validate_all_configs(configs: Dict[str, Dict[str, Any]]) -> Dict[str, ProviderValidationResult]:
    """
    批量校验多个 Provider 配置。
    
    Args:
        configs: Dict of provider_name -> config_dict
    
    Returns:
        Dict of provider_name -> ProviderValidationResult
    """
    results = {}
    for name, config in configs.items():
        results[name] = validate_provider_config(name, config)
    return results


# ============================================================================
# Provider Error Handler (Provider 错误处理)
# ============================================================================

class ProviderError(Exception):
    """Provider 相关错误基类"""
    
    def __init__(
        self,
        message: str,
        provider_name: str = "",
        error_type: str = "unknown",
        recoverable: bool = True,
        suggestion: str = "",
    ):
        super().__init__(message)
        self.provider_name = provider_name
        self.error_type = error_type
        self.recoverable = recoverable
        self.suggestion = suggestion


class ProviderNotFoundError(ProviderError):
    """Provider 未找到错误"""
    
    def __init__(self, provider_name: str, suggestion: str = ""):
        super().__init__(
            f"Memory provider '{provider_name}' not found",
            provider_name=provider_name,
            error_type="not_found",
            recoverable=False,
            suggestion=suggestion,
        )


class ProviderLoadError(ProviderError):
    """Provider 加载错误"""
    
    def __init__(self, provider_name: str, original_error: Exception):
        super().__init__(
            f"Failed to load memory provider '{provider_name}': {original_error}",
            provider_name=provider_name,
            error_type="load_error",
            recoverable=False,
            suggestion=f"Check if '{provider_name}' is properly installed",
        )


class ProviderUnavailableError(ProviderError):
    """Provider 不可用错误"""
    
    def __init__(self, provider_name: str, reason: str = ""):
        super().__init__(
            f"Memory provider '{provider_name}' is not available" + (f": {reason}" if reason else ""),
            provider_name=provider_name,
            error_type="unavailable",
            recoverable=True,
            suggestion="Check provider configuration and credentials",
        )


class ProviderConfigError(ProviderError):
    """Provider 配置错误"""
    
    def __init__(self, provider_name: str, errors: List[str]):
        error_msg = f"Configuration errors for '{provider_name}': " + "; ".join(errors)
        super().__init__(
            error_msg,
            provider_name=provider_name,
            error_type="config_invalid",
            recoverable=True,
            suggestion="Review configuration and fix errors",
        )


def handle_provider_error(
    error: Exception,
    provider_name: str = "",
    fallback: str = "builtin",
) -> Tuple[bool, Optional["MemoryProvider"], str]:
    """
    处理 Provider 错误，提供优雅降级。
    
    Args:
        error: 原始错误
        provider_name: Provider 名称
        fallback: 回退 Provider 名称
    
    Returns:
        Tuple of (success, fallback_provider, message)
    """
    from agent.memory.memory_provider import BuiltinMemoryProvider
    
    if isinstance(error, ProviderNotFoundError):
        logger.warning(f"Provider '{provider_name}' not found, falling back to builtin")
        builtin = BuiltinMemoryProvider()
        return True, builtin, f"Provider '{provider_name}' not found, using builtin"
    
    if isinstance(error, ProviderUnavailableError):
        logger.warning(f"Provider '{provider_name}' unavailable: {error}, falling back to builtin")
        builtin = BuiltinMemoryProvider()
        return True, builtin, f"Provider '{provider_name}' unavailable, using builtin"
    
    if isinstance(error, ProviderConfigError):
        logger.error(f"Provider '{provider_name}' configuration error: {error}")
        return False, None, str(error)
    
    if isinstance(error, ProviderLoadError):
        logger.error(f"Provider '{provider_name}' load error: {error}")
        return False, None, str(error)
    
    # 未知错误，尝试回退
    logger.error(f"Unexpected error with provider '{provider_name}': {error}")
    try:
        builtin = BuiltinMemoryProvider()
        return True, builtin, f"Unexpected error: {error}, using builtin"
    except Exception:
        return False, None, f"Critical error: {error}"


# ============================================================================
# Provider Health Check (Provider 健康检查)
# ============================================================================

def health_check_provider(name: str) -> Dict[str, Any]:
    """
    对 Provider 执行健康检查。
    
    Returns:
        Dict with health status and metrics
    """
    import time
    
    result = {
        "name": name,
        "healthy": False,
        "checks": {},
        "timestamp": time.time(),
    }
    
    try:
        # 加载检查
        provider = load_memory_provider(name)
        result["checks"]["load"] = {
            "passed": provider is not None,
            "error": None if provider else "Failed to load",
        }
        
        if not provider:
            return result
        
        # 可用性检查
        try:
            is_available = provider.is_available()
            result["checks"]["availability"] = {
                "passed": is_available,
                "error": None if is_available else "Provider reported unavailable",
            }
        except Exception as e:
            result["checks"]["availability"] = {
                "passed": False,
                "error": str(e),
            }
        
        # 工具检查
        try:
            schemas = provider.get_tool_schemas()
            result["checks"]["tools"] = {
                "passed": True,
                "tool_count": len(schemas),
                "tools": [s.get("name") for s in schemas if s.get("name")],
            }
        except Exception as e:
            result["checks"]["tools"] = {
                "passed": False,
                "error": str(e),
            }
        
        # 综合判断
        result["healthy"] = all(
            check.get("passed", False) for check in result["checks"].values()
        )
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


# ============================================================================
# CLI Integration (CLI 集成)
# ============================================================================

def discover_plugin_cli_commands(provider_name: Optional[str] = None) -> List[Dict]:
    """
    发现已安装插件的 CLI 命令。
    
    Args:
        provider_name: 只返回指定 Provider 的 CLI（如果为 None，返回所有）
    
    Returns:
        CLI 命令列表
    """
    commands = []
    providers = discover_memory_providers()
    
    for name, available, path in providers:
        if provider_name and name != provider_name:
            continue
        
        if not available:
            continue
        
        cli_file = Path(path) / "cli.py"
        if not cli_file.exists():
            continue
        
        try:
            # 轻量级导入
            spec = importlib.util.spec_from_file_location(
                f"_cli_{name}",
                cli_file
            )
            if spec and spec.loader:
                cli_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(cli_mod)
                
                register_cli = getattr(cli_mod, "register_cli", None)
                if register_cli and callable(register_cli):
                    cmd = register_cli()
                    if cmd:
                        commands.append({
                            "name": name,
                            "command": cmd
                        })
        except Exception as e:
            logger.debug(f"Failed to load CLI for {name}: {e}")
    
    return commands


# ============================================================================
# Provider Registry (Provider 注册表)
# ============================================================================

def get_active_provider_name() -> str:
    """获取当前活跃的 Provider 名称"""
    try:
        from common.config import settings
        return getattr(settings, "memory_provider", "builtin")
    except Exception:
        return "builtin"


def get_provider_choices() -> List[Dict]:
    """
    获取所有可用 Provider 的选择列表。
    
    Returns:
        List of {"name": str, "available": bool, "path": str}
    """
    choices = [
        {"name": "builtin", "available": True, "path": "built-in"}
    ]
    
    for name, available, path in discover_memory_providers():
        choices.append({
            "name": name,
            "available": available,
            "path": path
        })
    
    return choices


__all__ = [
    # Discovery
    "discover_memory_providers",
    "load_memory_provider",
    "find_provider_dir",
    "is_provider_available",
    "reload_memory_providers",
    # Diagnostics
    "diagnose_provider",
    "diagnose_all_providers",
    "health_check_provider",
    # Validation
    "validate_provider_config",
    "validate_all_configs",
    # Error Handling
    "ProviderError",
    "ProviderNotFoundError",
    "ProviderLoadError",
    "ProviderUnavailableError",
    "ProviderConfigError",
    "handle_provider_error",
    # Types
    "ProviderStatus",
    "ProviderDiagnostics",
    "ProviderValidationResult",
    "PluginContext",
    # CLI
    "discover_plugin_cli_commands",
    "get_active_provider_name",
    "get_provider_choices",
]
