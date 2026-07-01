#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技能 Hub - 统一的技能搜索和安装入口

整合所有技能来源，提供统一的搜索和安装接口。

🚪 Access - 📋 Skills - Hub 管理
"""

import asyncio
import logging
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass, field

from common.logging_manager import get_decision_logger

logger = get_decision_logger("SkillHub")

# 尝试导入来源适配器
try:
    from agent.skill_sources import (
        SourceRouter,
        create_default_router,
        SourceResult,
        SourceSkillInfo,
        append_audit_log,
    )
    SOURCES_AVAILABLE = True
except ImportError:
    SOURCES_AVAILABLE = False
    logger.warning("Skill sources module not available")

# 尝试导入版本锁定
try:
    from cli.config.lock_file import HubLockFile, get_lock_file
    LOCK_FILE_AVAILABLE = True
except ImportError:
    LOCK_FILE_AVAILABLE = False


@dataclass
class InstallProgress:
    """安装进度"""
    stage: str  # "downloading", "scanning", "installing", "done"
    progress: float  # 0.0 - 1.0
    message: str = ""


@dataclass
class InstallResult:
    """安装结果"""
    success: bool
    skill_name: str
    path: Optional[str] = None
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class SkillHub:
    """技能 Hub - 统一的技能管理入口"""
    
    def __init__(
        self,
        skills_dir: Optional[Path] = None,
        quarantine_dir: Optional[Path] = None,
    ):
        """初始化 SkillHub
        
        Args:
            skills_dir: 技能安装目录
            quarantine_dir: 隔离扫描目录
        """
        if skills_dir is None:
            from common.config import get_skills_dir
            skills_dir = get_skills_dir()
        
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        
        # 隔离目录用于安全扫描
        if quarantine_dir is None:
            quarantine_dir = self.skills_dir.parent / ".quarantine"
        self.quarantine_dir = Path(quarantine_dir)
        
        # 来源路由器
        self.router: Optional[SourceRouter] = None
        if SOURCES_AVAILABLE:
            self.router = create_default_router()
        
        # 版本锁定
        self.lock_file: Optional[HubLockFile] = None
        if LOCK_FILE_AVAILABLE:
            self.lock_file = get_lock_file(self.skills_dir)
    
    async def search(
        self,
        query: str,
        sources: Optional[List[str]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """搜索技能
        
        Args:
            query: 搜索关键词
            sources: 要搜索的来源列表，None 表示所有来源
        
        Returns:
            {source_name: [skill_metadata, ...]}
        """
        if not SOURCES_AVAILABLE or not self.router:
            return {}
        
        try:
            results = await self.router.search(query)
            
            # 过滤来源
            if sources:
                results = {
                    k: v for k, v in results.items()
                    if k in sources
                }
            
            return {
                source: [self._metadata_to_dict(m) for m in skills]
                for source, skills in results.items()
            }
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {}
    
    async def unified_search(self, query: str) -> List[Dict[str, Any]]:
        """统一搜索（合并所有来源结果）
        
        Args:
            query: 搜索关键词
        
        Returns:
            [skill_metadata, ...]
        """
        if not SOURCES_AVAILABLE or not self.router:
            return []
        
        try:
            results = await self.router.unified_search(query)
            return [self._metadata_to_dict(m) for m in results]
        except Exception as e:
            logger.error(f"Unified search failed: {e}")
            return []
    
    async def install(
        self,
        skill_ref: str,
        progress_callback: Optional[Callable[[InstallProgress], None]] = None,
        force: bool = False,
    ) -> InstallResult:
        """安装技能
        
        Args:
            skill_ref: 技能引用（如 github:owner/repo 或 URL）
            progress_callback: 进度回调函数
            force: 是否强制覆盖已锁定的版本
        
        Returns:
            InstallResult: 安装结果
        """
        if not SOURCES_AVAILABLE or not self.router:
            return InstallResult(
                success=False,
                skill_name="",
                error="Skill sources not available",
            )
        
        skill_name = self._extract_skill_name(skill_ref)
        
        # 检查版本锁定
        if self.lock_file and not force:
            if self.lock_file.check_conflict(skill_name, "latest"):
                return InstallResult(
                    success=False,
                    skill_name=skill_name,
                    error=f"Skill '{skill_name}' is locked. Use --force to override.",
                )
        
        # 报告进度：下载中
        if progress_callback:
            progress_callback(InstallProgress(
                stage="downloading",
                progress=0.1,
                message=f"Downloading {skill_name}...",
            ))
        
        # 执行安装
        result = await self.router.install(skill_ref, self.skills_dir)
        
        if not result.success:
            return InstallResult(
                success=False,
                skill_name=skill_name,
                error=result.error,
            )
        
        # 报告进度：扫描中
        if progress_callback:
            progress_callback(InstallProgress(
                stage="scanning",
                progress=0.5,
                message="Scanning for security issues...",
            ))
        
        # 安全扫描（简化版：检查危险模式）
        skill_path = result.metadata.get('path')
        warnings: List[str] = []
        if skill_path:
            is_safe, warnings = await self._scan_skill(Path(skill_path))
            if not is_safe:
                # 隔离危险技能
                await self._quarantine_skill(Path(skill_path))
                return InstallResult(
                    success=False,
                    skill_name=skill_name,
                    error=f"Security scan failed: {warnings[0] if warnings else 'unknown'}",
                    warnings=warnings,
                )
        
        # 报告进度：安装完成
        if progress_callback:
            progress_callback(InstallProgress(
                stage="done",
                progress=1.0,
                message=f"Installed {skill_name}",
            ))
        
        # 更新锁文件
        if self.lock_file:
            self.lock_file.add(
                skill_name=skill_name,
                version="latest",
                source=result.source_name,
                source_ref=skill_ref,
            )

        # 记录审计日志
        if SOURCES_AVAILABLE:
            scan_verdict = "clean" if not warnings else "warn"
            append_audit_log(
                action="INSTALL",
                skill_name=skill_name,
                source=result.source_name,
                trust_level="community",
                verdict=scan_verdict,
                extra=skill_ref,
            )

        return InstallResult(
            success=True,
            skill_name=skill_name,
            path=skill_path,
            warnings=warnings if skill_path else [],
        )
    
    async def _scan_skill(self, skill_path: Path) -> tuple:
        """扫描技能安全性

        使用统一的 skills_guard.scan_skill() 进行完整的安全扫描。

        Returns:
            (is_safe, warnings)
        """
        try:
            from tools.skills_guard import scan_skill, should_allow_install, format_scan_report

            # 使用统一的扫描器
            result = scan_skill(skill_path, source="hub-install")
            allowed, reason = should_allow_install(result)

            if allowed is False:
                return False, [format_scan_report(result)]
            elif allowed is None:
                # 需要确认，视为警告
                return True, [f"Warning: {reason}"]
            else:
                # 允许，检查是否有警告
                warnings = []
                if result.findings:
                    for f in result.findings[:5]:  # 最多5条警告
                        warnings.append(f"{f.severity}: {f.description} in {f.file}")
                return True, warnings

        except ImportError:
            logger.warning("skills_guard not available, skipping security scan")
            return True, []
        except Exception as e:
            logger.error(f"Security scan failed: {e}")
            return True, [f"Scan error: {e}"]
    
    async def _quarantine_skill(self, skill_path: Path):
        """隔离危险技能"""
        try:
            self.quarantine_dir.mkdir(parents=True, exist_ok=True)
            
            quarantine_path = self.quarantine_dir / skill_path.name
            if quarantine_path.exists():
                shutil.rmtree(quarantine_path)
            
            shutil.move(str(skill_path), str(quarantine_path))
            logger.warning(f"Quarantined dangerous skill: {skill_path.name}")
        except Exception as e:
            logger.error(f"Failed to quarantine skill: {e}")
    
    def _extract_skill_name(self, ref: str) -> str:
        """从引用中提取技能名称"""
        if ref.startswith('github:'):
            parts = ref.split('/')
            return parts[-1].split(':')[0]
        elif ref.startswith('http'):
            from urllib.parse import urlparse, unquote
            path = urlparse(ref).path
            name = unquote(path.split('/')[-1])
            return name.rsplit('.', 1)[0] if '.' in name else name
        return ref
    
    def _metadata_to_dict(self, metadata: 'SourceSkillInfo') -> Dict[str, Any]:
        """将 SourceSkillInfo 转换为字典"""
        return {
            'name': metadata.name,
            'description': metadata.description,
            'author': metadata.author,
            'version': metadata.version,
            'source': metadata.source,
            'url': metadata.url,
            'tags': metadata.tags,
        }
    
    def list_installed(self) -> List[Dict[str, Any]]:
        """列出已安装的技能"""
        if not self.lock_file:
            return []
        
        installed = []
        for skill_name, entry in self.lock_file.get_all().items():
            installed.append({
                'name': entry.skill_name,
                'version': entry.version,
                'source': entry.source,
                'installed_at': entry.installed_at,
            })
        
        return installed
    
    def uninstall(self, skill_name: str) -> bool:
        """卸载技能"""
        skill_path = self.skills_dir / skill_name

        if not skill_path.exists():
            logger.warning(f"Skill not found: {skill_name}")
            return False

        # 获取技能来源信息
        source = "unknown"
        if self.lock_file:
            entry = self.lock_file.get(skill_name)
            if entry:
                source = entry.source

        try:
            shutil.rmtree(skill_path)

            if self.lock_file:
                self.lock_file.remove(skill_name)

            # 记录审计日志
            if SOURCES_AVAILABLE:
                append_audit_log(
                    action="UNINSTALL",
                    skill_name=skill_name,
                    source=source,
                    trust_level="community",
                    verdict="n/a",
                    extra="user_request",
                )

            logger.info(f"Uninstalled skill: {skill_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to uninstall skill: {e}")
            return False


# 便捷函数
_hub_instance: Optional[SkillHub] = None


def get_skill_hub() -> SkillHub:
    """获取全局 SkillHub 实例"""
    global _hub_instance
    if _hub_instance is None:
        _hub_instance = SkillHub()
    return _hub_instance
