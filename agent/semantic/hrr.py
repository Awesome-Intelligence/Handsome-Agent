#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Holographic Reduced Representations (HRR) 实现

参考 Hermes plugins/memory/holographic/holographic.py 实现

HRRs 是一种向量符号架构，用于编码组合结构到固定宽度的分布式表示中。
使用相位向量：每个概念是一个 [0, 2π) 角度的向量。

代数运算：
- bind (绑定) - 循环卷积（相位加法）- 关联两个概念
- unbind (解绑) - 循环相关（相位减法）- 从绑定值中检索
- bundle (捆绑) - 叠加（循环均值）- 合并多个概念

相位编码数值稳定，避免了传统复数 HRR 的幅度崩塌问题。

原子通过 SHA-256 确定性生成，确保跨进程、跨机器、跨语言版本的一致表示。

参考：
- Plate (1995) — Holographic Reduced Representations
- Gayler (2004) — Vector Symbolic Architectures answer Jackendoff's challenges
"""

import hashlib
import struct
import math
from typing import Optional

# 使用统一的日志管理器
from common.logging_manager import get_memory_logger

logger = get_memory_logger("HRR")

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False
    np = None  # type: ignore

_TWO_PI = 2.0 * math.pi


def _require_numpy() -> None:
    """检查 numpy 是否可用"""
    if not _HAS_NUMPY:
        raise RuntimeError("numpy is required for holographic operations. Install with: pip install numpy")


def encode_atom(word: str, dim: int = 512) -> "np.ndarray":
    """
    通过 SHA-256 计数器块生成确定性相位向量

    算法：
    - 通过哈希 f"{word}:{i}" 生成足够的 SHA-256 块，i=0,1,2,...
    - 连接摘要，解释为通过 struct.unpack 的 uint16 值
    - 缩放到 [0, 2π): phases = values * (2π / 65536)
    - 截断到 dim 个元素
    - 返回形状为 (dim,) 的 np.float64 数组

    Args:
        word: 要编码的词
        dim: 向量维度（默认 512）

    Returns:
        相位向量数组
    """
    _require_numpy()

    # 每个 SHA-256 摘要 32 字节 = 16 个 uint16 值
    values_per_block = 16
    blocks_needed = math.ceil(dim / values_per_block)

    uint16_values: list[int] = []
    for i in range(blocks_needed):
        digest = hashlib.sha256(f"{word}:{i}".encode()).digest()
        uint16_values.extend(struct.unpack("<16H", digest))

    phases = np.array(uint16_values[:dim], dtype=np.float64) * (_TWO_PI / 65536.0)
    return phases


def bind(a: "np.ndarray", b: "np.ndarray") -> "np.ndarray":
    """
    循环卷积 = 逐元素相位加法

    绑定将两个概念关联成一个复合向量。
    结果与两个输入都不同（准正交）。

    Args:
        a: 第一个相位向量
        b: 第二个相位向量

    Returns:
        绑定后的相位向量
    """
    _require_numpy()
    return (a + b) % _TWO_PI


def unbind(memory: "np.ndarray", key: "np.ndarray") -> "np.ndarray":
    """
    循环相关 = 逐元素相位减法

    解绑从内存向量中检索与键关联的值。
    unbind(bind(a, b), a) ≈ b（在叠加噪声范围内）

    Args:
        memory: 内存相位向量
        key: 键相位向量

    Returns:
        解绑后的相位向量
    """
    _require_numpy()
    return (memory - key) % _TWO_PI


def bundle(*vectors: "np.ndarray") -> "np.ndarray":
    """
    通过复指数的循环均值进行叠加

    捆绑将多个向量合并为一个与每个输入相似的向量。
    结果可以保存 O(sqrt(dim)) 个项目而不降低相似度。

    Args:
        *vectors: 要捆绑的相位向量列表

    Returns:
        捆绑后的相位向量
    """
    _require_numpy()
    complex_sum = np.sum([np.exp(1j * v) for v in vectors], axis=0)
    return np.angle(complex_sum) % _TWO_PI


def similarity(a: "np.ndarray", b: "np.ndarray") -> float:
    """
    相位余弦相似度。范围 [-1, 1]

    - 返回 1.0 表示完全相同的向量
    - 返回接近 0.0 表示随机（不相关）向量
    - 返回 -1.0 表示完全反相关的向量

    Args:
        a: 第一个相位向量
        b: 第二个相位向量

    Returns:
        相似度分数
    """
    _require_numpy()
    return float(np.mean(np.cos(a - b)))


def encode_text(text: str, dim: int = 512) -> "np.ndarray":
    """
    词袋编码：将每个 token 的原子向量捆绑

    分词方式：小写、按空格分割、去除前后标点符号。

    如果文本为空或不产生任何 token，返回 encode_atom("__hrr_empty__", dim)。

    Args:
        text: 要编码的文本
        dim: 向量维度

    Returns:
        所有 token 原子向量的捆绑
    """
    _require_numpy()

    tokens = [
        token.strip(".,!?;:\"'()[]{}")
        for token in text.lower().split()
    ]
    tokens = [t for t in tokens if t]

    if not tokens:
        return encode_atom("__hrr_empty__", dim)

    atom_vectors = [encode_atom(token, dim) for token in tokens]
    return bundle(*atom_vectors)


def encode_fact(content: str, entities: list, dim: int = 512) -> "np.ndarray":
    """
    结构化编码：content 绑定到 ROLE_CONTENT，每个 entity 绑定到 ROLE_ENTITY，全部捆绑

    角色向量是保留原子： "__hrr_role_content__", "__hrr_role_entity__"

    组件：
    1. bind(encode_text(content, dim), encode_atom("__hrr_role_content__", dim))
    2. 对于每个 entity: bind(encode_atom(entity.lower(), dim), encode_atom("__hrr_role_entity__", dim))
    3. 捆绑所有组件

    这支持代数提取：
        unbind(fact, bind(entity, ROLE_ENTITY)) ≈ content_vector

    Args:
        content: 事实内容
        entities: 实体列表
        dim: 向量维度

    Returns:
        编码的事实向量
    """
    _require_numpy()

    role_content = encode_atom("__hrr_role_content__", dim)
    role_entity = encode_atom("__hrr_role_entity__", dim)

    components: list = [
        bind(encode_text(content, dim), role_content)
    ]

    for entity in entities:
        components.append(bind(encode_atom(str(entity).lower(), dim), role_entity))

    return bundle(*components)


def encode_query(query: str, dim: int = 512) -> "np.ndarray":
    """
    编码查询向量（用于检索匹配）

    对于查询，使用词袋方法，与 encode_text 相同。

    Args:
        query: 查询文本
        dim: 向量维度

    Returns:
        查询向量
    """
    return encode_text(query, dim)


def phases_to_bytes(phases: "np.ndarray") -> bytes:
    """
    将相位向量序列化为字节

    float64 tobytes — dim=512 时约 4 KB

    Args:
        phases: 相位向量

    Returns:
        序列化字节
    """
    _require_numpy()
    return phases.tobytes()


def bytes_to_phases(data: bytes, dim: int = 512) -> "np.ndarray":
    """
    将字节反序列化为相位向量

    需要 .copy() 调用，因为 frombuffer 返回只读视图。
    调用方期望可变数组。

    Args:
        data: 序列化字节
        dim: 向量维度

    Returns:
        相位向量
    """
    _require_numpy()
    return np.frombuffer(data, dtype=np.float64).copy()


def snr_estimate(dim: int, n_items: int) -> float:
    """
    估计 holographic 存储的信噪比

    当 n_items > 0 时，SNR = sqrt(dim / n_items)，否则为 inf。

    当 n_items > dim / 4 时，SNR 低于 2.0，意味着检索错误可能增加。
    超过此阈值时记录警告。

    Args:
        dim: 向量维度
        n_items: 存储的项目数

    Returns:
        信噪比估计
    """
    _require_numpy()

    if n_items <= 0:
        return float("inf")

    snr = math.sqrt(dim / n_items)

    if snr < 2.0:
        logger.warning(
            "HRR storage near capacity: SNR=%.2f (dim=%d, n_items=%d). "
            "Retrieval accuracy may degrade. Consider increasing dim or reducing stored items.",
            snr, dim, n_items,
        )

    return snr


def compute_similarity_normalized(query_vec: "np.ndarray", memory_vec: "np.ndarray") -> float:
    """
    计算归一化的相似度分数 [0, 1]

    Args:
        query_vec: 查询向量
        memory_vec: 记忆向量

    Returns:
        归一化相似度 [0, 1]
    """
    sim = similarity(query_vec, memory_vec)
    # 将 [-1, 1] 映射到 [0, 1]
    return (sim + 1.0) / 2.0
