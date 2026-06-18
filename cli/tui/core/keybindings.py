#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Key Bindings Module - Textual TUI Keyboard Shortcuts

🚪 Access - 💬 CLI - TUI - Key Bindings

提供快捷键映射系统，支持：
- 全局快捷键定义
- 分类组织（navigation, tab, command, help, session）
- 可扩展的自定义快捷键
- i18n 翻译支持

快捷键分类：
- navigation: 导航快捷键（↑/↓/j/k）
- tab: 标签管理快捷键（Ctrl+T/W/Tab）
- command: 命令快捷键（Ctrl+K/L/C/V）
- help: 帮助快捷键（F1/Ctrl+/）
- session: 会话管理快捷键（Ctrl+R）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, TYPE_CHECKING

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
# 快捷键类别定义
# ============================================================================

class KeyBindingCategory:
    """快捷键类别枚举"""
    NAVIGATION = "navigation"    # 导航快捷键
    TAB = "tab"                  # 标签管理
    COMMAND = "command"          # 命令操作
    HELP = "help"                # 帮助
    SESSION = "session"         # 会话管理


# ============================================================================
# KeyBinding 数据类
# ============================================================================

@dataclass
class KeyBinding:
    """快捷键绑定定义
    
    Attributes:
        key: 快捷键字符串（如 "ctrl+t", "j", "up"）
        description: 快捷键功能描述
        action: 触发时执行的回调函数
        category: 快捷键类别
        hidden: 是否在帮助面板中隐藏
    """
    key: str
    description: str
    action: Callable
    category: str = KeyBindingCategory.COMMAND
    hidden: bool = False
    
    def __post_init__(self):
        """规范化快捷键字符串"""
        self.key = self.key.lower().strip()


@dataclass
class KeyBindingGroup:
    """快捷键分组
    
    Attributes:
        name: 分组名称
        bindings: 分组内的快捷键列表
    """
    name: str
    bindings: list[KeyBinding] = field(default_factory=list)
    
    def add_binding(self, binding: KeyBinding) -> None:
        """添加快捷键到分组"""
        self.bindings.append(binding)


# ============================================================================
# 默认快捷键定义
# ============================================================================

def create_default_keybindings(
    on_new_tab: Optional[Callable] = None,
    on_close_tab: Optional[Callable] = None,
    on_next_tab: Optional[Callable] = None,
    on_prev_tab: Optional[Callable] = None,
    on_open_command_palette: Optional[Callable] = None,
    on_scroll_up: Optional[Callable] = None,
    on_scroll_down: Optional[Callable] = None,
    on_open_help: Optional[Callable] = None,
    on_open_session_selector: Optional[Callable] = None,
    on_clear_screen: Optional[Callable] = None,
    on_copy: Optional[Callable] = None,
    on_paste: Optional[Callable] = None,
    on_escape: Optional[Callable] = None,
    on_quit: Optional[Callable] = None,
) -> list[KeyBinding]:
    """创建默认快捷键列表
    
    Args:
        on_new_tab: 新建标签回调
        on_close_tab: 关闭标签回调
        on_next_tab: 切换到下一个标签回调
        on_prev_tab: 切换到上一个标签回调
        on_open_command_palette: 打开命令面板回调
        on_scroll_up: 上移/滚动回调
        on_scroll_down: 下移/滚动回调
        on_open_help: 打开帮助回调
        on_open_session_selector: 打开会话选择器回调
        on_clear_screen: 清屏回调
        on_copy: 复制回调
        on_paste: 粘贴回调
        on_escape: 关闭模态/取消回调
        on_quit: 退出应用回调
    
    Returns:
        快捷键列表
    """
    bindings = []
    
    # 标签管理快捷键
    if on_new_tab:
        bindings.append(KeyBinding(
            key="ctrl+t",
            description="新建标签",
            action=on_new_tab,
            category=KeyBindingCategory.TAB,
        ))
    
    if on_close_tab:
        bindings.append(KeyBinding(
            key="ctrl+w",
            description="关闭标签",
            action=on_close_tab,
            category=KeyBindingCategory.TAB,
        ))
    
    if on_next_tab:
        bindings.append(KeyBinding(
            key="ctrl+tab",
            description="切换到下一个标签",
            action=on_next_tab,
            category=KeyBindingCategory.TAB,
        ))
    
    if on_prev_tab:
        bindings.append(KeyBinding(
            key="ctrl+shift+tab",
            description="切换到上一个标签",
            action=on_prev_tab,
            category=KeyBindingCategory.TAB,
        ))
    
    # 命令快捷键
    if on_open_command_palette:
        bindings.append(KeyBinding(
            key="ctrl+k",
            description="打开命令面板",
            action=on_open_command_palette,
            category=KeyBindingCategory.COMMAND,
        ))
    
    if on_clear_screen:
        bindings.append(KeyBinding(
            key="ctrl+l",
            description="清屏",
            action=on_clear_screen,
            category=KeyBindingCategory.COMMAND,
        ))
    
    if on_copy:
        bindings.append(KeyBinding(
            key="ctrl+c",
            description="复制选中内容",
            action=on_copy,
            category=KeyBindingCategory.COMMAND,
        ))
    
    if on_paste:
        bindings.append(KeyBinding(
            key="ctrl+v",
            description="粘贴",
            action=on_paste,
            category=KeyBindingCategory.COMMAND,
        ))
    
    # 导航快捷键
    if on_scroll_up:
        bindings.append(KeyBinding(
            key="up",
            description="上移/滚动",
            action=on_scroll_up,
            category=KeyBindingCategory.NAVIGATION,
        ))
        bindings.append(KeyBinding(
            key="k",
            description="上移/滚动 (vim)",
            action=on_scroll_up,
            category=KeyBindingCategory.NAVIGATION,
        ))
    
    if on_scroll_down:
        bindings.append(KeyBinding(
            key="down",
            description="下移/滚动",
            action=on_scroll_down,
            category=KeyBindingCategory.NAVIGATION,
        ))
        bindings.append(KeyBinding(
            key="j",
            description="下移/滚动 (vim)",
            action=on_scroll_down,
            category=KeyBindingCategory.NAVIGATION,
        ))
    
    # 帮助快捷键
    if on_open_help:
        bindings.append(KeyBinding(
            key="f1",
            description="打开帮助",
            action=on_open_help,
            category=KeyBindingCategory.HELP,
        ))
        bindings.append(KeyBinding(
            key="ctrl+/",
            description="打开帮助",
            action=on_open_help,
            category=KeyBindingCategory.HELP,
        ))
    
    # 会话管理快捷键
    if on_open_session_selector:
        bindings.append(KeyBinding(
            key="ctrl+r",
            description="打开会话选择器",
            action=on_open_session_selector,
            category=KeyBindingCategory.SESSION,
        ))
    
    # 通用快捷键
    if on_escape:
        bindings.append(KeyBinding(
            key="escape",
            description="关闭模态/取消",
            action=on_escape,
            category=KeyBindingCategory.COMMAND,
        ))
    
    if on_quit:
        bindings.append(KeyBinding(
            key="ctrl+q",
            description="退出应用",
            action=on_quit,
            category=KeyBindingCategory.COMMAND,
        ))
        bindings.append(KeyBinding(
            key="q",
            description="退出应用",
            action=on_quit,
            category=KeyBindingCategory.COMMAND,
        ))
    
    return bindings


# ============================================================================
# KeyBindingManager - 快捷键管理器
# ============================================================================

class KeyBindingManager:
    """快捷键管理器
    
    管理应用的所有快捷键绑定，支持：
    - 添加/移除快捷键
    - 按类别查询快捷键
    - 模糊搜索
    - 自定义快捷键覆盖
    
    Attributes:
        bindings: 快捷键列表
        custom_overrides: 自定义快捷键覆盖
        _logger: 日志记录器
    """
    
    def __init__(self):
        """初始化快捷键管理器"""
        self.bindings: list[KeyBinding] = []
        self.custom_overrides: dict[str, KeyBinding] = {}
        self._logger = get_access_logger("KeyBindingManager", sublayer="cli")
    
    def register(self, binding: KeyBinding) -> None:
        """注册快捷键
        
        Args:
            binding: 快捷键绑定
        """
        # 检查是否已存在相同键的快捷键
        for i, existing in enumerate(self.bindings):
            if existing.key == binding.key:
                self._logger.debug(f"Replacing existing binding for key: {binding.key}")
                self.bindings[i] = binding
                return
        
        self.bindings.append(binding)
        self._logger.debug(f"Registered binding: {binding.key} -> {binding.description}")
    
    def register_batch(self, bindings: list[KeyBinding]) -> None:
        """批量注册快捷键
        
        Args:
            bindings: 快捷键列表
        """
        for binding in bindings:
            self.register(binding)
    
    def unregister(self, key: str) -> bool:
        """取消注册快捷键
        
        Args:
            key: 快捷键字符串
            
        Returns:
            True 如果成功移除，否则 False
        """
        key = key.lower().strip()
        for i, binding in enumerate(self.bindings):
            if binding.key == key:
                self.bindings.pop(i)
                self._logger.debug(f"Unregistered binding: {key}")
                return True
        return False
    
    def get_by_key(self, key: str) -> Optional[KeyBinding]:
        """根据键获取快捷键
        
        Args:
            key: 快捷键字符串
            
        Returns:
            快捷键绑定，如果不存在则返回 None
        """
        key = key.lower().strip()
        
        # 首先检查自定义覆盖
        if key in self.custom_overrides:
            return self.custom_overrides[key]
        
        # 然后检查默认绑定
        for binding in self.bindings:
            if binding.key == key:
                return binding
        
        return None
    
    def get_by_category(self, category: str) -> list[KeyBinding]:
        """根据类别获取快捷键
        
        Args:
            category: 类别名称
            
        Returns:
            该类别下的所有快捷键
        """
        return [
            binding for binding in self.bindings
            if binding.category == category
        ]
    
    def search(self, query: str, include_hidden: bool = False) -> list[KeyBinding]:
        """模糊搜索快捷键
        
        Args:
            query: 搜索关键词
            include_hidden: 是否包含隐藏的快捷键
            
        Returns:
            匹配的快捷键列表
        """
        query = query.lower().strip()
        results = []
        
        for binding in self.bindings:
            # 跳过隐藏的快捷键（除非明确要求）
            if binding.hidden and not include_hidden:
                continue
            
            # 匹配键或描述
            if query in binding.key.lower() or query in binding.description.lower():
                results.append(binding)
        
        return results
    
    def get_all_categories(self) -> list[str]:
        """获取所有已使用的类别
        
        Returns:
            类别列表
        """
        categories = set()
        for binding in self.bindings:
            categories.add(binding.category)
        return sorted(categories)
    
    def get_grouped_bindings(self, include_hidden: bool = False) -> dict[str, list[KeyBinding]]:
        """获取按类别分组的快捷键
        
        Args:
            include_hidden: 是否包含隐藏的快捷键
            
        Returns:
            {类别: [快捷键列表]} 的字典
        """
        grouped: dict[str, list[KeyBinding]] = {}
        
        for binding in self.bindings:
            if binding.hidden and not include_hidden:
                continue
            
            if binding.category not in grouped:
                grouped[binding.category] = []
            grouped[binding.category].append(binding)
        
        return grouped
    
    def override(self, key: str, binding: KeyBinding) -> None:
        """覆盖快捷键
        
        Args:
            key: 要覆盖的快捷键
            binding: 新的快捷键绑定
        """
        key = key.lower().strip()
        self.custom_overrides[key] = binding
        self._logger.info(f"Override binding: {key} -> {binding.description}")
    
    def clear_overrides(self) -> None:
        """清除所有自定义覆盖"""
        self.custom_overrides.clear()
        self._logger.debug("Cleared all custom overrides")
    
    def format_for_display(self, binding: KeyBinding, i18n_enabled: bool = True) -> str:
        """格式化快捷键用于显示
        
        Args:
            binding: 快捷键绑定
            i18n_enabled: 是否启用 i18n
            
        Returns:
            格式化的字符串
        """
        key_display = self._format_key(binding.key)
        desc = binding.description
        
        if i18n_enabled:
            i18n = get_i18n()
            desc = i18n.t(f"tui.keybinding.{binding.key}", default=desc)
        
        return f"[bold]{key_display}[/bold]  {desc}"
    
    def _format_key(self, key: str) -> str:
        """格式化键名用于显示
        
        Args:
            key: 原始键名
            
        Returns:
            格式化后的键名
        """
        # 转换 ctrl -> Ctrl+, shift -> Shift+, alt -> Alt+
        parts = key.split("+")
        formatted = []
        
        for part in parts:
            part = part.lower().strip()
            if part == "ctrl":
                formatted.append("Ctrl+")
            elif part == "shift":
                formatted.append("Shift+")
            elif part == "alt":
                formatted.append("Alt+")
            elif part == "escape":
                formatted.append("Esc")
            elif part == "tab":
                formatted.append("Tab")
            elif part == "up":
                formatted.append("↑")
            elif part == "down":
                formatted.append("↓")
            elif part == "left":
                formatted.append("←")
            elif part == "right":
                formatted.append("→")
            else:
                formatted.append(part.upper())
        
        return "".join(formatted)


# ============================================================================
# 模块导出
# ============================================================================

__all__ = [
    "KeyBinding",
    "KeyBindingGroup",
    "KeyBindingManager",
    "KeyBindingCategory",
    "create_default_keybindings",
]
