#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""StatusBarMixin — 底部状态栏更新

🚪 Access - 💬 TUI - Textual App - Status Bar

v8.x 从 ``tui/textual_app/app.py`` L664–781 抽出：
- ``_update_status_bar``         主状态栏刷新
- ``_update_used_tools``         工具使用统计
- ``_update_queue_display``      队列状态显示
- ``_toggle_budget_mode``        Goal/迭代模式切换
- ``_on_status_mode_toggle_clicked`` 切换按钮点击（主类 @on 调用）
- ``_update_mode_toggle_label``  模式按钮初始化显示
- ``_update_mode_toggle_tooltip`` 模式按钮 tooltip

依赖主类的 ``self._widget_cache`` / ``self._used_tools`` /
``self._pending_queue`` / ``self._agent`` / ``self._current_token_count`` /
``self._current_status`` / ``self._STATUS_ICONS``。
"""

from __future__ import annotations

import logging

from tui.core.formatters import format_token_count

from .imports import t  # type: ignore[attr-defined]

logger = logging.getLogger(__name__)


class StatusBarMixin:
    """状态栏更新 Mixin."""

    _logger = logging.getLogger(__name__)
    _widget_cache: dict = {}
    _used_tools: set = set()
    _pending_queue: list = []
    _current_token_count: int = 0
    _current_status: str = "online"
    _STATUS_ICONS: dict = {"online": "🟢", "busy": ["⏳"], "offline": "⚫"}
    context_length: int = 0

    # ------------------------------------------------------------------
    # 主状态栏
    # ------------------------------------------------------------------

    def _update_status_bar(self) -> None:
        try:
            # 使用缓存的 widgets（避免频繁 query_one）
            icon_widget = self._widget_cache.get("status_icon")
            if icon_widget:
                icon_widget.update(self._STATUS_ICONS.get(self._current_status, "😐"))

            tokens_widget = self._widget_cache.get("status_tokens")
            if tokens_widget:
                if self.context_length:
                    tokens_widget.update(
                        f"│ {format_token_count(self._current_token_count)}"
                        f"/{format_token_count(self.context_length)} "
                    )
                else:
                    tokens_widget.update("│ n/a ")

            time_widget = self._widget_cache.get("status_time")
            if time_widget:
                time_widget.update("│ 0m 0s ")

            tools_widget = self._widget_cache.get("status_tools")
            if tools_widget:
                tools_widget.update("🔧")
        except Exception as e:
            self._logger.debug(f"Failed to update status bar: {e}")

    def _update_used_tools(self) -> None:
        """更新已使用工具的显示."""
        try:
            tools_widget = self._widget_cache.get("status_tools")
            if tools_widget:
                count = len(self._used_tools)
                if count > 0:
                    # 显示工具名称（限制总长度）
                    tools_str = ",".join(sorted(self._used_tools))
                    if len(tools_str) > 15:
                        # 如果太长，缩写
                        sorted_tools = sorted(self._used_tools)
                        tools_str = ",".join(sorted_tools[:3])
                        if count > 3:
                            tools_str += f",+{count-3}"
                    tools_widget.update(f"🔧{tools_str}")
                else:
                    tools_widget.update("🔧")
        except Exception as e:
            self._logger.debug(f"Failed to update tools display: {e}")

    def _update_queue_display(self, queue_len_override=None) -> None:
        """更新队列状态显示（状态栏 + 输入框内容）.

        Args:
            queue_len_override: 可选，强制使用指定队列长度（用于 pop 后准确反映剩余数量）
        """
        queue_len = (
            queue_len_override
            if queue_len_override is not None
            else len(self._pending_queue)
        )
        try:
            queue_widget = self._widget_cache.get("status_queue")
            text_area = self._widget_cache.get("user_input")
            if queue_len > 0:
                # 状态栏显示排队数量
                if queue_widget:
                    queue_widget.update(f"⏳ {queue_len}")
                    queue_widget.set_class(True, "has-queue")
                # 输入框直接显示队首排队消息，禁用编辑
                if text_area:
                    text_area.text = self._pending_queue[0]
                    text_area.disabled = True
            else:
                # 队列空：恢复空闲状态
                if queue_widget:
                    queue_widget.update("")
                    queue_widget.set_class(False, "has-queue")
                if text_area:
                    text_area.text = ""
                    text_area.disabled = False
                    text_area.placeholder = t(
                        "tui.input.placeholder", "输入消息...Enter 发送"
                    )
        except Exception as e:
            self._logger.debug(f"Failed to update queue display: {e}")

    # ------------------------------------------------------------------
    # 模式切换
    # ------------------------------------------------------------------

    def _toggle_budget_mode(self) -> None:
        """切换 Goal 模式和迭代模式."""
        try:
            if (
                hasattr(self, "_agent")
                and self._agent
                and hasattr(self._agent, "state")
            ):
                state = self._agent.state
                from agent.state import BudgetMode

                if state.budget_mode == BudgetMode.TURN:
                    state._enable_iteration_mode()
                    mode_icon = t("tui.status_bar.mode_iter", "⚡ 单步")
                    mode_text = "单步"
                else:
                    state._enable_goal_mode()
                    mode_icon = t("tui.status_bar.mode_goal", "🎯 目标")
                    mode_text = "目标"

                # 更新按钮显示
                toggle_widget = self._widget_cache.get("status_mode_toggle")
                if toggle_widget:
                    toggle_widget.update(mode_icon)

                # 同步更新 tooltip
                self._update_mode_toggle_tooltip()

                self._logger.info(f"Budget mode switched to: {mode_text}")
        except Exception as e:
            self._logger.debug(f"Failed to toggle budget mode: {e}")

    def _on_status_mode_toggle_clicked(self, event=None) -> None:
        """处理模式切换按钮点击事件（显式方法供主类调用）."""
        self._logger.info("Mode toggle clicked (explicit handler)!")
        self._toggle_budget_mode()

    def _update_mode_toggle_label(self) -> None:
        """初始化/更新模式切换按钮显示（根据当前 agent state）."""
        try:
            toggle_widget = self._widget_cache.get("status_mode_toggle")
            if toggle_widget is None:
                try:
                    from .imports import Static
                    toggle_widget = self.query_one("#status-mode-toggle", Static)
                    self._widget_cache["status_mode_toggle"] = toggle_widget
                except Exception:
                    return
            # 尝试从 agent state 读取当前模式
            if (
                hasattr(self, "_agent")
                and self._agent
                and hasattr(self._agent, "state")
            ):
                from agent.state import BudgetMode
                state = self._agent.state
                if state.budget_mode == BudgetMode.TURN:
                    toggle_widget.update(t("tui.status_bar.mode_goal", "🎯 目标"))
                else:
                    toggle_widget.update(t("tui.status_bar.mode_iter", "⚡ 单步"))
            else:
                # 默认显示单步
                toggle_widget.update(t("tui.status_bar.mode_iter", "⚡ 单步"))
        except Exception as e:
            self._logger.debug(f"Failed to update mode toggle label: {e}")

    def _update_mode_toggle_tooltip(self) -> None:
        """更新模式切换按钮的 tooltip."""
        try:
            toggle_widget = self._widget_cache.get("status_mode_toggle")
            if toggle_widget is None:
                try:
                    from .imports import Static
                    toggle_widget = self.query_one("#status-mode-toggle", Static)
                    self._widget_cache["status_mode_toggle"] = toggle_widget
                except Exception:
                    return
            toggle_widget.tooltip = t(
                "tui.command.toggle_budget_mode",
                "切换单步/目标模式 (当前: {mode})",
                mode=self._get_current_budget_mode_label(),
            )
        except Exception as e:
            self._logger.debug(f"Failed to update mode toggle tooltip: {e}")

    def _get_current_budget_mode_label(self) -> str:
        """获取当前预算模式的中文标签."""
        try:
            if (
                hasattr(self, "_agent")
                and self._agent
                and hasattr(self._agent, "state")
            ):
                from agent.state import BudgetMode
                if self._agent.state.budget_mode == BudgetMode.TURN:
                    return t("tui.status_bar.mode_goal", "🎯 目标")
            return t("tui.status_bar.mode_iter", "⚡ 单步")
        except Exception:
            return t("tui.status_bar.mode_iter", "⚡ 单步")


__all__ = ["StatusBarMixin"]