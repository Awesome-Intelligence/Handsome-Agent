#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FileLock Module - 跨平台文件锁实现

提供真正的跨平台文件锁功能：
- Unix 平台使用 `fcntl.flock()` 实现阻塞/非阻塞文件锁
- Windows 平台使用 `msvcrt.locking()` 实现文件锁
- 支持锁超时机制，防止死锁
- 提供上下文管理器接口

基于 Hermes Agent 的 memory_tool.py 文件锁实现。

日志子层：💾 Memory
"""

import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from common.logging_manager import get_execution_logger

logger = get_execution_logger("MemoryStore")

# 跨平台锁实现
# fcntl 用于 Unix，msvcrt 用于 Windows
_fcntl_lock = None
_msvcrt_lock = None

try:
    import fcntl
    _fcntl_lock = fcntl
except ImportError:
    pass

try:
    import msvcrt
    _msvcrt_lock = msvcrt
except ImportError:
    pass


class FileLockError(Exception):
    """文件锁异常"""
    pass


class FileLockTimeoutError(FileLockError):
    """获取锁超时异常"""
    pass


class FileLock:
    """
    跨平台文件锁实现。

    使用独立的 .lock 文件实现锁机制，这样目标文件本身可以
    通过 os.replace() 进行原子替换。

    支持：
    - Unix: fcntl.flock() 阻塞/非阻塞锁
    - Windows: msvcrt.locking() 锁机制
    - 锁超时机制，防止死锁
    - 上下文管理器接口

    用法：
        lock = FileLock(path)
        with lock.acquire(timeout=5.0):
            # 临界区操作
            pass
    """

    # 默认锁超时时间（秒）
    DEFAULT_TIMEOUT = 30.0

    def __init__(self, path: Path, timeout: Optional[float] = None):
        """
        初始化文件锁。

        Args:
            path: 需要加锁的目标文件路径
            timeout: 获取锁的超时时间（秒），None 表示使用默认值
        """
        self._path = Path(path)
        self._lock_path = self._path.with_suffix(self._path.suffix + ".lock")
        self._timeout = timeout if timeout is not None else self.DEFAULT_TIMEOUT
        self._fd = None
        self._locked = False

    @property
    def lock_path(self) -> Path:
        """返回锁文件路径"""
        return self._lock_path

    @property
    def is_locked(self) -> bool:
        """返回当前是否持有锁"""
        return self._locked

    def _ensure_lock_dir(self):
        """确保锁文件目录存在"""
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)

    def _acquire_unix(self, blocking: bool = True) -> bool:
        """
        在 Unix 系统上获取文件锁。

        Args:
            blocking: 是否阻塞等待

        Returns:
            True 获取成功，False 获取失败（非阻塞模式）
        """
        if _fcntl_lock is None:
            return True  # 没有锁机制，静默通过

        self._ensure_lock_dir()
        self._fd = open(self._lock_path, "a+", encoding="utf-8")

        try:
            if blocking:
                _fcntl_lock.flock(self._fd, _fcntl_lock.LOCK_EX)
            else:
                result = _fcntl_lock.flock(self._fd, _fcntl_lock.LOCK_EX | _fcntl_lock.LOCK_NB)
                if result != 0:
                    return False
            return True
        except (OSError, IOError) as e:
            if self._fd:
                self._fd.close()
                self._fd = None
            raise FileLockError(f"Failed to acquire lock: {e}")

    def _release_unix(self):
        """在 Unix 系统上释放文件锁"""
        if _fcntl_lock is None:
            return

        if self._fd:
            try:
                _fcntl_lock.flock(self._fd, _fcntl_lock.LOCK_UN)
            except (OSError, IOError):
                pass
            finally:
                try:
                    self._fd.close()
                except (OSError, IOError):
                    pass
                self._fd = None

    def _acquire_windows(self, blocking: bool = True) -> bool:
        """
        在 Windows 系统上获取文件锁。

        Args:
            blocking: 是否阻塞等待

        Returns:
            True 获取成功，False 获取失败（非阻塞模式）
        """
        if _msvcrt_lock is None:
            return True  # 没有锁机制，静默通过

        self._ensure_lock_dir()
        # Windows 上需要 "a+" 模式来创建文件（如果不存在）
        self._fd = open(self._lock_path, "a+", encoding="utf-8")

        try:
            self._fd.seek(0)
            if blocking:
                # Windows 阻塞锁：持续尝试直到成功或超时
                start_time = time.time()
                while True:
                    try:
                        _msvcrt_lock.locking(self._fd.fileno(), _msvcrt_lock.LK_LOCK, 1)
                        return True
                    except (OSError, IOError):
                        if self._timeout is not None:
                            elapsed = time.time() - start_time
                            if elapsed >= self._timeout:
                                self._fd.close()
                                self._fd = None
                                return False
                        time.sleep(0.1)
            else:
                # Windows 非阻塞锁
                try:
                    _msvcrt_lock.locking(self._fd.fileno(), _msvcrt_lock.LK_NBLCK, 1)
                    return True
                except (OSError, IOError):
                    self._fd.close()
                    self._fd = None
                    return False
        except (OSError, IOError) as e:
            if self._fd:
                self._fd.close()
                self._fd = None
            raise FileLockError(f"Failed to acquire lock: {e}")

    def _release_windows(self):
        """在 Windows 系统上释放文件锁"""
        if _msvcrt_lock is None:
            return

        if self._fd:
            try:
                self._fd.seek(0)
                _msvcrt_lock.locking(self._fd.fileno(), _msvcrt_lock.LK_UNLCK, 1)
            except (OSError, IOError):
                pass
            finally:
                try:
                    self._fd.close()
                except (OSError, IOError):
                    pass
                self._fd = None

    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        获取文件锁。

        Args:
            blocking: 是否阻塞等待
            timeout: 覆盖实例级别的超时时间

        Returns:
            True 获取成功，False 获取失败（超时或非阻塞模式）

        Raises:
            FileLockTimeoutError: 获取锁超时
        """
        if self._locked:
            return True

        effective_timeout = timeout if timeout is not None else self._timeout

        # 选择平台实现
        if _fcntl_lock is not None:
            _acquire = self._acquire_unix
            _release = self._release_unix
        elif _msvcrt_lock is not None:
            _acquire = self._acquire_windows
            _release = self._release_windows
        else:
            # 没有可用的锁机制
            logger.warning("No file locking mechanism available on this platform")
            self._locked = True
            return True

        if not blocking:
            # 非阻塞模式
            if _acquire(blocking=False):
                self._locked = True
                return True
            return False

        # 阻塞模式：带超时
        if effective_timeout is not None and effective_timeout <= 0:
            # 立即超时，尝试非阻塞
            if _acquire(blocking=False):
                self._locked = True
                return True
            raise FileLockTimeoutError(
                f"Failed to acquire lock within {effective_timeout}s"
            )

        # 阻塞等待直到成功或超时
        start_time = time.time()
        while True:
            if _acquire(blocking=False):
                self._locked = True
                return True

            if effective_timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= effective_timeout:
                    raise FileLockTimeoutError(
                        f"Failed to acquire lock within {effective_timeout}s"
                    )

            # 使用指数退避避免频繁重试
            sleep_time = min(0.1 + elapsed * 0.01, 1.0)
            time.sleep(sleep_time)

    def release(self):
        """释放文件锁"""
        if not self._locked:
            return

        if _fcntl_lock is not None:
            self._release_unix()
        elif _msvcrt_lock is not None:
            self._release_windows()

        self._locked = False

    def __enter__(self):
        """上下文管理器入口"""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.release()
        return False


@contextmanager
def file_lock(path: Path, timeout: Optional[float] = None):
    """
    文件锁上下文管理器。

    这是一个便捷函数，创建 FileLock 实例并作为上下文管理器使用。

    Args:
        path: 需要加锁的目标文件路径
        timeout: 获取锁的超时时间（秒）

    用法：
        with file_lock(target_path, timeout=10.0):
            # 临界区操作
            pass

    Raises:
        FileLockTimeoutError: 获取锁超时
        FileLockError: 其他锁错误
    """
    lock = FileLock(path, timeout=timeout)
    try:
        lock.acquire()
        yield lock
    finally:
        lock.release()


def is_lock_available() -> bool:
    """
    检查当前平台是否支持文件锁。

    Returns:
        True 支持文件锁，False 不支持
    """
    return _fcntl_lock is not None or _msvcrt_lock is not None


def get_lock_type() -> str:
    """
    获取当前平台使用的锁类型。

    Returns:
        'fcntl' (Unix), 'msvcrt' (Windows), 或 'none' (不可用)
    """
    if _fcntl_lock is not None:
        return 'fcntl'
    elif _msvcrt_lock is not None:
        return 'msvcrt'
    return 'none'


__all__ = [
    'FileLock',
    'FileLockError',
    'FileLockTimeoutError',
    'file_lock',
    'is_lock_available',
    'get_lock_type',
]
