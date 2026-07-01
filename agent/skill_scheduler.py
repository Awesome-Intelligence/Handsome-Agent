#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill Scheduler - 定时任务调度器

提供技能系统的定时任务支持：
- 定时 Curator 清理
- 定时更新检测
- 后台任务管理

🚪 Access - 📋 Skills - 定时任务
"""

from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import json

from common.config import get_settings

logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_CURATOR_INTERVAL_HOURS = 24  # Curator 运行间隔（小时）
DEFAULT_UPDATE_CHECK_INTERVAL_HOURS = 6  # 更新检测间隔（小时）


@dataclass
class ScheduledTask:
    """定时任务"""
    name: str
    func: Callable
    interval_hours: float
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    enabled: bool = True
    run_count: int = 0
    last_error: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def should_run(self) -> bool:
        """检查是否应该运行"""
        if not self.enabled:
            return False

        if self.next_run is None:
            return True

        try:
            from datetime import datetime, timezone
            next_dt = datetime.fromisoformat(self.next_run)
            if next_dt.tzinfo is None:
                next_dt = next_dt.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) >= next_dt
        except Exception:
            return True

    def update_next_run(self) -> None:
        """更新下次运行时间"""
        self.last_run = datetime.now(timezone.utc).isoformat()
        next_dt = datetime.now(timezone.utc) + timedelta(hours=self.interval_hours)
        self.next_run = next_dt.isoformat()


@dataclass
class SchedulerStats:
    """调度器统计"""
    running: bool
    paused: bool
    tasks_count: int
    enabled_tasks: int
    run_count: int
    last_run: Optional[str]
    errors_count: int


class SkillScheduler:
    """
    技能定时任务调度器

    管理后台定时任务，包括：
    - Curator 清理
    - 更新检测
    """

    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._run_count = 0
        self._errors_count = 0
        self._last_error: Optional[str] = None

        # 加载配置
        self._load_config()

        # 注册默认任务
        self._register_default_tasks()

    def _load_config(self) -> None:
        """从配置加载调度器设置"""
        try:
            skills_config = get_settings().skills
            scheduler_config = skills_config.get("scheduler", {})

            self._curator_interval = scheduler_config.get(
                "curator_interval_hours", DEFAULT_CURATOR_INTERVAL_HOURS
            )
            self._update_check_interval = scheduler_config.get(
                "update_check_interval_hours", DEFAULT_UPDATE_CHECK_INTERVAL_HOURS
            )
            self._enabled = scheduler_config.get("enabled", True)
            self._check_idle = scheduler_config.get("check_idle", True)
            self._min_idle_hours = scheduler_config.get("min_idle_hours", 2)

        except Exception as e:
            logger.warning(f"Failed to load scheduler config: {e}")
            self._curator_interval = DEFAULT_CURATOR_INTERVAL_HOURS
            self._update_check_interval = DEFAULT_UPDATE_CHECK_INTERVAL_HOURS
            self._enabled = True
            self._check_idle = True
            self._min_idle_hours = 2

    def _register_default_tasks(self) -> None:
        """注册默认任务"""

        # Curator 清理任务
        self.register_task(
            name="curator_cleanup",
            func=self._run_curator,
            interval_hours=self._curator_interval,
            enabled=self._enabled,
            extra={"description": "自动清理过期技能"},
        )

        # 更新检测任务
        self.register_task(
            name="update_check",
            func=self._check_updates,
            interval_hours=self._update_check_interval,
            enabled=False,  # 默认禁用，需要来源适配器支持
            extra={"description": "检查技能更新"},
        )

    def register_task(
        self,
        name: str,
        func: Callable,
        interval_hours: float,
        enabled: bool = True,
        extra: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        注册定时任务

        Args:
            name: 任务名称
            func: 任务函数
            interval_hours: 运行间隔（小时）
            enabled: 是否启用
            extra: 额外配置

        Returns:
            是否成功
        """
        task = ScheduledTask(
            name=name,
            func=func,
            interval_hours=interval_hours,
            enabled=enabled,
            extra=extra or {},
        )

        # 计算首次运行时间
        task.update_next_run()

        self._tasks[name] = task
        logger.info(f"Registered scheduled task: {name} (interval: {interval_hours}h)")
        return True

    def unregister_task(self, name: str) -> bool:
        """取消注册任务"""
        if name in self._tasks:
            del self._tasks[name]
            logger.info(f"Unregistered scheduled task: {name}")
            return True
        return False

    def enable_task(self, name: str) -> bool:
        """启用任务"""
        if name in self._tasks:
            self._tasks[name].enabled = True
            self._tasks[name].update_next_run()
            logger.info(f"Enabled scheduled task: {name}")
            return True
        return False

    def disable_task(self, name: str) -> bool:
        """禁用任务"""
        if name in self._tasks:
            self._tasks[name].enabled = False
            logger.info(f"Disabled scheduled task: {name}")
            return True
        return False

    def _run_curator(self) -> Dict[str, Any]:
        """运行 Curator 清理"""
        try:
            from agent.skill_curator import run_curator, CuratorConfig

            config = CuratorConfig(
                dry_run=False,
                auto_archive=True,
                auto_mark_stale=True,
            )

            report = run_curator(config)

            result = {
                "success": True,
                "marked_stale": len([a for a in report.actions if a.action == "mark_stale"]),
                "archived": len([a for a in report.actions if a.action == "archive"]),
                "errors": len(report.errors),
            }

            logger.info(
                f"Curator cleanup completed: {result['marked_stale']} stale, "
                f"{result['archived']} archived, {result['errors']} errors"
            )

            return result

        except Exception as e:
            logger.error(f"Curator cleanup failed: {e}")
            raise

    def _check_updates(self) -> Dict[str, Any]:
        """检查技能更新"""
        try:
            from agent.skill_lock import list_locked_skills

            entries = list_locked_skills()

            result = {
                "success": True,
                "total_skills": len(entries),
                "updates_available": 0,
                "details": [],
            }

            # TODO: 与来源适配器集成检测更新
            # 目前只统计锁定数量

            logger.info(f"Update check completed: {len(entries)} skills tracked")

            return result

        except Exception as e:
            logger.error(f"Update check failed: {e}")
            raise

    def _should_run_idle_check(self) -> bool:
        """检查是否应该在空闲时运行"""
        if not self._check_idle:
            return True

        # TODO: 检查系统空闲时间
        # 目前简单实现，总是返回 True
        return True

    async def _run_task_async(self, task: ScheduledTask) -> None:
        """异步运行任务"""
        try:
            logger.info(f"Running scheduled task: {task.name}")

            # 运行任务
            if asyncio.iscoroutinefunction(task.func):
                result = await task.func()
            else:
                result = task.func()

            # 更新状态
            task.run_count += 1
            task.last_error = None
            self._run_count += 1
            task.update_next_run()

            logger.info(f"Scheduled task completed: {task.name}")

        except Exception as e:
            task.last_error = str(e)
            self._errors_count += 1
            self._last_error = str(e)
            logger.error(f"Scheduled task failed: {task.name}: {e}")

    def _scheduler_loop(self) -> None:
        """调度器主循环"""
        while not self._stop_event.is_set():
            try:
                # 检查空闲状态
                if not self._should_run_idle_check():
                    self._stop_event.wait(60)  # 等待1分钟后再检查
                    continue

                # 检查每个任务
                for task in self._tasks.values():
                    if task.should_run():
                        # 在新线程中运行任务
                        thread = threading.Thread(
                            target=self._run_task_wrapper,
                            args=(task,),
                            daemon=True,
                        )
                        thread.start()

                # 每分钟检查一次
                self._stop_event.wait(60)

            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                self._stop_event.wait(60)

    def _run_task_wrapper(self, task: ScheduledTask) -> None:
        """运行任务的包装器"""
        try:
            if asyncio.iscoroutinefunction(task.func):
                # 创建新的事件循环
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(task.func())
                finally:
                    loop.close()
            else:
                task.func()

            # 更新状态
            task.run_count += 1
            task.last_error = None
            self._run_count += 1
            task.update_next_run()

        except Exception as e:
            task.last_error = str(e)
            self._errors_count += 1
            self._last_error = str(e)
            logger.error(f"Scheduled task failed: {task.name}: {e}")

    def start(self) -> bool:
        """启动调度器"""
        if self._running:
            logger.warning("Scheduler already running")
            return False

        self._running = True
        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name="SkillScheduler",
        )
        self._thread.start()

        logger.info("Skill scheduler started")
        return True

    def stop(self) -> bool:
        """停止调度器"""
        if not self._running:
            return False

        self._running = False
        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=5)

        logger.info("Skill scheduler stopped")
        return True

    def pause(self) -> None:
        """暂停调度器"""
        self._paused = True
        logger.info("Skill scheduler paused")

    def resume(self) -> None:
        """恢复调度器"""
        self._paused = False
        logger.info("Skill scheduler resumed")

    def run_now(self, task_name: str) -> bool:
        """
        立即运行指定任务

        Args:
            task_name: 任务名称

        Returns:
            是否成功
        """
        if task_name not in self._tasks:
            logger.warning(f"Task not found: {task_name}")
            return False

        task = self._tasks[task_name]
        thread = threading.Thread(
            target=self._run_task_wrapper,
            args=(task,),
            daemon=True,
        )
        thread.start()

        logger.info(f"Triggered immediate run of task: {task_name}")
        return True

    def get_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        enabled_count = sum(1 for t in self._tasks.values() if t.enabled)

        return {
            "running": self._running,
            "paused": self._paused,
            "tasks_count": len(self._tasks),
            "enabled_tasks": enabled_count,
            "run_count": self._run_count,
            "errors_count": self._errors_count,
            "last_error": self._last_error,
        }

    def get_task_status(self, name: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        if name not in self._tasks:
            return None

        task = self._tasks[name]

        return {
            "name": task.name,
            "enabled": task.enabled,
            "interval_hours": task.interval_hours,
            "last_run": task.last_run,
            "next_run": task.next_run,
            "run_count": task.run_count,
            "last_error": task.last_error,
            "description": task.extra.get("description", ""),
        }

    def list_tasks(self) -> List[Dict[str, Any]]:
        """列出所有任务"""
        return [self.get_task_status(name) for name in self._tasks]


# 全局实例
_scheduler: Optional[SkillScheduler] = None


def get_scheduler() -> SkillScheduler:
    """获取全局调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = SkillScheduler()
    return _scheduler


# 便捷函数

def start_scheduler() -> bool:
    """启动调度器"""
    scheduler = get_scheduler()
    return scheduler.start()


def stop_scheduler() -> bool:
    """停止调度器"""
    global _scheduler
    if _scheduler is None:
        return False
    return _scheduler.stop()


def pause_scheduler() -> None:
    """暂停调度器"""
    scheduler = get_scheduler()
    scheduler.pause()


def resume_scheduler() -> None:
    """恢复调度器"""
    scheduler = get_scheduler()
    scheduler.resume()


def run_curator_now() -> bool:
    """立即运行 Curator"""
    scheduler = get_scheduler()
    return scheduler.run_now("curator_cleanup")


def get_scheduler_status() -> Dict[str, Any]:
    """获取调度器状态"""
    scheduler = get_scheduler()
    return scheduler.get_status()


if __name__ == "__main__":
    # 测试
    scheduler = get_scheduler()

    print("Scheduler status:")
    print(json.dumps(scheduler.get_status(), indent=2))

    print("\nTasks:")
    for task in scheduler.list_tasks():
        print(f"  - {task['name']}: {task['description']} (enabled={task['enabled']})")

    # 立即运行 Curator
    print("\nRunning Curator now...")
    scheduler.run_now("curator_cleanup")
