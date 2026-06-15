#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StatusBar Widget - Textual UI Status Bar Component

🚪 Access - 💬 CLI - TUI Widgets - StatusBar

显示模型信息、Token 计数、上下文占用率等状态信息。
使用牛油果绿主题配色，支持根据上下文占用率显示不同颜色。

Features:
- 模型名称和提供商显示
- 会话 ID 显示（可选）
- Token 计数（prompt/completion）
- 上下文占用率进度条
- 根据占用率变色（绿色/黄色/红色）
- 实时状态更新机制
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

# Textual 框架导入（带降级机制）
TEXTUAL_AVAILABLE = True
try:
    from textual.widget import Widget
    from textual.message import Message
except ImportError:
    TEXTUAL_AVAILABLE = False
    Widget = object  # type: ignore
    Message = object  # type: ignore

# i18n 支持
try:
    from common.i18n import get_i18n
except ImportError:
    # 降级：简单的翻译函数
    def get_i18n():
        class SimpleI18n:
            def t(self, key, default=None, **kwargs):
                return default or key
        return SimpleI18n()

# 日志支持
try:
    from common.logging_manager import get_access_logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    def get_access_logger(*args, **kwargs):
        return logging.getLogger("HandsomeAgent")


# ============================================================================
# 主题颜色常量（牛油果绿）
# ============================================================================

# 牛油果绿主题 - Avocado Theme
AVOCADO_PRIMARY = "#8B9A46"       # rgb(139,154,70) - 主色
AVOCADO_BRIGHT = "#A0B45A"        # rgb(160,180,90) - 亮色
AVOCADO_DIM = "#647030"           # rgb(100,120,50) - 暗色
AVOCADO_DARK = "#465020"          # rgb(70,90,32) - 深色

# 状态颜色
COLOR_SUCCESS = "#4CAF50"        # 绿色 - 正常
COLOR_WARNING = "#FF9800"        # 橙色 - 警告
COLOR_DANGER = "#F44336"         # 红色 - 危险
COLOR_INFO = "#2196F3"           # 蓝色 - 信息

# 背景和文字颜色
WHITE = "white"
GRAY_DIM = "#888888"
SURFACE = "#1a1a1a"


# ============================================================================
# StatusBar 消息定义
# ============================================================================

class StatusBarUpdated(Message):
    """状态栏更新消息"""
    def __init__(self, sender: Widget, field: str, value: any) -> None:
        """初始化状态更新消息
        
        Args:
            sender: 发送者组件
            field: 更新的字段名
            value: 新的值
        """
        super().__init__()
        self.field = field
        self.value = value


# ============================================================================
# StatusBar Widget
# ============================================================================

class StatusBar(Widget):
    """Textual 状态栏组件
    
    显示当前模型状态信息，包括：
    - 模型名称和提供商
    - 会话 ID
    - Token 计数（prompt/completion）
    - 上下文占用率进度条
    
    Attributes:
        COMPONENT_CLASSES: CSS 类定义
        model_name: 当前模型名称
        provider: 模型提供商
        session_id: 会话 ID
        prompt_tokens: Prompt token 数量
        completion_tokens: Completion token 数量
        context_used: 已使用的上下文 token
        context_total: 上下文总容量
    """
    
    COMPONENT_CLASSES = {
        "model-info",
        "token-info",
        "context-bar",
        "session-info",
    }
    
    def __init__(
        self,
        model_name: str = "Unknown",
        provider: str = "",
        session_id: Optional[str] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        context_used: int = 0,
        context_total: int = 128000,
        **kwargs
    ) -> None:
        """初始化状态栏
        
        Args:
            model_name: 模型名称
            provider: 模型提供商
            session_id: 会话 ID（可选）
            prompt_tokens: Prompt token 数量
            completion_tokens: Completion token 数量
            context_used: 已使用的上下文 token
            context_total: 上下文总容量
            **kwargs: 传递给父类的参数
        """
        super().__init__(**kwargs)
        self.model_name = model_name
        self.provider = provider
        self.session_id = session_id
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.context_used = context_used
        self.context_total = context_total
        self._logger = get_access_logger("StatusBar", sublayer="cli")
        self._update_scheduled = False
    
    # ========================================================================
    # 状态更新方法
    # ========================================================================
    
    def update_model(self, model_name: str, provider: str = "") -> None:
        """更新模型信息
        
        Args:
            model_name: 新的模型名称
            provider: 新的提供商名称
        """
        self.model_name = model_name
        self.provider = provider
        self._schedule_update("model")
        self.post_message(StatusBarUpdated(self, "model", (model_name, provider)))
        self._logger.debug(f"Model updated: {model_name} ({provider})")
    
    def update_token_count(self, prompt: int, completion: int) -> None:
        """更新 Token 计数
        
        Args:
            prompt: 新的 prompt token 数量
            completion: 新的 completion token 数量
        """
        self.prompt_tokens = prompt
        self.completion_tokens = completion
        self._schedule_update("tokens")
        self.post_message(StatusBarUpdated(self, "tokens", (prompt, completion)))
        self._logger.debug(f"Token count updated: prompt={prompt}, completion={completion}")
    
    def update_context_usage(self, used: int, total: int) -> None:
        """更新上下文占用
        
        Args:
            used: 已使用的 token 数量
            total: 上下文总容量
        """
        self.context_used = used
        self.context_total = total
        self._schedule_update("context")
        self.post_message(StatusBarUpdated(self, "context", (used, total)))
        ratio = self._get_context_ratio() * 100
        self._logger.debug(f"Context usage updated: {used}/{total} ({ratio:.1f}%)")
    
    def update_session_id(self, session_id: Optional[str]) -> None:
        """更新会话 ID
        
        Args:
            session_id: 新的会话 ID（None 表示隐藏）
        """
        self.session_id = session_id
        self._schedule_update("session")
        self.post_message(StatusBarUpdated(self, "session", session_id))
        self._logger.debug(f"Session ID updated: {session_id}")
    
    def _schedule_update(self, field: str) -> None:
        """调度 UI 更新（避免频繁刷新）"""
        if not self._update_scheduled:
            self._update_scheduled = True
            self.call_next(self._do_update)
    
    def _do_update(self) -> None:
        """执行 UI 更新"""
        self._update_scheduled = False
        self.refresh()
    
    # ========================================================================
    # 辅助方法
    # ========================================================================
    
    def _get_context_ratio(self) -> float:
        """获取上下文占用率
        
        Returns:
            占用率（0.0 - 1.0）
        """
        if self.context_total <= 0:
            return 0.0
        return min(self.context_used / self.context_total, 1.0)
    
    def _get_context_color(self) -> str:
        """获取上下文占用颜色
        
        Returns:
            根据占用率返回对应颜色：
            - < 50%: 绿色（正常）
            - 50-80%: 橙色（警告）
            - > 80%: 红色（危险）
        """
        ratio = self._get_context_ratio()
        if ratio < 0.5:
            return COLOR_SUCCESS
        elif ratio < 0.8:
            return COLOR_WARNING
        else:
            return COLOR_DANGER
    
    def _format_number(self, num: int) -> str:
        """格式化数字（添加千位分隔符）
        
        Args:
            num: 要格式化的数字
            
        Returns:
            格式化后的字符串，如 "1,234"
        """
        return f"{num:,}"
    
    def _format_percentage(self, value: int, total: int) -> str:
        """计算并格式化百分比
        
        Args:
            value: 数值
            total: 总数
            
        Returns:
            百分比字符串，如 "62%"
        """
        if total <= 0:
            return "0%"
        ratio = value / total * 100
        return f"{ratio:.0f}%"
    
    def _get_context_bar(self, width: int = 12) -> str:
        """生成上下文占用进度条
        
        Args:
            width: 进度条总宽度（字符数）
            
        Returns:
            进度条字符串，如 "[████████░░░░]"
        """
        ratio = self._get_context_ratio()
        filled = int(ratio * width)
        empty = width - filled
        color = self._get_context_color()
        
        bar = f"[{color}{'█' * filled}{GRAY_DIM}{'░' * empty}{WHITE}]"
        return bar
    
    # ========================================================================
    # 翻译辅助方法
    # ========================================================================
    
    def _translate(self, key: str, default: str) -> str:
        """获取翻译文本，如果不存在则返回默认文本
        
        Args:
            key: 翻译 key
            default: 默认文本
            
        Returns:
            翻译后的文本或默认文本
        """
        i18n = get_i18n()
        result = i18n.t(key, default=default)
        # 如果返回的是 key 本身，说明翻译不存在
        if result == key:
            return default
        return result
    
    # ========================================================================
    # 渲染方法
    # ========================================================================
    
    def render(self) -> str:
        """渲染状态栏内容
        
        Returns:
            格式化的状态栏字符串
        """
        # 模型信息
        if self.provider:
            model_display = f"{self.provider}:{self.model_name}"
        else:
            model_display = self.model_name
        
        # Token 信息
        total_tokens = self.prompt_tokens + self.completion_tokens
        token_str = f"{self._format_number(total_tokens)}/{self._format_number(self.context_total)}"
        token_percentage = self._format_percentage(total_tokens, self.context_total)
        
        # 上下文占用条
        context_bar = self._get_context_bar(12)
        
        # 翻译文本
        label_token = self._translate("tui.status.token", "Token")
        label_session = self._translate("tui.status.session", "Session")
        
        # 会话 ID
        session_str = ""
        if self.session_id:
            session_str = f" | {label_session}: {self.session_id[:8]}..."
        
        # 组装状态栏
        parts = [
            f"[{AVOCADO_BRIGHT}]●[/{AVOCADO_BRIGHT}]",  # 连接状态指示器
            f"[{AVOCADO_PRIMARY}]{model_display}[/{AVOCADO_PRIMARY}]",
            f"[{GRAY_DIM}]|[/{GRAY_DIM}]",
            f"{label_token}: {token_str} ({token_percentage})",
            f"[{GRAY_DIM}]|[/{GRAY_DIM}]",
            context_bar,
            session_str,
        ]
        
        return " ".join(part for part in parts if part)
    
    def on_mount(self) -> None:
        """组件挂载时初始化"""
        self._logger.info("StatusBar mounted")
        self._schedule_update("initial")