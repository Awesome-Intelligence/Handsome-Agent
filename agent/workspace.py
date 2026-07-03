#!/usr/bin/env python3
"""
Workspace Management Module

参考 OpenClaw 的 workspace 实现，提供配置文件的模板复制、加载和管理功能。

架构：
- 模板目录 (agent/templates/) - 存放默认配置模板
- 用户工作空间 (~/.handsome_agent/) - 用户实际修改的配置

配置文件：
- agent.md / SOUL.md - Agent 身份和性格
- user.md / USER.md - 用户画像
- memory.md / MEMORY.md - 记忆系统
- heartbeat.md / HEARTBEAT.md - 状态监测
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from common.logging_manager import get_decision_logger

logger = get_decision_logger("WorkspaceManager")

# 默认配置
DEFAULT_WORKSPACE_DIR = Path.home() / ".handsome_agent"
DEFAULT_TEMPLATE_DIR = Path(__file__).parent.parent / "agent" / "templates"

# 配置文件名映射
BOOTSTRAP_FILES = {
    "agent": "agent.md",
    "user": "user.md",
    "memory": "memory.md",
    "tools": "tools.md",
}

# 可选配置文件（首次启动时可跳过）
OPTIONAL_FILES = {"user"}

# 状态文件
STATE_FILE = ".workspace_state.json"
STATE_VERSION = 1


class WorkspaceManager:
    """工作空间管理器"""

    def __init__(self, workspace_dir: Optional[Path] = None):
        self.workspace_dir = workspace_dir or DEFAULT_WORKSPACE_DIR
        self.template_dir = DEFAULT_TEMPLATE_DIR
        self.state_path = self.workspace_dir / STATE_FILE
        self.logs_dir = self.workspace_dir / "logs"
        self.sessions_dir = self.workspace_dir / "sessions"
        self._state: Dict[str, Any] = {}
        self._file_cache: Dict[str, str] = {}

    def _load_state(self) -> Dict[str, Any]:
        """加载工作空间状态"""
        if self._state:
            return self._state

        if self.state_path.exists():
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    self._state = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load workspace state: {e}")
                self._state = {}
        else:
            self._state = {"version": STATE_VERSION}

        return self._state

    def _save_state(self):
        """保存工作空间状态"""
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save workspace state: {e}")

    def _load_template(self, filename: str) -> str:
        """加载模板文件内容"""
        template_path = self.template_dir / filename
        if template_path.exists():
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def _write_file_if_missing(self, filepath: Path, content: str) -> bool:
        """仅在文件不存在时写入"""
        if filepath.exists():
            return False
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True

    def is_workspace_setup_completed(self) -> bool:
        """检查工作空间是否已完成设置"""
        state = self._load_state()
        return state.get("setup_completed_at") is not None

    def _is_file_modified_from_template(self, filename: str) -> bool:
        """检查文件是否已从模板修改"""
        template_path = self.template_dir / filename
        workspace_path = self.workspace_dir / filename

        if not workspace_path.exists():
            return False
        if not template_path.exists():
            return True

        try:
            with open(template_path, "r", encoding="utf-8") as f:
                template_content = f.read()
            with open(workspace_path, "r", encoding="utf-8") as f:
                workspace_content = f.read()
            return template_content != workspace_content
        except Exception as e:
            logger.error(f"Failed to compare file with template: {e}")
            return False

    def ensure_workspace(self, skip_optional: bool = False) -> bool:
        """
        确保工作空间存在并包含必要的配置文件

        Args:
            skip_optional: 是否跳过可选文件

        Returns:
            True 如果工作空间已设置完成，False 表示需要引导
        """
        state = self._load_state()

        # 如果已经设置完成，直接返回
        if state.get("setup_completed_at"):
            return True

        # 创建工作空间目录
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # 复制模板文件到工作空间
        created_files = []
        for key, filename in BOOTSTRAP_FILES.items():
            # 跳过可选文件
            if skip_optional and key in OPTIONAL_FILES:
                continue

            template_content = self._load_template(filename)
            if template_content:
                workspace_path = self.workspace_dir / filename
                if self._write_file_if_missing(workspace_path, template_content):
                    created_files.append(filename)
                    logger.info(f"Created workspace file: {filename}")

        # 更新状态
        if created_files:
            state["bootstrap_seeded_at"] = self._get_timestamp()
            self._save_state()

        # 检查是否需要引导
        if not state.get("bootstrap_seeded_at"):
            # 检查是否已有用户修改的文件
            has_user_content = any(
                self._is_file_modified_from_template(f)
                for f in BOOTSTRAP_FILES.values()
            )
            if has_user_content:
                state["setup_completed_at"] = self._get_timestamp()
                self._save_state()
                return True

        return False

    def load_workspace_file(self, filename: str) -> Optional[str]:
        """
        从工作空间加载配置文件

        Args:
            filename: 文件名

        Returns:
            文件内容，如果文件不存在返回 None
        """
        # 先检查缓存
        cache_key = str(self.workspace_dir / filename)
        if cache_key in self._file_cache:
            return self._file_cache[cache_key]

        filepath = self.workspace_dir / filename
        if filepath.exists():
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    self._file_cache[cache_key] = content
                    return content
            except Exception as e:
                logger.error(f"Failed to load workspace file {filename}: {e}")
        return None

    def save_workspace_file(self, filename: str, content: str):
        """
        保存配置文件到工作空间

        Args:
            filename: 文件名
            content: 文件内容
        """
        filepath = self.workspace_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        # 更新缓存
        cache_key = str(filepath)
        self._file_cache[cache_key] = content
        logger.info(f"Saved workspace file: {filename}")

    def get_workspace_files(self) -> Dict[str, str]:
        """获取所有工作空间配置文件"""
        result = {}
        for key, filename in BOOTSTRAP_FILES.items():
            content = self.load_workspace_file(filename)
            if content:
                result[key] = content
        return result

    def mark_setup_complete(self):
        """标记工作空间设置完成"""
        state = self._load_state()
        state["setup_completed_at"] = self._get_timestamp()
        self._save_state()
        logger.info("Workspace setup completed")

    def _get_timestamp(self) -> str:
        """获取当前时间戳（ISO 格式）"""
        from datetime import datetime

        return datetime.now().isoformat()

    def clear_cache(self):
        """清除文件缓存"""
        self._file_cache.clear()


# 全局实例
_workspace_manager = None


def get_workspace_manager() -> WorkspaceManager:
    """获取全局工作空间管理器实例"""
    global _workspace_manager
    if _workspace_manager is None:
        _workspace_manager = WorkspaceManager()
    return _workspace_manager


def ensure_workspace() -> bool:
    """确保工作空间存在（便捷函数）"""
    return get_workspace_manager().ensure_workspace()


def load_workspace_file(filename: str) -> Optional[str]:
    """加载工作空间文件（便捷函数）"""
    return get_workspace_manager().load_workspace_file(filename)


def save_workspace_file(filename: str, content: str):
    """保存工作空间文件（便捷函数）"""
    get_workspace_manager().save_workspace_file(filename, content)