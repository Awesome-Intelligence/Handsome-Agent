#!/usr/bin/env python3
"""
Cronjob Tool Module

Provides scheduled task functionality:
- Scheduled task creation and management
- Task scheduling
- Task execution history

Based on Hermes Agent's cronjob_tools.py implementation.

Usage:
    from tools.cronjob_tool import cron_create_job, cron_list_jobs
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from common.logging_manager import get_execution_logger
from tools.registry import registry

logger = get_execution_logger("CronjobTool")


class CronJob:
    """定时任务类"""
    
    def __init__(
        self,
        name: str,
        schedule: str,
        command: str,
        description: Optional[str] = None,
        enabled: bool = True,
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.schedule = schedule
        self.command = command
        self.description = description or ""
        self.enabled = enabled
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.execution_history: List[Dict[str, Any]] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "schedule": self.schedule,
            "command": self.command,
            "description": self.description,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "execution_history": self.execution_history[-50:],  # 只保留最近50条
        }


class CronJobManager:
    """定时任务管理器"""
    
    def __init__(self):
        self._jobs: Dict[str, CronJob] = {}
        self._storage_path = Path.home() / ".agent_z" / "cron_jobs.json"
        self._load_jobs()
    
    def _load_jobs(self):
        """加载任务"""
        if self._storage_path.exists():
            try:
                with open(self._storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for job_data in data.get("jobs", []):
                        job = CronJob(
                            name=job_data["name"],
                            schedule=job_data["schedule"],
                            command=job_data["command"],
                            description=job_data.get("description", ""),
                            enabled=job_data.get("enabled", True),
                        )
                        job.id = job_data["id"]
                        job.created_at = job_data["created_at"]
                        job.updated_at = job_data["updated_at"]
                        job.execution_history = job_data.get("execution_history", [])
                        self._jobs[job.id] = job
            except Exception as e:
                logger.error(f"加载定时任务失败: {e}")
    
    def _save_jobs(self):
        """保存任务"""
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = {
                "jobs": [job.to_dict() for job in self._jobs.values()],
            }
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存定时任务失败: {e}")
    
    def create_job(
        self,
        name: str,
        schedule: str,
        command: str,
        description: Optional[str] = None,
    ) -> str:
        """创建定时任务"""
        job = CronJob(name, schedule, command, description)
        self._jobs[job.id] = job
        self._save_jobs()
        logger.info(f"创建定时任务: {name}")
        return job.id
    
    def update_job(
        self,
        job_id: str,
        name: Optional[str] = None,
        schedule: Optional[str] = None,
        command: Optional[str] = None,
        description: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> bool:
        """更新定时任务"""
        job = self._jobs.get(job_id)
        if not job:
            return False
        
        if name is not None:
            job.name = name
        if schedule is not None:
            job.schedule = schedule
        if command is not None:
            job.command = command
        if description is not None:
            job.description = description
        if enabled is not None:
            job.enabled = enabled
        
        job.updated_at = datetime.now().isoformat()
        self._save_jobs()
        logger.info(f"更新定时任务: {job.name}")
        return True
    
    def delete_job(self, job_id: str) -> bool:
        """删除定时任务"""
        if job_id in self._jobs:
            job_name = self._jobs[job_id].name
            del self._jobs[job_id]
            self._save_jobs()
            logger.info(f"删除定时任务: {job_name}")
            return True
        return False
    
    def toggle_job(self, job_id: str) -> Optional[bool]:
        """切换任务启用状态"""
        job = self._jobs.get(job_id)
        if not job:
            return None
        
        job.enabled = not job.enabled
        job.updated_at = datetime.now().isoformat()
        self._save_jobs()
        return job.enabled
    
    def get_job(self, job_id: str) -> Optional[CronJob]:
        """获取任务"""
        return self._jobs.get(job_id)
    
    def list_jobs(self) -> List[Dict[str, Any]]:
        """列出所有任务"""
        return [
            {
                "id": job.id,
                "name": job.name,
                "schedule": job.schedule,
                "command": job.command,
                "description": job.description,
                "enabled": job.enabled,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
                "last_execution": job.execution_history[-1] if job.execution_history else None,
            }
            for job in self._jobs.values()
        ]


# 全局管理器实例
_cron_manager = CronJobManager()


def cron_create_job(
    name: str,
    schedule: str,
    command: str,
    description: Optional[str] = None,
) -> str:
    """
    创建定时任务。
    
    Args:
        name: 任务名称
        schedule: cron表达式 (如 "0 2 * * *")
        command: 要执行的命令
        description: 可选的描述
    
    Returns:
        JSON 格式的结果字符串
    """
    job_id = _cron_manager.create_job(name, schedule, command, description)
    
    result = {
        "success": True,
        "job_id": job_id,
        "name": name,
        "schedule": schedule,
        "message": f"定时任务已创建: {name}",
        "note": "此为配置存储功能，实际调度执行需要额外的调度器服务。",
    }
    
    return json.dumps(result, ensure_ascii=False)


def cron_update_job(
    job_id: str,
    name: Optional[str] = None,
    schedule: Optional[str] = None,
    command: Optional[str] = None,
    description: Optional[str] = None,
    enabled: Optional[bool] = None,
) -> str:
    """
    更新定时任务。
    
    Args:
        job_id: 任务ID
        name: 可选的新名称
        schedule: 可选的新cron表达式
        command: 可选的新命令
        description: 可选的新描述
        enabled: 可选的启用状态
    
    Returns:
        JSON 格式的结果字符串
    """
    success = _cron_manager.update_job(
        job_id, name, schedule, command, description, enabled
    )
    
    if success:
        result = {
            "success": True,
            "message": "定时任务已更新",
        }
    else:
        result = {
            "success": False,
            "error": f"定时任务不存在: {job_id}",
        }
    
    return json.dumps(result, ensure_ascii=False)


def cron_delete_job(job_id: str) -> str:
    """
    删除定时任务。
    
    Args:
        job_id: 任务ID
    
    Returns:
        JSON 格式的结果字符串
    """
    success = _cron_manager.delete_job(job_id)
    
    if success:
        result = {
            "success": True,
            "message": "定时任务已删除",
        }
    else:
        result = {
            "success": False,
            "error": f"定时任务不存在: {job_id}",
        }
    
    return json.dumps(result, ensure_ascii=False)


def cron_toggle_job(job_id: str) -> str:
    """
    切换定时任务启用状态。
    
    Args:
        job_id: 任务ID
    
    Returns:
        JSON 格式的结果字符串
    """
    enabled = _cron_manager.toggle_job(job_id)
    
    if enabled is not None:
        result = {
            "success": True,
            "enabled": enabled,
            "message": f"定时任务已{'启用' if enabled else '禁用'}",
        }
    else:
        result = {
            "success": False,
            "error": f"定时任务不存在: {job_id}",
        }
    
    return json.dumps(result, ensure_ascii=False)


def cron_list_jobs() -> str:
    """
    列出所有定时任务。
    
    Returns:
        JSON 格式的结果字符串
    """
    jobs = _cron_manager.list_jobs()
    
    result = {
        "success": True,
        "jobs": jobs,
        "total": len(jobs),
        "note": "此为配置管理功能，实际调度执行需要额外的调度器服务。",
    }
    
    return json.dumps(result, ensure_ascii=False)


def cron_view_job(job_id: str) -> str:
    """
    查看定时任务详情。
    
    Args:
        job_id: 任务ID
    
    Returns:
        JSON 格式的结果字符串
    """
    job = _cron_manager.get_job(job_id)
    
    if job:
        result = {
            "success": True,
            "job": job.to_dict(),
        }
    else:
        result = {
            "success": False,
            "error": f"定时任务不存在: {job_id}",
        }
    
    return json.dumps(result, ensure_ascii=False)


def check_cron_requirements() -> bool:
    """定时任务工具无外部依赖，始终可用"""
    return True


# 工具定义
CRON_CREATE_JOB_SCHEMA = {
    "name": "cron_create_job",
    "description": "Create a new cron job (scheduled task).",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name of the cron job.",
            },
            "schedule": {
                "type": "string",
                "description": "Cron schedule expression (e.g., '0 2 * * *' for daily at 2 AM).",
            },
            "command": {
                "type": "string",
                "description": "Command to execute.",
            },
            "description": {
                "type": "string",
                "description": "Optional description of the job.",
            },
        },
        "required": ["name", "schedule", "command"],
    },
}


CRON_UPDATE_JOB_SCHEMA = {
    "name": "cron_update_job",
    "description": "Update an existing cron job.",
    "parameters": {
        "type": "object",
        "properties": {
            "job_id": {
                "type": "string",
                "description": "ID of the job to update.",
            },
            "name": {
                "type": "string",
                "description": "Optional new name.",
            },
            "schedule": {
                "type": "string",
                "description": "Optional new cron schedule.",
            },
            "command": {
                "type": "string",
                "description": "Optional new command.",
            },
            "description": {
                "type": "string",
                "description": "Optional new description.",
            },
            "enabled": {
                "type": "boolean",
                "description": "Optional enable/disable the job.",
            },
        },
        "required": ["job_id"],
    },
}


CRON_DELETE_JOB_SCHEMA = {
    "name": "cron_delete_job",
    "description": "Delete a cron job.",
    "parameters": {
        "type": "object",
        "properties": {
            "job_id": {
                "type": "string",
                "description": "ID of the job to delete.",
            },
        },
        "required": ["job_id"],
    },
}


CRON_TOGGLE_JOB_SCHEMA = {
    "name": "cron_toggle_job",
    "description": "Toggle a cron job's enabled/disabled state.",
    "parameters": {
        "type": "object",
        "properties": {
            "job_id": {
                "type": "string",
                "description": "ID of the job to toggle.",
            },
        },
        "required": ["job_id"],
    },
}


CRON_LIST_JOBS_SCHEMA = {
    "name": "cron_list_jobs",
    "description": "List all cron jobs.",
    "parameters": {
        "type": "object",
        "properties": {},
    },
}


CRON_VIEW_JOB_SCHEMA = {
    "name": "cron_view_job",
    "description": "View details of a specific cron job.",
    "parameters": {
        "type": "object",
        "properties": {
            "job_id": {
                "type": "string",
                "description": "ID of the job to view.",
            },
        },
        "required": ["job_id"],
    },
}


# 注册工具
registry.register(
    name="cron_create_job",
    toolset="cron",
    schema=CRON_CREATE_JOB_SCHEMA,
    handler=lambda args, **kw: cron_create_job(
        name=args.get("name", ""),
        schedule=args.get("schedule", ""),
        command=args.get("command", ""),
        description=args.get("description"),
    ),
    check_fn=check_cron_requirements,
    emoji="⏰",
)


registry.register(
    name="cron_update_job",
    toolset="cron",
    schema=CRON_UPDATE_JOB_SCHEMA,
    handler=lambda args, **kw: cron_update_job(
        job_id=args.get("job_id", ""),
        name=args.get("name"),
        schedule=args.get("schedule"),
        command=args.get("command"),
        description=args.get("description"),
        enabled=args.get("enabled"),
    ),
    check_fn=check_cron_requirements,
    emoji="✏️",
)


registry.register(
    name="cron_delete_job",
    toolset="cron",
    schema=CRON_DELETE_JOB_SCHEMA,
    handler=lambda args, **kw: cron_delete_job(args.get("job_id", "")),
    check_fn=check_cron_requirements,
    emoji="🗑️",
)


registry.register(
    name="cron_toggle_job",
    toolset="cron",
    schema=CRON_TOGGLE_JOB_SCHEMA,
    handler=lambda args, **kw: cron_toggle_job(args.get("job_id", "")),
    check_fn=check_cron_requirements,
    emoji="🔄",
)


registry.register(
    name="cron_list_jobs",
    toolset="cron",
    schema=CRON_LIST_JOBS_SCHEMA,
    handler=lambda args, **kw: cron_list_jobs(),
    check_fn=check_cron_requirements,
    emoji="📋",
)


registry.register(
    name="cron_view_job",
    toolset="cron",
    schema=CRON_VIEW_JOB_SCHEMA,
    handler=lambda args, **kw: cron_view_job(args.get("job_id", "")),
    check_fn=check_cron_requirements,
    emoji="👁️",
)
