"""Context Compressor - 上下文压缩引擎

参考 Hermes Agent 的上下文压缩机制，实现有损摘要压缩。

功能：
1. 自动检测上下文长度
2. 智能选择要压缩的内容
3. 生成摘要保留关键信息
4. 维护压缩历史的父子关系
"""

import json
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging


@dataclass
class CompressionResult:
    """压缩结果"""
    original_count: int  # 原始消息数
    compressed_count: int  # 压缩后消息数
    summary: str  # 生成的摘要
    compressed_messages: List[Dict[str, Any]]  # 压缩后的消息列表
    parent_messages: List[Dict[str, Any]]  # 被压缩的原始消息（用于追踪）
    compression_ratio: float  # 压缩率
    timestamp: float = field(default_factory=time.time)
    compression_type: str = "summary"  # 压缩类型


class ContextCompressor(ABC):
    """上下文压缩抽象基类"""

    @abstractmethod
    async def compress(
        self,
        messages: List[Dict[str, Any]],
        max_messages: int = 20
    ) -> CompressionResult:
        """
        压缩消息列表

        Args:
            messages: 原始消息列表
            max_messages: 压缩后保留的最大消息数

        Returns:
            CompressionResult: 压缩结果
        """
        pass

    @abstractmethod
    def estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """估算消息的 token 数"""
        pass


class SummaryCompressor(ContextCompressor):
    """
    基于摘要的上下文压缩器

    策略：
    1. 保留最近 N 条消息（工作记忆）
    2. 将早期消息压缩为摘要
    3. 摘要包含关键信息和话题
    """

    def __init__(self, recent_messages: int = 10, summary_prompt: Optional[str] = None):
        """
        Args:
            recent_messages: 保留的最近消息数
            summary_prompt: 自定义摘要提示词
        """
        self.recent_messages = recent_messages
        self.summary_prompt = summary_prompt or self._default_summary_prompt()
        self.logger = logging.getLogger(self.__class__.__name__)

    def _default_summary_prompt(self) -> str:
        """默认摘要提示词"""
        return """请将以下对话压缩为简洁的摘要。

要求：
1. 保留关键信息、决策、结论
2. 提取涉及的主题和话题
3. 记录重要的用户偏好和习惯
4. 忽略重复的寒暄和次要细节

对话内容：
{content}

请生成一个结构化摘要，格式如下：
## 话题
[主要讨论的主题]

## 关键信息
- [关键点1]
- [关键点2]

## 决定/结论
[如有]

## 涉及偏好
[如有用户偏好]
"""

    def estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """简单估算 token 数（中文约 1 token/字符，英文约 4 token/词）"""
        total_chars = 0
        for msg in messages:
            content = msg.get('content', '')
            # 简单估算：中文按字符计，英文按空格分割后计数
            chinese_chars = sum(1 for c in content if '\u4e00' <= c <= '\u9fff')
            english_words = len(content.split())
            total_chars += chinese_chars + english_words * 5  # 英文一个词约5个字符
        return int(total_chars * 0.6)  # 压缩系数

    async def compress(
        self,
        messages: List[Dict[str, Any]],
        max_messages: int = 20
    ) -> CompressionResult:
        """
        执行上下文压缩

        策略：
        1. 如果消息数 <= max_messages，不压缩
        2. 保留最近的 recent_messages 条消息
        3. 其余消息压缩为摘要
        """
        if len(messages) <= max_messages:
            return CompressionResult(
                original_count=len(messages),
                compressed_count=len(messages),
                summary="",
                compressed_messages=messages,
                parent_messages=[],
                compression_ratio=1.0
            )

        # 保留最近的消息
        recent = messages[-self.recent_messages:] if self.recent_messages > 0 else []

        # 计算要压缩的消息
        if self.recent_messages > 0:
            to_compress = messages[:-self.recent_messages]
        else:
            # 如果 recent_messages 为 0，保留 max_messages 条，压缩其余的
            to_compress = messages[:-max_messages] if max_messages > 0 else messages[:-1]

        if not to_compress:
            return CompressionResult(
                original_count=len(messages),
                compressed_count=len(messages),
                summary="",
                compressed_messages=messages,
                parent_messages=[],
                compression_ratio=1.0
            )

        # 生成摘要
        summary = self._generate_summary(to_compress)

        # 创建压缩后的消息
        compressed_messages = []

        # 添加摘要消息
        compressed_messages.append({
            'role': 'system',
            'content': f"[对话历史摘要 - 可展开查看详情]\n\n{summary}",
            'timestamp': time.time(),
            'metadata': {
                'type': 'compressed_summary',
                'original_count': len(to_compress),
                'compression_type': 'summary'
            }
        })

        # 添加最近的消息
        compressed_messages.extend(recent)

        compression_ratio = len(compressed_messages) / len(messages)

        self.logger.info(
            f"Compressed {len(messages)} messages to {len(compressed_messages)} "
            f"(ratio: {compression_ratio:.2%})"
        )

        return CompressionResult(
            original_count=len(messages),
            compressed_count=len(compressed_messages),
            summary=summary,
            compressed_messages=compressed_messages,
            parent_messages=to_compress,
            compression_ratio=compression_ratio
        )

    def _generate_summary(self, messages: List[Dict[str, Any]]) -> str:
        """生成对话摘要"""
        # 构建对话文本
        content_parts = []
        for msg in messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            if content:
                content_parts.append(f"{role}: {content}")

        full_content = "\n".join(content_parts)

        # 截断过长内容
        if len(full_content) > 2000:
            full_content = full_content[:2000] + "..."

        # 格式化提示词
        prompt = self.summary_prompt.format(content=full_content)

        # TODO: 这里应该调用 LLM 生成摘要
        # 暂时返回简单摘要
        return self._simple_summary(messages)

    def _simple_summary(self, messages: List[Dict[str, Any]]) -> str:
        """简单的摘要生成（无 LLM）"""
        topics = set()
        key_points = []
        user_prefs = []

        for msg in messages:
            content = msg.get('content', '').lower()

            # DEPRECATED: 关键词提取应该由 LLM 完成，这里仅作为降级使用
            # 简化：不做关键词提取，让 LLM 在生成摘要时自己识别
            pass  # 不再使用硬编码关键词

        summary_parts = []

        # DEPRECATED: 应该由 LLM 直接生成摘要
        if not summary_parts:
            summary_parts.append(f"## 摘要\n- 共 {len(messages)} 条对话")

        return "\n\n".join(summary_parts)


class HierarchicalCompressor(ContextCompressor):
    """
    分层压缩器 - 参考 MemGPT 的分层记忆架构

    层级：
    1. Working Memory (工作记忆) - 最近 10 条消息
    2. Core Memory (核心记忆) - 压缩后的摘要
    3. Archive Memory (归档记忆) - 更早期的历史
    """

    def __init__(
        self,
        working_size: int = 10,
        core_size: int = 5,
        archive_threshold: int = 50
    ):
        self.working_size = working_size
        self.core_size = core_size
        self.archive_threshold = archive_threshold
        self.logger = logging.getLogger(self.__class__.__name__)
        self.summary_compressor = SummaryCompressor(recent_messages=0)

    def estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        return self.summary_compressor.estimate_tokens(messages)

    async def compress(
        self,
        messages: List[Dict[str, Any]],
        max_messages: int = 20
    ) -> CompressionResult:
        """
        执行分层压缩

        策略：
        1. 工作记忆：保留最近 working_size 条消息
        2. 核心记忆：将中间部分压缩为核心摘要
        3. 归档记忆：早期历史标记但不保留详细内容
        """
        total = len(messages)

        if total <= max_messages:
            return CompressionResult(
                original_count=total,
                compressed_count=total,
                summary="",
                compressed_messages=messages,
                parent_messages=[],
                compression_ratio=1.0
            )

        compressed_messages = []

        # 1. 归档标记（如果有早期历史）
        if total > self.archive_threshold:
            archive_msg = {
                'role': 'system',
                'content': f"[早期对话历史 - 共 {total - self.archive_threshold} 条消息已归档]",
                'timestamp': messages[0].get('timestamp', time.time()),
                'metadata': {
                    'type': 'archive_marker',
                    'count': total - self.archive_threshold,
                    'first_timestamp': messages[0].get('timestamp', 0),
                    'last_timestamp': messages[self.archive_threshold - 1].get('timestamp', 0)
                }
            }
            compressed_messages.append(archive_msg)
            messages = messages[self.archive_threshold:]

        # 2. 核心记忆摘要
        if len(messages) > self.working_size + self.core_size:
            to_summarize = messages[:len(messages) - self.working_size]
            working = messages[len(messages) - self.working_size:]

            core_result = await self.summary_compressor.compress(
                to_summarize,
                max_messages=self.core_size
            )

            if core_result.summary:
                core_msg = {
                    'role': 'system',
                    'content': f"[对话核心记忆]\n\n{core_result.summary}",
                    'timestamp': time.time(),
                    'metadata': {
                        'type': 'core_memory',
                        'original_count': len(to_summarize)
                    }
                }
                compressed_messages.append(core_msg)

            compressed_messages.extend(working)
        else:
            compressed_messages.extend(messages)

        compression_ratio = len(compressed_messages) / total

        self.logger.info(
            f"Hierarchical compression: {total} -> {len(compressed_messages)} "
            f"(ratio: {compression_ratio:.2%})"
        )

        return CompressionResult(
            original_count=total,
            compressed_count=len(compressed_messages),
            summary="分层压缩完成",
            compressed_messages=compressed_messages,
            parent_messages=messages[len(compressed_messages):],
            compression_ratio=compression_ratio,
            compression_type="hierarchical"
        )


class ContextCompressionManager:
    """
    上下文压缩管理器

    协调多个压缩器，自动选择最佳压缩策略
    """

    def __init__(
        self,
        max_tokens: int = 8000,
        compressor_type: str = "summary"
    ):
        self.max_tokens = max_tokens
        self.compression_history: List[CompressionResult] = []

        if compressor_type == "hierarchical":
            self.compressor = HierarchicalCompressor()
        else:
            self.compressor = SummaryCompressor()

        self.logger = logging.getLogger(self.__class__.__name__)

    async def process(
        self,
        messages: List[Dict[str, Any]],
        force_compress: bool = False
    ) -> Tuple[List[Dict[str, Any]], Optional[CompressionResult]]:
        """
        处理消息列表，必要时进行压缩

        Args:
            messages: 原始消息列表
            force_compress: 是否强制压缩

        Returns:
            Tuple: (处理后的消息, 压缩结果如果有)
        """
        # 估算当前 token 数
        current_tokens = self.compressor.estimate_tokens(messages)

        # 如果未超过限制且不强制压缩，直接返回
        if current_tokens <= self.max_tokens and not force_compress:
            return messages, None

        # 执行压缩
        max_messages = int(self.max_tokens / 4)  # 估算每条消息约 4 tokens
        result = await self.compressor.compress(messages, max_messages=max_messages)

        # 记录压缩历史
        self.compression_history.append(result)

        # 限制历史记录大小
        if len(self.compression_history) > 100:
            self.compression_history = self.compression_history[-100:]

        self.logger.info(
            f"Context compressed: {result.original_count} -> {result.compressed_count} messages"
        )

        return result.compressed_messages, result

    def get_compression_stats(self) -> Dict[str, Any]:
        """获取压缩统计信息"""
        if not self.compression_history:
            return {
                'total_compressions': 0,
                'average_ratio': 0,
                'total_messages_saved': 0
            }

        return {
            'total_compressions': len(self.compression_history),
            'average_ratio': sum(c.compression_ratio for c in self.compression_history) / len(self.compression_history),
            'total_messages_saved': sum(
                c.original_count - c.compressed_count
                for c in self.compression_history
            ),
            'last_compression': {
                'timestamp': self.compression_history[-1].timestamp,
                'ratio': self.compression_history[-1].compression_ratio
            }
        }
