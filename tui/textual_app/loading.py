#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LoadingMixin — 加载动画与状态图标

🚪 Access - 💬 TUI - Textual App - Loading

v8.x 从 ``tui/textual_app/app.py`` L1091–1175 抽出：
- ``_start_loading_animation`` / ``_stop_loading_animation``
- ``_update_busy_animation``
- ``_update_status_icon`` / ``set_agent_status``
- ``_STATUS_ICONS`` 类级常量

依赖：
- ``LoadingIndicator``（来自 ``tui.textual_app.imports``）
- 主类的 ``query_one`` / ``set_timer`` / ``notify`` / ``self._widget_cache``
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .imports import LoadingIndicator

if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)


# ============================================================================
# LoadingMixin
# ============================================================================


class LoadingMixin:
    """加载动画与状态图标 Mixin。"""

    # 状态图标映射（与 tui.theming.icons 保持兼容）
    _STATUS_ICONS: dict[str, object] = {
        "online": "🟢",
        "busy": ["⏳", "⌛", "🔄", "✨"],
        "away": "🌙",
        "offline": "⚫",
        "error": "🔴",
        "thinking": "💭",
    }

    # 依赖主类初始化时填充
    _is_loading: bool = False
    _current_status: str = "online"
    _busy_frame_index: int = 0
    _use_native_loading: bool = False
    _loading_indicator: object = None
    _widget_cache: dict = {}
    _breathing_timer: object = None
    _breathing_bright: bool = True
    _busy_animation_timer: object = None

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def set_agent_status(self, status: str) -> None:
        """设置 Agent 状态（自动刷新图标显示）."""
        if status in self._STATUS_ICONS:
            self._current_status = status
        logger.debug(f"Agent status changed to: {status}")
        # 状态变更时同步刷新图标显示（如果已挂载且非加载中）
        try:
            if not getattr(self, "_is_loading", False):
                self._update_status_icon()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 加载动画生命周期
    # ------------------------------------------------------------------

    def _start_loading_animation(self) -> None:
        # 启动前先清理旧状态（防止重复启动残留）
        self._stop_loading_animation_silent_cleanup()

        self._is_loading = True

        # 更新状态为忙碌
        self._current_status = "busy"
        self._busy_frame_index = 0

        # 开启呼吸效果 - 先重置亮度状态，确保从亮开始
        self._breathing_bright = True
        try:
            status_bar = self.query_one("#status-bar")
            status_bar.styles.opacity = 1.0
        except Exception:
            pass
        self._breathing_timer = self.set_timer(0.75, self._breathing_pulse)

        if self._use_native_loading and LoadingIndicator is not None:
            # 使用 Textual 原生 LoadingIndicator
            try:
                if self._loading_indicator is None:
                    self._loading_indicator = LoadingIndicator()
                    self.query_one("#status-bar").mount(self._loading_indicator)
            except Exception:
                pass
        else:
            # 使用状态图标动画
            self._update_status_icon()
            self._update_busy_animation()

    def _stop_loading_animation_silent_cleanup(self) -> None:
        """静默清理所有动画 timer 和状态（不更新图标显示，供 start 前调用）.

        用于 _start_loading_animation 启动前的兜底清理，避免前一次未
        正常停止导致的残留 timer 并行运行。
        """
        self._is_loading = False

        # 清理呼吸 timer
        if self._breathing_timer is not None:
            try:
                self._breathing_timer.stop()
            except Exception:
                pass
            self._breathing_timer = None

        # 清理 busy 动画 timer
        if self._busy_animation_timer is not None:
            try:
                self._busy_animation_timer.stop()
            except Exception:
                pass
            self._busy_animation_timer = None

        # 重置呼吸亮度状态
        self._breathing_bright = True

        # 重置动画帧索引
        self._busy_frame_index = 0

        # 恢复 status-bar opacity 到 1.0（防止停在 0.5 的半透明状态）
        try:
            status_bar = self.query_one("#status-bar")
            status_bar.styles.opacity = 1.0
        except Exception:
            pass

    def _stop_loading_animation(self) -> None:
        # 先执行完整的 timer 清理和状态重置（含 opacity 恢复）
        self._stop_loading_animation_silent_cleanup()

        # 显式确保 _is_loading = False（虽然 silent_cleanup 已经设置）
        self._is_loading = False

        # 注意：不在这里强制设置 _current_status = "online"
        # 也不在这里调 _update_status_icon
        # 因为调用方接下来会调用 set_agent_status(status)，而 set_agent_status
        # 已经会在非加载状态下自动刷新图标到正确状态（避免中间状态闪烁）

        if self._use_native_loading and self._loading_indicator is not None:
            # 移除 Textual 原生 LoadingIndicator
            try:
                self._loading_indicator.remove()
                self._loading_indicator = None
            except Exception:
                pass

    def _breathing_pulse(self) -> None:
        """呼吸效果：切换状态栏亮度."""
        # 早期安全检查：如果已经停止，不再调度下一次，恢复 opacity 后退出
        if not self._is_loading:
            try:
                status_bar = self.query_one("#status-bar")
                status_bar.styles.opacity = 1.0
            except Exception:
                pass
            self._breathing_timer = None
            return

        self._breathing_bright = not self._breathing_bright
        try:
            status_bar = self.query_one("#status-bar")
            status_bar.styles.opacity = 1.0 if self._breathing_bright else 0.5
        except Exception:
            pass

        # 先清除旧引用（已完成回调的 timer），再设置新的
        self._breathing_timer = None
        # 再次检查：如果在上面操作期间状态被置为停止，不再调度下一次
        if not self._is_loading:
            try:
                status_bar = self.query_one("#status-bar")
                status_bar.styles.opacity = 1.0
            except Exception:
                pass
            return
        self._breathing_timer = self.set_timer(0.75, self._breathing_pulse)

    def _update_busy_animation(self) -> None:
        """更新 busy 状态的动画图标."""
        # 早期安全检查：停止状态下不继续调度，并清除 timer 引用
        if not self._is_loading or self._current_status != "busy":
            self._busy_animation_timer = None
            return

        self._busy_frame_index = (self._busy_frame_index + 1) % 4
        self._update_status_icon()

        # 先清除旧引用，再设置新的
        self._busy_animation_timer = None
        # 再次检查：操作期间可能已被停止
        if not self._is_loading or self._current_status != "busy":
            return
        self._busy_animation_timer = self.set_timer(0.5, self._update_busy_animation)

    def _update_status_icon(self) -> None:
        """更新状态图标."""
        icon_widget = self._widget_cache.get("status_icon")
        if icon_widget:
            status_icon = self._STATUS_ICONS.get(self._current_status, "😐")
            # busy 状态使用动画帧
            if self._current_status == "busy" and isinstance(status_icon, list):
                icon = status_icon[self._busy_frame_index % len(status_icon)]
            else:
                icon = status_icon
            icon_widget.update(icon)


__all__ = ["LoadingMixin"]