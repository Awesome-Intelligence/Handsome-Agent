"""Streaming Think Scrubber - 流式推理内容过滤器

过滤流式输出中的 <think>... 等推理标签，
同时提取推理内容供单独显示。
"""

from typing import Optional, Tuple
import re


class StreamingThinkScrubber:
    """
    流式推理标签清除器
    
    使用状态机逐块处理流式输出，过滤掉推理标签，
    同时提取推理内容供单独显示。
    
    用法::
    
        scrubber = StreamingThinkScrubber()
        
        # 处理每个流式增量
        while text := stream.read():
            visible, reasoning = scrubber.feed(text)
            if visible:
                print(visible, end="", flush=True)  # 输出可见内容
            if reasoning:
                print(f"[推理] {reasoning}")  # 输出推理内容
    """
    
    # 推理标签（英文）- 开放标签
    OPEN_TAGS_EN = ["think", "thinking", "reasoning", "thought", "REASONING_SCRATCHPAD"]
    # 推理标签（中文）
    OPEN_TAGS_ZH = ["思考", "推理", "思维"]
    
    # 完整的开放标签（包括特殊符号形式）
    # 包括 <think> 和 <think> 等形式
    _open_en = tuple(f"<{tag}>" for tag in OPEN_TAGS_EN)
    _open_zh = tuple(f"<{tag}>" for tag in OPEN_TAGS_ZH)
    ALL_OPEN_TAGS = _open_en + _open_zh
    
    # 完整的关闭标签（包括英文和中文方括号）
    _close_en = tuple(f"</{tag}>" for tag in OPEN_TAGS_EN)
    _close_zh = tuple(f"</{tag}>" for tag in OPEN_TAGS_ZH)
    ALL_CLOSE_TAGS = _close_en + _close_zh
    
    def __init__(self):
        self._buf = ""
        self._in_block = False
        self._reasoning_buf = ""
        self._pending_close = ""
    
    def feed(self, text: str) -> Tuple[str, Optional[str]]:
        """
        处理流式文本增量
        
        Args:
            text: 文本增量
            
        Returns:
            (visible_text, reasoning_text) 元组
            visible_text: 可见内容（过滤后的）
            reasoning_text: 推理内容（有的话）
        """
        if not text:
            return "", None
        
        self._buf += text
        return self._process()
    
    def _process(self) -> Tuple[str, Optional[str]]:
        """处理缓冲区，返回可见内容和推理内容"""
        visible_parts = []
        reasoning_parts = []
        
        while self._buf:
            if self._in_block:
                # 等待关闭标签
                close_result = self._find_close_tag()
                if close_result is None:
                    # 没有找到关闭标签，保留部分内容等待下一块
                    # 找出可能被部分关闭标签污染的内容
                    held = self._max_partial_suffix(self._buf, self.ALL_CLOSE_TAGS)
                    if held > 0:
                        # 有部分关闭标签，保持等待
                        self._buf = self._buf[-held:]
                    else:
                        # 完全是推理内容，累积
                        reasoning_parts.append(self._buf)
                        self._buf = ""
                    break
                else:
                    # 找到关闭标签
                    close_idx, close_len, close_tag = close_result
                    reasoning_parts.append(self._buf[:close_idx])
                    self._buf = self._buf[close_idx + close_len:]
                    self._in_block = False
            else:
                # 寻找开放标签
                open_result = self._find_open_tag()
                if open_result is None:
                    # 没有更多开放标签
                    if self._buf.strip():
                        visible_parts.append(self._buf)
                    self._buf = ""
                    break
                else:
                    # 找到开放标签
                    open_idx, open_len, open_tag = open_result
                    
                    # 添加开放标签前的内容
                    if open_idx > 0:
                        visible_parts.append(self._buf[:open_idx])
                    
                    self._buf = self._buf[open_idx + open_len:]
                    self._in_block = True
        
        visible = "".join(visible_parts)
        reasoning = "".join(reasoning_parts) if reasoning_parts else None
        
        return visible, reasoning if reasoning else None
    
    def _find_open_tag(self) -> Optional[Tuple[int, int, str]]:
        """查找下一个开放标签"""
        if not self._buf:
            return None
        
        # 找到最近的开放标签
        best_idx = -1
        best_len = 0
        best_tag = ""
        
        for tag in self.ALL_OPEN_TAGS:
            idx = self._buf.find(tag)
            if idx != -1 and (best_idx == -1 or idx < best_idx):
                best_idx = idx
                best_len = len(tag)
                best_tag = tag
        
        if best_idx == -1:
            return None
        
        return best_idx, best_len, best_tag
    
    def _find_close_tag(self) -> Optional[Tuple[int, int, str]]:
        """查找关闭标签"""
        if not self._buf:
            return None
        
        # 找到最近的关闭标签（跳过空字符串）
        best_idx = -1
        best_len = 0
        best_tag = ""
        
        for tag in self.ALL_CLOSE_TAGS:
            if not tag:  # 跳过空字符串
                continue
            idx = self._buf.find(tag)
            if idx != -1 and (best_idx == -1 or idx < best_idx):
                best_idx = idx
                best_len = len(tag)
                best_tag = tag
        
        if best_idx == -1:
            return None
        
        return best_idx, best_len, best_tag
    
    def _max_partial_suffix(self, text: str, tags: tuple) -> int:
        """找出文本末尾可能是不完整关闭标签的最大长度"""
        max_len = 0
        for tag in tags:
            if text.endswith(tag[:min(len(tag), 10)]):
                # 可能是部分关闭标签
                for i in range(1, len(tag) + 1):
                    if text.endswith(tag[:i]):
                        max_len = max(max_len, i)
        return max_len
    
    def flush(self) -> Tuple[str, Optional[str]]:
        """刷新缓冲区，返回剩余内容"""
        if not self._buf:
            return "", None
        
        if self._in_block:
            # 开放标签未关闭，可能是不完整的推理内容
            reasoning = self._buf
            self._buf = ""
            return "", reasoning
        
        visible = self._buf
        self._buf = ""
        return visible, None
    
    def reset(self) -> None:
        """重置状态"""
        self._buf = ""
        self._in_block = False
        self._reasoning_buf = ""
        self._pending_close = ""
    
    @property
    def is_in_thinking(self) -> bool:
        """是否正在处理推理块"""
        return self._in_block


def extract_thinking_tags(text: str) -> Tuple[str, Optional[str]]:
    """
    简单版本的推理标签提取（非流式）
    
    用法::
    
        visible, reasoning = extract_thinking_tags(
            "<think> some thinking </think> actual response"
        )
        # visible = " actual response"
        # reasoning = "some thinking"
    """
    scrubber = StreamingThinkScrubber()
    visible, reasoning = scrubber.feed(text)
    remaining_visible, remaining_reasoning = scrubber.flush()
    return visible + remaining_visible, reasoning or remaining_reasoning


# 编译正则表达式用于非流式场景
_THINK_PATTERN = re.compile(
    r'<(?:think|thinking|reasoning|thought|REASONING_SCRATCHPAD|思考|推理|思维)>'
    r'([\s\S]*?)'
    r'</(?:think|thinking|reasoning|thought|REASONING_SCRATCHPAD|思考|推理|思维)>',
    re.IGNORECASE
)


def strip_thinking_tags(text: str) -> str:
    """移除所有推理标签及其内容"""
    return _THINK_PATTERN.sub('', text)


def extract_thinking_content(text: str) -> Optional[str]:
    """提取推理内容（非流式）"""
    matches = _THINK_PATTERN.findall(text)
    if matches:
        return '\n'.join(m.strip() for m in matches if m.strip())
    return None