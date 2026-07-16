#!/usr/bin/env python3
"""
Per-thread Interrupt Signaling Module

Provides thread-scoped interrupt tracking so that interrupting one agent
session does not kill tools running in other sessions.

Usage in tools:
    from tools.interrupt import is_interrupted, set_interrupt

    if is_interrupted():
        return {"output": "[interrupted]", "returncode": 130}
"""

import logging
import os
import threading

logger = logging.getLogger(__name__)

_DEBUG_INTERRUPT = bool(os.getenv("AGENTZ_DEBUG_INTERRUPT"))

if _DEBUG_INTERRUPT:
    logger.setLevel(logging.INFO)

_interrupted_threads: set[int] = set()
_lock = threading.Lock()


def set_interrupt(active: bool, thread_id: int | None = None) -> None:
    tid = thread_id if thread_id is not None else threading.current_thread().ident
    with _lock:
        if active:
            _interrupted_threads.add(tid)
        else:
            _interrupted_threads.discard(tid)
        _snapshot = set(_interrupted_threads) if _DEBUG_INTERRUPT else None
    if _DEBUG_INTERRUPT:
        logger.info(
            "[interrupt-debug] set_interrupt(active=%s, target_tid=%s) "
            "called_from_tid=%s current_set=%s",
            active, tid, threading.current_thread().ident, _snapshot,
        )


def is_interrupted() -> bool:
    tid = threading.current_thread().ident
    with _lock:
        return tid in _interrupted_threads


class _ThreadAwareEventProxy:
    def is_set(self) -> bool:
        return is_interrupted()

    def set(self) -> None:
        set_interrupt(True)

    def clear(self) -> None:
        set_interrupt(False)

    def wait(self, timeout: float | None = None) -> bool:
        return self.is_set()


_interrupt_event = _ThreadAwareEventProxy()