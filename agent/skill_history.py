#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill History - 技能版本历史

提供技能版本控制功能：
- 记录技能变更历史
- 支持版本回滚
- 版本对比

🚪 Access - 📋 Skills - 版本历史
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from common.config import get_skills_dir, get_config_dir
from common.logging_manager import get_execution_logger

logger = get_execution_logger("SkillHistory")

# 历史记录目录
HISTORY_DIR = "skill_history"
MAX_HISTORY_PER_SKILL = 100  # 每个技能最多保留的历史记录数


@dataclass
class HistoryEntry:
    """历史记录条目"""
    version: str  # 版本号 (如 v1, v2, v3...)
    timestamp: str  # ISO 格式时间戳
    action: str  # 操作类型: create, edit, patch, delete
    content_hash: str  # 内容哈希
    diff_summary: str  # 变更摘要
    author: str = "agent"  # 作者
    message: str = ""  # 变更说明

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "action": self.action,
            "content_hash": self.content_hash,
            "diff_summary": self.diff_summary,
            "author": self.author,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> HistoryEntry:
        return cls(
            version=data.get("version", ""),
            timestamp=data.get("timestamp", ""),
            action=data.get("action", ""),
            content_hash=data.get("content_hash", ""),
            diff_summary=data.get("diff_summary", ""),
            author=data.get("author", "agent"),
            message=data.get("message", ""),
        )


@dataclass
class SkillSnapshot:
    """技能快照"""
    version: str
    timestamp: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "content": self.content,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SkillSnapshot:
        return cls(
            version=data.get("version", ""),
            timestamp=data.get("timestamp", ""),
            content=data.get("content", ""),
            metadata=data.get("metadata", {}),
        )


class SkillHistory:
    """
    技能版本历史管理器

    提供：
    - 自动记录变更历史
    - 版本快照保存
    - 版本对比
    - 版本回滚
    """

    def __init__(self):
        self._skills_dir = get_skills_dir()
        self._history_dir = get_config_dir() / HISTORY_DIR
        self._history_dir.mkdir(parents=True, exist_ok=True)

    def _get_history_file(self, skill_name: str) -> Path:
        """获取技能历史文件路径"""
        return self._history_dir / f"{skill_name}.json"

    def _get_snapshots_dir(self, skill_name: str) -> Path:
        """获取技能快照目录"""
        return self._history_dir / skill_name / "snapshots"

    def record_change(
        self,
        skill_name: str,
        action: str,
        content: str,
        message: str = "",
        author: str = "agent",
    ) -> Optional[HistoryEntry]:
        """
        记录技能变更

        Args:
            skill_name: 技能名称
            action: 操作类型
            content: 变更后的内容
            message: 变更说明
            author: 作者

        Returns:
            历史记录条目
        """
        try:
            history_file = self._get_history_file(skill_name)
            entries = self._load_history(skill_name)

            # 计算内容哈希
            content_hash = hashlib.sha256(content.encode()).hexdigest()

            # 生成版本号
            version = f"v{len(entries) + 1}"

            # 生成变更摘要
            diff_summary = self._generate_diff_summary(action, content)

            # 创建历史记录
            entry = HistoryEntry(
                version=version,
                timestamp=datetime.now(timezone.utc).isoformat(),
                action=action,
                content_hash=content_hash,
                diff_summary=diff_summary,
                author=author,
                message=message,
            )

            entries.append(entry)

            # 限制历史记录数量
            if len(entries) > MAX_HISTORY_PER_SKILL:
                entries = entries[-MAX_HISTORY_PER_SKILL:]

            # 保存历史
            self._save_history(skill_name, entries)

            # 保存快照
            self._save_snapshot(skill_name, version, content)

            logger.info(f"Recorded history for {skill_name}: {version} - {action}")
            return entry

        except Exception as e:
            logger.error(f"Failed to record history: {e}")
            return None

    def _generate_diff_summary(self, action: str, content: str) -> str:
        """生成变更摘要"""
        summaries = {
            "create": "创建技能",
            "edit": "编辑技能内容",
            "patch": "修补技能内容",
            "delete": "删除技能",
        }

        base = summaries.get(action, action)

        # 简单统计内容变化
        lines = content.split("\n")
        non_empty = [l for l in lines if l.strip()]

        if len(non_empty) > 0:
            return f"{base} ({len(non_empty)} 行)"
        return base

    def _load_history(self, skill_name: str) -> List[HistoryEntry]:
        """加载历史记录"""
        history_file = self._get_history_file(skill_name)

        if not history_file.exists():
            return []

        try:
            data = json.loads(history_file.read_text(encoding="utf-8"))
            return [HistoryEntry.from_dict(e) for e in data]
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
            return []

    def _save_history(self, skill_name: str, entries: List[HistoryEntry]) -> None:
        """保存历史记录"""
        history_file = self._get_history_file(skill_name)
        data = [e.to_dict() for e in entries]
        history_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _save_snapshot(self, skill_name: str, version: str, content: str) -> None:
        """保存快照"""
        snapshots_dir = self._get_snapshots_dir(skill_name)
        snapshots_dir.mkdir(parents=True, exist_ok=True)

        snapshot_file = snapshots_dir / f"{version}.json"

        snapshot = SkillSnapshot(
            version=version,
            timestamp=datetime.now(timezone.utc).isoformat(),
            content=content,
        )

        snapshot_file.write_text(json.dumps(snapshot.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

        # 清理旧快照，保留最近10个
        self._cleanup_old_snapshots(skill_name)

    def _cleanup_old_snapshots(self, skill_name: str) -> None:
        """清理旧快照"""
        snapshots_dir = self._get_snapshots_dir(skill_name)

        if not snapshots_dir.exists():
            return

        snapshots = list(snapshots_dir.glob("*.json"))
        snapshots.sort(key=lambda p: p.name)

        # 只保留最近10个
        for old_snapshot in snapshots[:-10]:
            old_snapshot.unlink()

    def get_history(self, skill_name: str) -> List[HistoryEntry]:
        """
        获取技能历史记录

        Args:
            skill_name: 技能名称

        Returns:
            历史记录列表
        """
        return self._load_history(skill_name)

    def get_snapshot(self, skill_name: str, version: str) -> Optional[SkillSnapshot]:
        """
        获取技能快照

        Args:
            skill_name: 技能名称
            version: 版本号 (如 v1, v2)

        Returns:
            快照内容
        """
        snapshot_file = self._get_snapshots_dir(skill_name) / f"{version}.json"

        if not snapshot_file.exists():
            return None

        try:
            data = json.loads(snapshot_file.read_text(encoding="utf-8"))
            return SkillSnapshot.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load snapshot: {e}")
            return None

    def diff(
        self,
        skill_name: str,
        version1: str,
        version2: str = None,
    ) -> Dict[str, Any]:
        """
        对比两个版本的差异

        Args:
            skill_name: 技能名称
            version1: 第一个版本
            version2: 第二个版本，如果为 None 则与当前版本对比

        Returns:
            差异信息
        """
        # 获取第一个版本
        snapshot1 = self.get_snapshot(skill_name, version1)
        if not snapshot1:
            return {"error": f"Version not found: {version1}"}

        # 获取第二个版本
        if version2:
            snapshot2 = self.get_snapshot(skill_name, version2)
        else:
            # 与当前版本对比
            skill_file = self._skills_dir / skill_name / "SKILL.md"
            if not skill_file.exists():
                return {"error": "Current version not found"}
            current_content = skill_file.read_text(encoding="utf-8")
            snapshot2 = SkillSnapshot(
                version="current",
                timestamp=datetime.now(timezone.utc).isoformat(),
                content=current_content,
            )

        if not snapshot2:
            return {"error": f"Version not found: {version2}"}

        # 计算差异
        lines1 = snapshot1.content.split("\n")
        lines2 = snapshot2.content.split("\n")

        # 简单差异计算
        added = []
        removed = []

        # 逐行比较
        i, j = 0, 0
        while i < len(lines1) or j < len(lines2):
            if i >= len(lines1):
                added.append(j + 1)
            elif j >= len(lines2):
                removed.append(i + 1)
            elif lines1[i] != lines2[j]:
                # 简单算法：假设后面的行会重新匹配
                # 简化处理
                if lines1[i] in lines2[j:]:
                    added.append(j + 1)
                    j += 1
                elif lines2[j] in lines1[i:]:
                    removed.append(i + 1)
                    i += 1
                else:
                    removed.append(i + 1)
                    added.append(j + 1)
                    i += 1
                    j += 1
            else:
                i += 1
                j += 1

        return {
            "skill_name": skill_name,
            "version1": snapshot1.version,
            "version2": snapshot2.version,
            "timestamp1": snapshot1.timestamp,
            "timestamp2": snapshot2.timestamp,
            "lines_added": len(added),
            "lines_removed": len(removed),
            "added_lines": added[:20],  # 只显示前20行
            "removed_lines": removed[:20],
        }

    def rollback(self, skill_name: str, version: str) -> Dict[str, Any]:
        """
        回滚到指定版本

        Args:
            skill_name: 技能名称
            version: 版本号

        Returns:
            回滚结果
        """
        result = {"success": False, "message": ""}

        # 获取快照
        snapshot = self.get_snapshot(skill_name, version)
        if not snapshot:
            result["message"] = f"Version not found: {version}"
            return result

        # 保存当前版本作为新快照（回滚前的备份）
        skill_file = self._skills_dir / skill_name / "SKILL.md"
        if skill_file.exists():
            current_content = skill_file.read_text(encoding="utf-8")
            entries = self._load_history(skill_name)
            backup_version = f"v{len(entries) + 1}" if entries else "v1"
            self._save_snapshot(skill_name, backup_version, current_content)

        # 写入回滚版本
        try:
            skill_file.parent.mkdir(parents=True, exist_ok=True)
            skill_file.write_text(snapshot.content, encoding="utf-8")

            # 记录历史
            self.record_change(
                skill_name=skill_name,
                action="rollback",
                content=snapshot.content,
                message=f"回滚到版本 {version}",
            )

            result["success"] = True
            result["message"] = f"已回滚到版本 {version}"
            logger.info(f"Rolled back {skill_name} to {version}")

        except Exception as e:
            result["message"] = f"回滚失败: {e}"
            logger.error(f"Rollback failed: {e}")

        return result

    def get_version_list(self, skill_name: str) -> List[Dict[str, Any]]:
        """
        获取版本列表

        Args:
            skill_name: 技能名称

        Returns:
            版本列表
        """
        entries = self._load_history(skill_name)

        return [
            {
                "version": e.version,
                "timestamp": e.timestamp,
                "action": e.action,
                "message": e.message,
                "author": e.author,
                "content_hash": e.content_hash,
            }
            for e in entries
        ]

    def delete_history(self, skill_name: str) -> bool:
        """
        删除技能历史

        Args:
            skill_name: 技能名称

        Returns:
            是否成功
        """
        try:
            # 删除历史文件
            history_file = self._get_history_file(skill_name)
            if history_file.exists():
                history_file.unlink()

            # 删除快照目录
            snapshots_dir = self._get_snapshots_dir(skill_name)
            if snapshots_dir.exists():
                import shutil
                shutil.rmtree(snapshots_dir)

            logger.info(f"Deleted history for {skill_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete history: {e}")
            return False


# 全局实例
_history: Optional[SkillHistory] = None


def get_history() -> SkillHistory:
    """获取全局历史管理器实例"""
    global _history
    if _history is None:
        _history = SkillHistory()
    return _history


# 便捷函数

def record_skill_change(
    skill_name: str,
    action: str,
    content: str,
    message: str = "",
) -> Optional[HistoryEntry]:
    """记录技能变更"""
    return get_history().record_change(skill_name, action, content, message)


def get_skill_history(skill_name: str) -> List[HistoryEntry]:
    """获取技能历史"""
    return get_history().get_history(skill_name)


def rollback_skill(skill_name: str, version: str) -> Dict[str, Any]:
    """回滚技能"""
    return get_history().rollback(skill_name, version)


def diff_skill_versions(skill_name: str, v1: str, v2: str = None) -> Dict[str, Any]:
    """对比技能版本"""
    return get_history().diff(skill_name, v1, v2)


if __name__ == "__main__":
    history = get_history()

    # 测试
    print("Skill History Manager")
    print("Use record_change() to record changes")
    print("Use get_history() to get change history")
    print("Use diff() to compare versions")
    print("Use rollback() to revert to a previous version")
