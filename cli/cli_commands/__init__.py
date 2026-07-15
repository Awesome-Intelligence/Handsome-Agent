#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI Commands - CLI 命令系统模块

🚪 Access - 💬 CLI - CLI 命令系统

包含各种 CLI 命令实现：
- doctor: 诊断检查
- sessions: 会话管理
- logs: 日志查看
- gateway: Gateway 服务管理
- cron: 定时任务管理
- acp: ACP 服务器管理
- session_recap: 会话摘要
- uninstall: 卸载功能
"""

from .doctor import run_diagnostics
from .sessions import list_sessions, browse_sessions
from .logs import show_logs, tail_logs
from .gateway import (
    start_gateway,
    stop_gateway,
    check_gateway_status,
    restart_gateway,
)
from .cron import (
    build_parser as cron_build_parser,
    list_cron_jobs,
    check_cron_status,
    main as cron_main,
)
from .acp import (
    start_acp_server,
    stop_acp_server,
    check_acp_status,
)
from .session_recap import generate_session_recap
from .uninstall import (
    uninstall_agent,
    restore_from_backup,
    list_backups,
)

__all__ = [
    # doctor
    "run_diagnostics",
    # sessions
    "list_sessions",
    "browse_sessions",
    # logs
    "show_logs",
    "tail_logs",
    # gateway
    "start_gateway",
    "stop_gateway",
    "check_gateway_status",
    "restart_gateway",
    # cron
    "cron_build_parser",
    "cron_main",
    "list_cron_jobs",
    "check_cron_status",
    # acp
    "start_acp_server",
    "stop_acp_server",
    "check_acp_status",
    # session_recap
    "generate_session_recap",
    # uninstall
    "uninstall_agent",
    "restore_from_backup",
    "list_backups",
]