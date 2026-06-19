#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ApprovalDialog - 权限审批确认对话框

🚪 Access - 💬 CLI - TUI Widgets - ApprovalDialog

提供工具执行前的确认对话框，支持：
- 操作描述显示
- 风险等级指示（低/中/高）
- 确认/取消按钮
- 键盘快捷键（Enter 确认，Esc 取消）
- 敏感操作警告样式
"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable, TYPE_CHECKING

# Textual 框架导入（带降级机制）
TEXTUAL_AVAILABLE = True
try:
    from textual.app import ComposeResult
    from textual.widgets import Static, Button, Label
    from textual.containers import Container, VerticalScroll, HorizontalLayout
    from textual.message import Message
except ImportError:
    TEXTUAL_AVAILABLE = False
    Static = object  # type: ignore
    Button = object  # type: ignore
    Label = object  # type: ignore
    Container = object  # type: ignore
    VerticalScroll = object  # type: ignore
    HorizontalLayout = object  # type: ignore
    Message = object  # type: ignore

# i18n 支持
try:
    from common.i18n import get_i18n, t
except ImportError:
    # 降级：简单的翻译函数
    def get_i18n():
        class SimpleI18n:
            def t(self, key, default=None, **kwargs):
                return default or key
        return SimpleI18n()
    
    def t(key, default=None, **kwargs):
        return default or key

# 日志支持
try:
    from common.logging_manager import get_access_logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    def get_access_logger(*args, **kwargs):
        return logging.getLogger("HandsomeAgent")


# ============================================================================
# 审批模式枚举
# ============================================================================

class ApprovalMode(Enum):
    """审批模式枚举
    
    控制工具执行前的确认行为：
    - AUTO: 自动执行，不确认
    - SUGGEST: 建议确认（仅敏感操作确认）
    - MANUAL: 完全手动（所有操作确认）
    """
    AUTO = "auto"       # 自动执行，不确认
    SUGGEST = "suggest" # 建议确认（敏感操作确认）
    MANUAL = "manual"   # 完全手动（所有操作确认）
    
    @classmethod
    def from_string(cls, value: str) -> "ApprovalMode":
        """从字符串转换为审批模式
        
        Args:
            value: 字符串值（auto/suggest/manual）
            
        Returns:
            对应的 ApprovalMode
        """
        value = value.lower().strip()
        for mode in cls:
            if mode.value == value:
                return mode
        return cls.SUGGEST  # 默认值
    
    def __str__(self) -> str:
        return self.value


# ============================================================================
# 风险等级枚举
# ============================================================================

class RiskLevel(Enum):
    """风险等级枚举"""
    LOW = "low"      # 低风险
    MEDIUM = "medium" # 中风险
    HIGH = "high"    # 高风险
    
    @classmethod
    def from_operation(cls, operation: str, sensitive_operations: list[str]) -> "RiskLevel":
        """根据操作名称判断风险等级
        
        Args:
            operation: 操作名称
            sensitive_operations: 敏感操作列表
            
        Returns:
            风险等级
        """
        # 高风险操作列表
        HIGH_RISK_OPERATIONS = [
            "delete_file",
            "delete_directory",
            "remove_directory",
            "execute_command",
            "run_shell",
        ]
        
        # 中风险操作列表
        MEDIUM_RISK_OPERATIONS = [
            "write_file",
            "create_directory",
            "move_file",
            "copy_file",
        ]
        
        operation_lower = operation.lower()
        
        # 检查高风险
        for high_op in HIGH_RISK_OPERATIONS:
            if high_op in operation_lower:
                return cls.HIGH
        
        # 检查中风险
        for medium_op in MEDIUM_RISK_OPERATIONS:
            if medium_op in operation_lower:
                return cls.MEDIUM
        
        return cls.LOW
    
    def get_color(self) -> str:
        """获取风险等级对应的颜色
        
        Returns:
            CSS 变量名
        """
        colors = {
            "low": "$success",     # 绿色
            "medium": "$warning",   # 橙色
            "high": "$error",       # 红色
        }
        return colors.get(self.value, "$text-muted")
    
    def get_icon(self) -> str:
        """获取风险等级对应的图标
        
        Returns:
            图标字符串
        """
        icons = {
            "low": "✓",
            "medium": "⚠",
            "high": "⚠",
        }
        return icons.get(self.value, "?")
    
    def get_label(self) -> str:
        """获取风险等级对应的标签
        
        Returns:
            标签文本
        """
        return t(f"approval.risk.{self.value}", self.value.upper())


# ============================================================================
# 敏感操作定义
# ============================================================================

SENSITIVE_OPERATIONS = [
    "delete_file",
    "delete_directory",
    "remove_directory",
    "execute_command",
    "run_shell",
    "write_file",  # 某些路径可能敏感
]


# ============================================================================
# 审批对话框样式 (Frogmouth 半透明风格)
# ============================================================================

APPROVAL_DIALOG_CSS = """
/* 审批对话框容器 */
ApprovalDialog {
    align: center middle;
    border: round $primary 50%;     /* 半透明圆角边框 */
    background: $boost;            /* 提升背景 */
    width: 60%;
    max-height: 70%;
    padding: 1 2;
}

/* 审批对话框内部容器 */
#approval-container {
    width: 100%;
    height: auto;
    background: $boost;
    border: round $primary 50%;     /* 半透明边框 */
    padding: 1 2;
}

/* 标题头 */
#approval-header {
    width: 100%;
    height: auto;
    padding: 0 1;
    margin-bottom: 1;
}

/* 风险等级样式 - 使用半透明背景 */

/* 高风险 */
.risk-high,
.risk-high > #approval-container {
    background: $error 15%;        /* 红色淡背景 */
    border: thick $error 50%;       /* 红色半透明边框 */
}

/* 中风险 */
.risk-medium,
.risk-medium > #approval-container {
    background: $warning 10%;       /* 橙色淡背景 */
    border: thick $warning 50%;      /* 橙色半透明边框 */
}

/* 低风险 */
.risk-low,
.risk-low > #approval-container {
    background: $success 10%;       /* 绿色淡背景 */
    border: thick $success 50%;      /* 绿色半透明边框 */
}

/* 风险徽章 */
#risk-badge {
    width: 100%;
    height: auto;
    margin-bottom: 1;
}

/* 操作信息 */
#operation-name {
    width: 100%;
    height: auto;
    margin-bottom: 1;
}

#operation-preview {
    width: 100%;
    height: auto;
    margin-bottom: 1;
}

/* 警告文本 */
.warning-text {
    color: $error;
    text-style: bold;
}

/* 提示文本 */
.hint-text {
    color: $text-muted;
}

/* 按钮区域 */
#approval-footer {
    width: 100%;
    height: auto;
    layout: horizontal;
    align: center middle;
    spacing: 1;
}

#cancel-button {
    width: auto;
    min-width: 10;
    border: blank;
    background: $surface 20%;
}

#cancel-button:hover {
    background: $surface 40%;
    border: heavy $surface;
}

#confirm-button {
    width: auto;
    min-width: 10;
    border: blank;
    background: $success 20%;
}

#confirm-button:hover {
    background: $success 40%;
    border: heavy $success;
}
"""


# ============================================================================
# 审批消息类
# ============================================================================

class ApprovalRequested(Message):
    """审批请求消息
    
    当需要用户确认时发布此事件。
    
    Attributes:
        operation: 操作名称
        preview: 操作预览
        risk_level: 风险等级
    """
    
    def __init__(
        self,
        sender: "ApprovalDialog",
        operation: str,
        preview: str = "",
        risk_level: RiskLevel = RiskLevel.MEDIUM,
    ) -> None:
        super().__init__()
        self.operation = operation
        self.preview = preview
        self.risk_level = risk_level


class ApprovalConfirmed(Message):
    """审批确认消息
    
    当用户确认操作时发布此事件。
    
    Attributes:
        operation: 操作名称
    """
    
    def __init__(self, sender: "ApprovalDialog", operation: str) -> None:
        super().__init__()
        self.operation = operation


class ApprovalRejected(Message):
    """审批拒绝消息
    
    当用户拒绝操作时发布此事件。
    
    Attributes:
        operation: 操作名称
    """
    
    def __init__(self, sender: "ApprovalDialog", operation: str) -> None:
        super().__init__()
        self.operation = operation


# ============================================================================
# ApprovalDialog 组件
# ============================================================================

class ApprovalDialog(Container):
    """权限审批确认对话框
    
    提供工具执行前的确认界面，支持：
    - 操作描述显示
    - 风险等级指示
    - 确认/取消按钮
    - 键盘快捷键
    
    Attributes:
        operation: 操作名称
        preview: 操作预览
        risk_level: 风险等级
    """
    
    CSS = APPROVAL_DIALOG_CSS
    
    def __init__(
        self,
        operation: str,
        preview: str = "",
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        **kwargs
    ) -> None:
        """初始化审批对话框
        
        Args:
            operation: 操作名称
            preview: 操作预览/命令预览
            risk_level: 风险等级
            **kwargs: 传递给父类的参数
        """
        super().__init__(**kwargs)
        self.operation = operation
        self.preview = preview
        self.risk_level = risk_level
        self._logger = get_access_logger("ApprovalDialog", sublayer="cli")
        self._focus_button = "confirm"  # 默认焦点在确认按钮
    
    def compose(self) -> ComposeResult:
        """组合对话框布局
        
        Returns:
            ComposeResult: 组件生成器
        """
        i18n = get_i18n()
        
        # 添加风险等级类名
        risk_class = f"risk-{self.risk_level.value}"
        
        with VerticalScroll(id="approval-container", classes=risk_class):
            # 标题头
            yield Static(
                t("approval.title", "⚠ 操作确认"),
                id="approval-header"
            )
            
            # 风险等级指示器
            risk_color = self.risk_level.get_color()
            risk_icon = self.risk_level.get_icon()
            risk_label = self.risk_level.get_label()
            yield Label(
                f"[{risk_color}]{risk_icon}[/{risk_color}] "
                f"[{risk_color}]{risk_label}[/{risk_color}] - "
                f"{t('approval.risk.description', '风险等级')}",
                id="risk-badge"
            )
            
            # 操作信息
            yield Label(
                f"[bold]{t('approval.operation', '操作')}:[/] {self.operation}",
                id="operation-name"
            )
            
            # 操作预览（如果有）
            if self.preview:
                yield Label(
                    f"[bold]{t('approval.preview', '预览')}:[/] [dim]{self.preview}[/dim]",
                    id="operation-preview"
                )
            
            # 警告信息（高风险操作）
            if self.risk_level == RiskLevel.HIGH:
                yield Label(
                    f"[bold #F44336]⚠ {t('approval.warning.high', '警告：此操作不可逆！')}[/bold #F44336]",
                    id="warning-text"
                )
            
            # 提示信息
            yield Label(
                f"[dim]{t('approval.hint', '提示')}: [key-hint]Enter[/key-hint] "
                f"{t('approval.confirm', '确认')} | [key-hint]Esc[/key-hint] "
                f"{t('approval.cancel', '取消')}[/dim]",
                id="hint-text"
            )
            
            # 按钮区域
            with HorizontalLayout(id="approval-footer"):
                yield Button(
                    t("approval.button.cancel", "取消 [Esc]"),
                    id="cancel-button",
                    variant="default"
                )
                yield Button(
                    t("approval.button.confirm", "确认 [Enter]"),
                    id="confirm-button",
                    variant="primary" if self.risk_level != RiskLevel.HIGH else "error"
                )
    
    def on_mount(self) -> None:
        """组件挂载时设置焦点"""
        self._logger.debug(f"ApprovalDialog mounted for: {self.operation}")
        
        # 根据风险等级设置默认焦点
        if self.risk_level == RiskLevel.HIGH:
            self._focus_button = "cancel"
        
        # 聚焦到默认按钮
        button = self.query_one(f"#{self._focus_button}-button", Button)
        button.focus()
    
    def on_key(self, event: "Static.Key") -> None:
        """处理键盘事件
        
        Args:
            event: 键盘事件
        """
        key = event.key
        
        if key == "enter":
            self._confirm()
        elif key == "escape":
            self._reject()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮按下事件
        
        Args:
            event: 按钮按下事件
        """
        button_id = event.button.id
        
        if button_id == "confirm-button":
            self._confirm()
        elif button_id == "cancel-button":
            self._reject()
    
    def _confirm(self) -> None:
        """确认操作"""
        self._logger.info(f"Operation approved: {self.operation}")
        self.post_message(ApprovalConfirmed(self, self.operation))
        self.remove()
    
    def _reject(self) -> None:
        """拒绝操作"""
        self._logger.info(f"Operation rejected: {self.operation}")
        self.post_message(ApprovalRejected(self, self.operation))
        self.remove()


# ============================================================================
# 审批管理器
# ============================================================================

class ApprovalManager:
    """审批管理器
    
    管理工具执行前的审批流程。
    
    Attributes:
        mode: 当前审批模式
        sensitive_operations: 敏感操作列表
        _logger: 日志记录器
    """
    
    def __init__(
        self,
        mode: ApprovalMode = ApprovalMode.SUGGEST,
        sensitive_operations: list[str] | None = None,
    ) -> None:
        """初始化审批管理器
        
        Args:
            mode: 审批模式
            sensitive_operations: 敏感操作列表
        """
        self.mode = mode
        self.sensitive_operations = sensitive_operations or SENSITIVE_OPERATIONS.copy()
        self._logger = get_access_logger("ApprovalManager", sublayer="cli")
    
    def set_mode(self, mode: ApprovalMode | str) -> None:
        """设置审批模式
        
        Args:
            mode: 审批模式（枚举或字符串）
        """
        if isinstance(mode, str):
            mode = ApprovalMode.from_string(mode)
        self.mode = mode
        self._logger.info(f"Approval mode set to: {mode.value}")
    
    def should_approve(self, operation: str) -> bool:
        """判断操作是否需要审批
        
        Args:
            operation: 操作名称
            
        Returns:
            True 如果需要审批，否则 False
        """
        operation_lower = operation.lower()
        
        if self.mode == ApprovalMode.AUTO:
            # 自动模式：不需要审批
            return False
        elif self.mode == ApprovalMode.SUGGEST:
            # 建议模式：仅敏感操作需要审批
            return any(sop in operation_lower for sop in self.sensitive_operations)
        elif self.mode == ApprovalMode.MANUAL:
            # 手动模式：所有操作都需要审批
            return True
        
        return False
    
    def get_risk_level(self, operation: str) -> RiskLevel:
        """获取操作的风险等级
        
        Args:
            operation: 操作名称
            
        Returns:
            风险等级
        """
        return RiskLevel.from_operation(operation, self.sensitive_operations)
    
    def is_sensitive_operation(self, operation: str) -> bool:
        """判断操作是否为敏感操作
        
        Args:
            operation: 操作名称
            
        Returns:
            True 如果是敏感操作
        """
        operation_lower = operation.lower()
        return any(sop in operation_lower for sop in self.sensitive_operations)


# ============================================================================
# 审批对话框工厂函数
# ============================================================================

def create_approval_dialog(
    operation: str,
    preview: str = "",
    risk_level: RiskLevel = RiskLevel.MEDIUM,
) -> ApprovalDialog:
    """创建审批对话框
    
    Args:
        operation: 操作名称
        preview: 操作预览
        risk_level: 风险等级
        
    Returns:
        ApprovalDialog 实例
    """
    return ApprovalDialog(
        operation=operation,
        preview=preview,
        risk_level=risk_level,
    )


# ============================================================================
# 模块导出
# ============================================================================

__all__ = [
    # 审批模式
    "ApprovalMode",
    # 风险等级
    "RiskLevel",
    # 敏感操作列表
    "SENSITIVE_OPERATIONS",
    # 审批对话框
    "ApprovalDialog",
    "ApprovalRequested",
    "ApprovalConfirmed",
    "ApprovalRejected",
    # 审批管理器
    "ApprovalManager",
    # 工厂函数
    "create_approval_dialog",
]
