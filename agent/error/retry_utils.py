"""重试工具 - 退避策略

参考 Hermes 的 jittered_backoff 实现，用于 API 调用重试时的延迟计算。
"""

import random
import threading
import time


# Monotonic counter for jitter seed uniqueness within the same process.
_jitter_counter = 0
_jitter_lock = threading.Lock()


def jittered_backoff(
    attempt: int,
    *,
    base_delay: float = 5.0,
    max_delay: float = 120.0,
    jitter_ratio: float = 0.5,
) -> float:
    """计算带抖动的指数退避延迟

    Args:
        attempt: 重试次数（从 1 开始）
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟上限（秒）
        jitter_ratio: 抖动比例（0.5 表示抖动在 [0, 0.5 * delay] 范围内）

    Returns:
        延迟时间（秒）
    """
    global _jitter_counter
    with _jitter_lock:
        _jitter_counter += 1
        tick = _jitter_counter

    exponent = max(0, attempt - 1)
    if exponent >= 63 or base_delay <= 0:
        delay = max_delay
    else:
        delay = min(base_delay * (2 ** exponent), max_delay)

    seed = (time.time_ns() ^ (tick * 0x9E3779B9)) & 0xFFFFFFFF
    rng = random.Random(seed)
    jitter = rng.uniform(0, jitter_ratio * delay)

    return delay + jitter
