#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
进程内存监控模块 - Periodic process memory usage logging

参考 Hermes Agent 的 gateway/memory_monitor.py 实现。

Gateway 是一个长期运行的进程，会累积内存（缓存 Agent 实例、会话记录、
工具模式、记忆提供者、MCP 连接等）。任何子系统的内存泄漏在单一日志行
中都不可见，只有观察 RSS 在数小时内的增长才能发现。

本模块每 N 分钟（默认 5 分钟）输出一条结构化的 ``[MEMORY] ...`` 日志，
以便维护者调查疑似泄漏问题。

设计要点：
- Grep 友好的单行格式，以 ``[MEMORY]`` 开头
- 关闭时记录最终快照
- 启动时立即记录基线快照
- 守护线程 - 永不阻塞进程退出
- 使用 ``psutil``（跨平台支持）

日志子层：📊 监控
"""

from __future__ import annotations

import gc
import logging
import os
import sys
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

_BYTES_TO_MB = 1024 * 1024

_monitor_thread: Optional[threading.Thread] = None
_stop_event: Optional[threading.Event] = None
_start_time: Optional[float] = None
_interval_seconds: float = 300.0  # 5 minutes
_lock = threading.Lock()
_enabled: bool = False


def _get_rss_mb() -> Optional[int]:
    """
    获取当前进程 RSS（Resident Set Size）大小（MB）。

    优先使用 psutil（跨平台支持）。
    """
    try:
        import psutil

        rss = psutil.Process(os.getpid()).memory_info().rss
        return int(rss / _BYTES_TO_MB)
    except ImportError:
        logger.debug("psutil not available, memory monitoring disabled")
        return None
    except Exception:
        return None


def log_memory_usage(prefix: str = "") -> None:
    """
    记录当前内存使用情况，格式为 grep 友好的 ``[MEMORY] ...`` 行。

    可从任何线程在重要生命周期时刻按需调用。

    Args:
        prefix: 可选的额外标签，例如 "baseline"、"shutdown"
    """
    global _start_time, _enabled

    if not _enabled:
        return

    rss = _get_rss_mb()
    uptime = int(time.monotonic() - _start_time) if _start_time else 0

    try:
        gc_counts = gc.get_count()  # (gen0, gen1, gen2)
    except Exception:
        gc_counts = (0, 0, 0)

    try:
        thread_count = threading.active_count()
    except Exception:
        thread_count = 0

    tag = f"{prefix} " if prefix else ""

    if rss is None:
        logger.info(
            "[MEMORY] %srss=unavailable gc=%s threads=%d uptime=%ds",
            tag,
            gc_counts,
            thread_count,
            uptime,
        )
    else:
        logger.info(
            "[MEMORY] %srss=%dMB gc=%s threads=%d uptime=%ds",
            tag,
            rss,
            gc_counts,
            thread_count,
            uptime,
        )


def _monitor_loop(stop_event: threading.Event, interval: float) -> None:
    """后台线程主体 - 每隔 interval 秒记录一次直到停止。"""
    while not stop_event.wait(interval):
        try:
            log_memory_usage()
        except Exception as e:
            logger.debug("Memory monitor iteration failed: %s", e)


def start_memory_monitoring(interval_seconds: float = 300.0) -> bool:
    """
    在守护线程中启动周期性内存使用日志记录。

    立即记录以捕获基线，然后每 interval_seconds 记录一次。
    多次调用是安全的 - 如果第一个监控仍在运行则无操作。

    Args:
        interval_seconds: 记录频率，默认 300 秒（5 分钟）

    Returns:
        如果启动了新的监控线程返回 True，如果已在运行或内存 introspection
        不可用则返回 False
    """
    global _monitor_thread, _stop_event, _start_time, _interval_seconds, _enabled

    with _lock:
        if _monitor_thread is not None and _monitor_thread.is_alive():
            return False

        # 检查是否可以读取 RSS
        if _get_rss_mb() is None:
            logger.warning(
                "[MEMORY] Memory monitoring unavailable: psutil could not read process RSS",
            )
            return False

        _start_time = time.monotonic()
        _interval_seconds = float(interval_seconds)
        _stop_event = threading.Event()
        _enabled = True

        # 记录基线快照
        log_memory_usage(prefix="baseline")

        _monitor_thread = threading.Thread(
            target=_monitor_loop,
            args=(_stop_event, _interval_seconds),
            name="gateway-memory-monitor",
            daemon=True,
        )
        _monitor_thread.start()

        logger.info(
            "[MEMORY] Periodic memory monitoring started (interval: %ds)",
            int(_interval_seconds),
        )
        return True


def stop_memory_monitoring(timeout: float = 2.0) -> None:
    """
    停止监控线程并记录最终快照。

    即使从未调用 start_memory_monitoring() 也是安全的。

    Args:
        timeout: 等待线程结束的超时时间（秒）
    """
    global _monitor_thread, _stop_event, _enabled

    with _lock:
        if _stop_event is None or _monitor_thread is None:
            return

        _enabled = False

        # 关闭前记录最终快照
        try:
            log_memory_usage(prefix="shutdown")
        except Exception:
            pass

        _stop_event.set()
        thread = _monitor_thread
        _monitor_thread = None
        _stop_event = None

    # 在锁外 join 以便卡住的日志调用不会死锁关闭
    try:
        thread.join(timeout=timeout)
    except Exception:
        pass

    logger.info("[MEMORY] Periodic memory monitoring stopped")


def is_running() -> bool:
    """后台监控线程是否存活。"""
    with _lock:
        return _monitor_thread is not None and _monitor_thread.is_alive()
