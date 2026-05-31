"""
自我进化集成管理器

整合所有自我进化组件:
- SkillTelemetry: 技能使用追踪
- SkillLifecycleManager: 技能生命周期管理
- EnhancedCurator: 自动审查和技能合成
- SkillMerger: 技能合并

为 AgentLoop 提供统一的自我进化能力
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Callable
from pathlib import Path
import asyncio
import logging


logger = logging.getLogger(__name__)


@dataclass
class SelfEvolutionConfig:
    """自我进化配置"""
    enable_telemetry: bool = True
    enable_lifecycle: bool = True
    enable_curator: bool = True
    enable_merger: bool = True

    telemetry_interval: int = 3600
    lifecycle_interval: int = 86400
    curator_interval_hours: int = 168
    curator_min_idle_hours: float = 2.0
    merger_threshold: float = 0.6


class SelfEvolutionManager:
    """
    自我进化管理器

    统一管理所有自我进化组件:
    - 启动/停止各组件
    - 配置管理
    - 状态查询
    - 触发审查
    """

    def __init__(
        self,
        config: Optional[SelfEvolutionConfig] = None,
        skills_dir: Optional[Path] = None,
    ):
        self.config = config or SelfEvolutionConfig()

        if skills_dir is None:
            from shared.config import get_data_dir
            skills_dir = get_data_dir() / "skills"

        self.skills_dir = Path(skills_dir)

        self._telemetry = None
        self._lifecycle = None
        self._curator = None
        self._merger = None

        self._running = False

        self._initialize_components()

    def _initialize_components(self) -> None:
        """初始化所有组件"""
        if self.config.enable_telemetry:
            try:
                from brain.skills import get_skill_telemetry
                self._telemetry = get_skill_telemetry()
                logger.info("Initialized skill telemetry")
            except Exception as e:
                logger.warning(f"Failed to initialize telemetry: {e}")

        if self.config.enable_lifecycle:
            try:
                from brain.skills import get_lifecycle_manager
                self._lifecycle = get_lifecycle_manager()
                logger.info("Initialized lifecycle manager")
            except Exception as e:
                logger.warning(f"Failed to initialize lifecycle manager: {e}")

        if self.config.enable_curator:
            try:
                from brain_curator.enhanced_curator import get_curator
                self._curator = get_curator()
                logger.info("Initialized curator")
            except Exception as e:
                logger.warning(f"Failed to initialize curator: {e}")

        if self.config.enable_merger:
            try:
                from brain.skills import SkillMerger
                self._merger = SkillMerger(
                    similarity_threshold=self.config.merger_threshold
                )
                logger.info("Initialized skill merger")
            except Exception as e:
                logger.warning(f"Failed to initialize merger: {e}")

    @property
    def telemetry(self):
        """获取 telemetry"""
        return self._telemetry

    @property
    def lifecycle(self):
        """获取 lifecycle manager"""
        return self._lifecycle

    @property
    def curator(self):
        """获取 curator"""
        return self._curator

    @property
    def merger(self):
        """获取 merger"""
        return self._merger

    async def start(self) -> None:
        """启动自我进化管理器"""
        if self._running:
            logger.warning("Self-evolution manager already running")
            return

        self._running = True

        if self._lifecycle:
            try:
                await self._lifecycle.start_periodic_checks()
            except Exception as e:
                logger.error(f"Failed to start lifecycle manager: {e}")

        if self._curator:
            try:
                self._curator.interval_hours = self.config.curator_interval_hours
                self._curator.min_idle_hours = self.config.curator_min_idle_hours
                await self._curator.start_periodic_review()
            except Exception as e:
                logger.error(f"Failed to start curator: {e}")

        logger.info("Self-evolution manager started")

    async def stop(self) -> None:
        """停止自我进化管理器"""
        if not self._running:
            return

        self._running = False

        if self._lifecycle:
            try:
                await self._lifecycle.stop_periodic_checks()
            except Exception as e:
                logger.error(f"Failed to stop lifecycle manager: {e}")

        if self._curator:
            try:
                await self._curator.stop_periodic_review()
            except Exception as e:
                logger.error(f"Failed to stop curator: {e}")

        logger.info("Self-evolution manager stopped")

    async def trigger_review(
        self,
        idle_for_seconds: Optional[float] = None,
        dry_run: bool = False,
        on_summary: Optional[Callable[[str], None]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        触发一次审查

        Args:
            idle_for_seconds: 空闲时间
            dry_run: 是否干运行
            on_summary: 回调函数

        Returns:
            审查结果
        """
        if not self._curator:
            logger.warning("Curator not available")
            return None

        try:
            return await self._curator.maybe_run(
                idle_for_seconds=idle_for_seconds,
                on_summary=on_summary,
            )
        except Exception as e:
            logger.error(f"Failed to trigger review: {e}")
            return None

    async def trigger_lifecycle_check(self) -> None:
        """触发生命周期检查"""
        if not self._lifecycle:
            logger.warning("Lifecycle manager not available")
            return

        try:
            self._lifecycle.apply_automatic_transitions()
        except Exception as e:
            logger.error(f"Failed to trigger lifecycle check: {e}")

    async def trigger_skill_merge(
        self,
        dry_run: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        触发技能合并

        Args:
            dry_run: 是否干运行

        Returns:
            合并结果
        """
        if not self._merger:
            logger.warning("Merger not available")
            return None

        try:
            from brain.skills import load_skills_from_directory
            skills = load_skills_from_directory(self.skills_dir)
            results = self._merger.perform_consolidation(
                skills=skills,
                skills_dir=self.skills_dir,
                dry_run=dry_run,
            )
            report = self._merger.generate_report()
            return {
                "results": results,
                "report": report,
                "dry_run": dry_run,
            }
        except Exception as e:
            logger.error(f"Failed to trigger skill merge: {e}")
            return None

    def record_skill_use(self, skill_id: str) -> None:
        """
        记录技能使用

        Args:
            skill_id: 技能 ID
        """
        if not self._telemetry:
            return

        try:
            self._telemetry.record_use(skill_id)
        except Exception as e:
            logger.error(f"Failed to record skill use: {e}")

    def record_skill_view(self, skill_id: str) -> None:
        """
        记录技能查看

        Args:
            skill_id: 技能 ID
        """
        if not self._telemetry:
            return

        try:
            self._telemetry.record_view(skill_id)
        except Exception as e:
            logger.error(f"Failed to record skill view: {e}")

    def get_status(self) -> Dict[str, Any]:
        """
        获取状态

        Returns:
            状态字典
        """
        status = {
            "running": self._running,
            "components": {
                "telemetry": self._telemetry is not None,
                "lifecycle": self._lifecycle is not None,
                "curator": self._curator is not None,
                "merger": self._merger is not None,
            },
        }

        if self._telemetry:
            try:
                status["telemetry_summary"] = self._telemetry.get_usage_summary()
            except Exception:
                pass

        if self._lifecycle:
            try:
                status["lifecycle_summary"] = self._lifecycle.get_lifecycle_summary()
            except Exception:
                pass

        if self._curator:
            try:
                status["curator_status"] = self._curator.get_status()
            except Exception:
                pass

        return status

    def enable(self, component: str) -> None:
        """
        启用组件

        Args:
            component: 组件名称
        """
        if component == "telemetry":
            self.config.enable_telemetry = True
        elif component == "lifecycle":
            self.config.enable_lifecycle = True
        elif component == "curator":
            self.config.enable_curator = True
        elif component == "merger":
            self.config.enable_merger = True

    def disable(self, component: str) -> None:
        """
        禁用组件

        Args:
            component: 组件名称
        """
        if component == "telemetry":
            self.config.enable_telemetry = False
        elif component == "lifecycle":
            self.config.enable_lifecycle = False
        elif component == "curator":
            self.config.enable_curator = False
        elif component == "merger":
            self.config.enable_merger = False


_global_manager: Optional[SelfEvolutionManager] = None


def get_self_evolution_manager() -> SelfEvolutionManager:
    """获取全局自我进化管理器"""
    global _global_manager
    if _global_manager is None:
        _global_manager = SelfEvolutionManager()
    return _global_manager
