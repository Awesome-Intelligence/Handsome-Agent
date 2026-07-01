#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill Preprocessing - 技能内容预处理

在技能加载时执行预处理：
1. 内置变量: {{SKILL_DIR}}, {{CWD}}, {{HOME}}, {{USER}}, {{DATE}}
2. 环境变量: ${VAR_NAME}
3. 配置变量: ${config:key.path}
4. 内联 Shell: `!command`
"""

import os
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, Optional, Tuple, List

from common.logging_manager import get_execution_logger

# 内联 Shell 专用日志器
_inline_shell_logger = get_execution_logger("InlineShell", sublayer="shell_exec")

# 内置变量模式
BUILTIN_VAR_PATTERN = re.compile(r"\{\{(\w+)\}\}")
# 环境变量模式
ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
# 配置变量模式
CONFIG_VAR_PATTERN = re.compile(r"\$\{config:([^}]+)\}")
# 内联 Shell 模式
INLINE_SHELL_PATTERN = re.compile(r"`!([^\n]+?)`")


@dataclass
class ShellResult:
    """Shell 执行结果"""
    success: bool
    stdout: str
    stderr: str
    returncode: int
    execution_time: float


class InlineShellExecutor:
    """内联 Shell 执行器

    解析 SKILL.md 内容中的 `!command` 格式并在技能目录下执行
    """

    # 危险命令模式
    DANGEROUS_PATTERNS: List[re.Pattern] = [
        re.compile(r'rm\s+-rf\s+/', re.IGNORECASE),
        re.compile(r'rm\s+-rf\s+\*'),
        re.compile(r'format\s+[a-z]:', re.IGNORECASE),
        re.compile(r'del\s+/[fqs]', re.IGNORECASE),
        re.compile(r'shutdown', re.IGNORECASE),
        re.compile(r'reboot', re.IGNORECASE),
        re.compile(r'curl\s+.*\|\s*sh', re.IGNORECASE),
        re.compile(r'wget\s+.*\|\s*sh', re.IGNORECASE),
    ]

    # 允许的命令白名单（可选，用于严格模式）
    ALLOWED_COMMANDS: List[str] = [
        'echo', 'cat', 'ls', 'dir', 'pwd', 'cd', 'mkdir', 'cp', 'mv',
        'python', 'python3', 'pip', 'node', 'npm', 'git', 'type', 'find',
    ]

    # 命令替换正则：`!command`
    COMMAND_PATTERN: re.Pattern = re.compile(r'`!([^\n]+?)`')

    def __init__(
        self,
        timeout: int = 30,
        max_output: int = 10240,
        use_whitelist: bool = False,
    ) -> None:
        self.timeout = timeout
        self.max_output = max_output
        self.use_whitelist = use_whitelist

    def parse_and_execute(
        self,
        content: str,
        skill_dir: Path,
    ) -> Tuple[str, List[str]]:
        """解析内容中的内联 Shell 并执行"""
        errors: List[str] = []

        def replace_command(match: re.Match) -> str:
            command = match.group(1).strip()
            _inline_shell_logger.debug(f"Found inline command: {command[:50]}")

            is_safe, error = self._check_safety(command)
            if not is_safe:
                _inline_shell_logger.warning(f"Blocked dangerous command: {command[:50]}")
                errors.append(error)
                return f"[BLOCKED: {error}]"

            result = self._execute(command, skill_dir)

            if result.success:
                _inline_shell_logger.debug(f"Command executed in {result.execution_time:.2f}s")
                return result.stdout.strip()
            else:
                error_msg = f"Command failed: {command[:50]}"
                _inline_shell_logger.warning(error_msg)
                errors.append(error_msg)
                return f"[ERROR: {result.stderr or 'command failed'}]"

        processed = self.COMMAND_PATTERN.sub(replace_command, content)
        return processed, errors

    def _check_safety(self, command: str) -> Tuple[bool, Optional[str]]:
        """检查命令安全性"""
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern.search(command):
                return False, f"Dangerous command detected: {command[:50]}"

        if len(command) > 1000:
            return False, "Command too long (>1000 chars)"

        if '|' in command or '&' in command or ';' in command:
            parts = command.split('|')
            if len(parts) > 3:
                return False, "Too many pipe operations (>3)"

        if self.use_whitelist:
            first_word = command.split()[0] if command.split() else ""
            if first_word not in self.ALLOWED_COMMANDS:
                return False, f"Command not in whitelist: {first_word}"

        return True, None

    def _execute(self, command: str, cwd: Path) -> ShellResult:
        """执行命令"""
        start_time = time.time()

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            stdout = result.stdout[:self.max_output]
            if len(result.stdout) > self.max_output:
                stdout += "\n[Output truncated...]"

            stderr = result.stderr[:self.max_output] if result.stderr else ""

            return ShellResult(
                success=result.returncode == 0,
                stdout=stdout,
                stderr=stderr,
                returncode=result.returncode,
                execution_time=time.time() - start_time,
            )

        except subprocess.TimeoutExpired:
            return ShellResult(
                success=False,
                stdout="",
                stderr=f"Command timeout after {self.timeout}s",
                returncode=-1,
                execution_time=self.timeout,
            )
        except Exception as e:
            return ShellResult(
                success=False,
                stdout="",
                stderr=str(e),
                returncode=-1,
                execution_time=time.time() - start_time,
            )

    def validate_command(self, command: str) -> Tuple[bool, Optional[str]]:
        """验证命令安全性（公开方法，供外部调用）"""
        return self._check_safety(command)


def preprocess_skill_content(
    content: str,
    skill_dir: Optional[Path] = None,
    session_id: Optional[str] = None,
    enable_inline_shell: bool = True,
) -> Tuple[str, List[str]]:
    """预处理技能内容，替换模板变量和执行内联 Shell
    
    Args:
        content: 原始技能内容
        skill_dir: 技能目录路径
        session_id: 会话 ID
        enable_inline_shell: 是否启用内联 Shell 执行
    
    Returns:
        (预处理后的内容, 警告/错误列表)
    """
    if not content:
        return content, []
    
    warnings: List[str] = []
    result = content
    
    # 1. 内置变量替换
    result = _substitute_builtin_vars(result, skill_dir, session_id)
    
    # 2. 环境变量替换
    result = _substitute_env_vars(result)
    
    # 3. 配置文件变量替换
    result = _substitute_config_vars(result)
    
    # 4. 内联 Shell 执行
    if enable_inline_shell:
        result, shell_warnings = _execute_inline_shell(result, skill_dir)
        warnings.extend(shell_warnings)
    
    return result, warnings


def substitute_template_vars(content: str, skill_dir: Optional[Path] = None) -> str:
    """纯变量替换（内置 + 环境变量，不执行 shell）

    Args:
        content: 原始内容
        skill_dir: 技能目录路径

    Returns:
        替换后的内容
    """
    if not content:
        return content

    result = _substitute_builtin_vars(content, skill_dir, session_id=None)
    result = _substitute_env_vars(result)
    result = _substitute_config_vars(result)
    return result


def _substitute_builtin_vars(
    content: str,
    skill_dir: Optional[Path],
    session_id: Optional[str],
) -> str:
    """替换内置变量"""
    replacements = {
        "SKILL_DIR": str(skill_dir) if skill_dir else "",
        "CWD": os.getcwd(),
        "HOME": os.path.expanduser("~"),
        "USER": os.getenv("USER") or os.getenv("USERNAME") or "user",
        "DATE": date.today().isoformat(),
        "SESSION_ID": session_id or "unknown",
    }
    
    def replace_builtin(match):
        var_name = match.group(1)
        return replacements.get(var_name, match.group(0))
    
    return BUILTIN_VAR_PATTERN.sub(replace_builtin, content)


def _substitute_env_vars(content: str) -> str:
    """替换环境变量 ${VAR_NAME}"""
    def replace_env_var(match):
        var_name = match.group(1)
        value = os.getenv(var_name)
        if value is not None:
            return value
        return match.group(0)  # 保持原样如果未找到
    
    return ENV_VAR_PATTERN.sub(replace_env_var, content)


def _substitute_config_vars(content: str) -> str:
    """替换配置变量 ${config:key.path}"""
    def replace_config_var(match):
        key = match.group(1)
        try:
            from common.config import get_config_value
            value = get_config_value(key)
            if value is not None:
                return str(value)
        except Exception:
            pass
        return match.group(0)  # 保持原样如果未找到
    
    return CONFIG_VAR_PATTERN.sub(replace_config_var, content)


def _execute_inline_shell(content: str, skill_dir: Optional[Path]) -> Tuple[str, List[str]]:
    """执行内联 Shell 命令"""
    warnings: List[str] = []
    
    if not skill_dir:
        warnings.append("No skill_dir provided, skipping inline shell execution")
        return content, warnings
    
    try:
        executor = InlineShellExecutor()
        processed, errors = executor.parse_and_execute(content, skill_dir)
        warnings.extend(errors)
        return processed, warnings
    except Exception as e:
        warnings.append(f"Inline shell execution failed: {e}")
        return content, warnings
