#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""设置界面控件组件

提供设置界面所需的自定义控件:
- Toggle: 开关控件
- Select: 选择下拉控件
- Slider: 滑块控件
- NumberInput: 数字输入控件
"""

from __future__ import annotations

from typing import Callable, Optional, Any, Union

# Textual 框架导入
TEXTUAL_AVAILABLE = True
try:
    from textual.app import ComposeResult
    from textual.widgets import Static, Button
    from textual.containers import Horizontal, Vertical
    from textual.message import Message
except ImportError:
    TEXTUAL_AVAILABLE = False
    Static = object
    Button = object
    Horizontal = object
    Vertical = object
    Message = object

# i18n 支持
try:
    from common.i18n import get_i18n
except ImportError:
    def get_i18n():
        class SimpleI18n:
            def t(self, key, default=None, **kwargs):
                return default or key
        return SimpleI18n()

# 主题颜色常量（高雅紫）
PURPLE_PRIMARY = "#B180D7"
PURPLE_BRIGHT = "#C9A0E0"
PURPLE_DIM = "#8B5CAC"
WHITE = "white"
GRAY_DIM = "#888888"
GRAY_LIGHT = "#AAAAAA"
SURFACE = "#2a2a2a"


# ============================================================================
# Toggle 开关控件
# ============================================================================

class ToggleValueChanged(Message):
    """开关值变更消息"""
    def __init__(self, sender, key: str, value: bool) -> None:
        self.key = key
        self.value = value
        super().__init__()


class SettingToggle(Static):
    """开关控件"""
    
    def __init__(
        self,
        key: str,
        label: str,
        value: bool = False,
        on_change: Callable[[str, bool], None] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self._key = key
        self._label = label
        self._value = value
        self._on_change = on_change
    
    def compose(self) -> ComposeResult:
        with Horizontal(classes="setting-toggle-container"):
            yield Static(
                self._label,
                classes="setting-toggle-label"
            )
            yield Static(
                "[×]" if self._value else "[ ]",
                classes="setting-toggle-value"
            )
    
    def toggle(self) -> None:
        """切换开关状态"""
        self._value = not self._value
        self.refresh()
        self.post_message(ToggleValueChanged(self, self._key, self._value))
        if self._on_change:
            self._on_change(self._key, self._value)
    
    def get_value(self) -> bool:
        """获取当前值"""
        return self._value
    
    def render(self) -> str:
        return f"{self._label}  {'[×]' if self._value else '[ ]'}"


# ============================================================================
# Select 选择控件
# ============================================================================

class SelectOption:
    """选择选项"""
    def __init__(self, value: str, label: str):
        self.value = value
        self.label = label

class SelectValueChanged(Message):
    """选择值变更消息"""
    def __init__(self, sender, key: str, value: str) -> None:
        self.key = key
        self.value = value
        super().__init__()


class SettingSelect(Static):
    """选择下拉控件"""
    
    CSS = """
    SettingSelect {
        height: auto;
    }
    
    SettingSelect .setting-select-label {
        width: 100%;
        height: auto;
        padding: 0 1;
    }
    
    SettingSelect .setting-select-current {
        width: 100%;
        height: auto;
        padding: 0 1;
        color: $accent;
    }
    
    SettingSelect .setting-select-options {
        width: 100%;
        height: auto;
        display: none;
        background: $surface;
        border: solid $border;
    }
    
    SettingSelect .setting-select-options.open {
        display: block;
    }
    
    SettingSelect .setting-select-option {
        width: 100%;
        height: auto;
        padding: 0 1;
    }
    
    SettingSelect .setting-select-option:hover,
    SettingSelect .setting-select-option.selected {
        background: $accent 15%;
    }
    """
    
    def __init__(
        self,
        key: str,
        label: str,
        options: list[tuple[str, str]],
        value: str = "",
        on_change: Callable[[str, str], None] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self._key = key
        self._label = label
        self._options = [SelectOption(v, l) for v, l in options]
        self._value = value or (options[0][0] if options else "")
        self._selected_index = self._get_index_by_value(self._value)
        self._on_change = on_change
        self._is_open = False
    
    def _get_index_by_value(self, value: str) -> int:
        for i, opt in enumerate(self._options):
            if opt.value == value:
                return i
        return 0
    
    def compose(self) -> ComposeResult:
        current_label = self._get_label_by_value(self._value)
        yield Static(self._label, classes="setting-select-label")
        yield Static(
            f"[▼] {current_label}",
            classes="setting-select-current"
        )
        
        # 生成选项列表
        options_container = Vertical(classes="setting-select-options")
        for i, opt in enumerate(self._options):
            is_selected = i == self._selected_index
            yield Static(
                f"  {opt.label}",
                classes=f"setting-select-option {'selected' if is_selected else ''}"
            )
    
    def _get_label_by_value(self, value: str) -> str:
        for opt in self._options:
            if opt.value == value:
                return opt.label
        return value
    
    def on_click(self) -> None:
        """点击切换展开/收起"""
        self._is_open = not self._is_open
        options = self.query(".setting-select-options")
        if options:
            for opt in options:
                if self._is_open:
                    opt.add_class("open")
                else:
                    opt.remove_class("open")
    
    def select_option(self, value: str) -> None:
        """选择选项"""
        old_value = self._value
        self._value = value
        self._selected_index = self._get_index_by_value(value)
        self._is_open = False
        self.refresh()
        
        if old_value != value:
            self.post_message(SelectValueChanged(self, self._key, value))
            if self._on_change:
                self._on_change(self._key, value)
    
    def get_value(self) -> str:
        """获取当前值"""
        return self._value


# ============================================================================
# Slider 滑块控件
# ============================================================================

class SliderValueChanged(Message):
    """滑块值变更消息"""
    def __init__(self, sender, key: str, value: float) -> None:
        self.key = key
        self.value = value
        super().__init__()


class SettingSlider(Static):
    """滑块控件"""
    
    def __init__(
        self,
        key: str,
        label: str,
        value: float = 0.5,
        min_value: float = 0.0,
        max_value: float = 1.0,
        step: float = 0.1,
        format_func: Callable[[float], str] = None,
        on_change: Callable[[str, float], None] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self._key = key
        self._label = label
        self._value = value
        self._min_value = min_value
        self._max_value = max_value
        self._step = step
        self._format_func = format_func or (lambda v: str(v))
        self._on_change = on_change
    
    def compose(self) -> ComposeResult:
        display_value = self._format_func(self._value)
        percentage = (self._value - self._min_value) / (self._max_value - self._min_value)
        bar_length = 20
        filled = int(bar_length * percentage)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        yield Static(self._label, classes="setting-slider-label")
        yield Static(
            f"[{bar}] {display_value}",
            classes="setting-slider-value"
        )
    
    def adjust(self, delta: float) -> None:
        """调整滑块值"""
        new_value = self._value + delta
        new_value = max(self._min_value, min(self._max_value, new_value))
        new_value = round(new_value / self._step) * self._step
        
        if new_value != self._value:
            self._value = new_value
            self.refresh()
            self.post_message(SliderValueChanged(self, self._key, self._value))
            if self._on_change:
                self._on_change(self._key, self._value)
    
    def get_value(self) -> float:
        """获取当前值"""
        return self._value
    
    def set_value(self, value: float) -> None:
        """设置值"""
        self._value = max(self._min_value, min(self._max_value, value))
        self.refresh()


# ============================================================================
# NumberInput 数字输入控件
# ============================================================================

class NumberValueChanged(Message):
    """数字值变更消息"""
    def __init__(self, sender, key: str, value: int) -> None:
        self.key = key
        self.value = value
        super().__init__()


class SettingNumberInput(Static):
    """数字输入控件"""
    
    def __init__(
        self,
        key: str,
        label: str,
        value: int = 0,
        min_value: int = 0,
        max_value: int = 100,
        step: int = 1,
        suffix: str = "",
        on_change: Callable[[str, int], None] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self._key = key
        self._label = label
        self._value = value
        self._min_value = min_value
        self._max_value = max_value
        self._step = step
        self._suffix = suffix
        self._on_change = on_change
    
    def compose(self) -> ComposeResult:
        yield Static(self._label, classes="setting-number-label")
        yield Static(
            f"[{self._value}{self._suffix}]  ▲▼",
            classes="setting-number-value"
        )
    
    def adjust(self, delta: int) -> None:
        """调整数值"""
        new_value = self._value + delta * self._step
        new_value = max(self._min_value, min(self._max_value, new_value))
        
        if new_value != self._value:
            self._value = new_value
            self.refresh()
            self.post_message(NumberValueChanged(self, self._key, self._value))
            if self._on_change:
                self._on_change(self._key, self._value)
    
    def increment(self) -> None:
        """增加"""
        self.adjust(1)
    
    def decrement(self) -> None:
        """减少"""
        self.adjust(-1)
    
    def get_value(self) -> int:
        """获取当前值"""
        return self._value
    
    def set_value(self, value: int) -> None:
        """设置值"""
        self._value = max(self._min_value, min(self._max_value, value))
        self.refresh()
