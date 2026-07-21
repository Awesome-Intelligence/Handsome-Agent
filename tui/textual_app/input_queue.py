#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""InputQueueMixin — 输入队列悬浮面板逻辑 Mixin

🚪 Access - 💬 TUI - Textual App - 输入队列 Mixin

v8.x 独立模块：
封装 TUI 中输入队列悬浮面板（#input-queue-panel）的所有行为：
- 初始化：_init_input_queue_panel  （on_mount 时调用）
- 渲染刷新：_render_input_queue_panel  （call_next 包裹，防 height=0）
- 单项删除：_on_queue_item_delete(index)  （删除按钮点击）
- 全量清空：_on_queue_clear_all(event)  （🗑️ 清空按钮点击）
- 公开刷新入口：_refresh_input_queue  （外部/其他 Mixin 调用）
- 防递归：_queue_rendering 标志

数据依赖（由主类 AgentApp 通过多继承共享）：
  self._pending_queue   deque 实例
  self._widget_cache   Dict[str, Widget]
  self._agent_busy     bool 是否正在处理 agent 任务

样式依赖：
  tui/textual_app/css/input_queue.py 中 INPUT_QUEUE_CSS

事件绑定（需在主类 @on 中绑定或由外部调用方绑定：
  @on(Click, '#input-queue-clear-all') → _on_queue_clear_all
  @on(Click, '.queue-delete-btn') → _on_queue_delete_clicked
"""

from __future__ import annotations

import logging
from collections import deque

from .imports import Click, Static, Horizontal, Vertical, on, t  # noqa: F401

logger = logging.getLogger(__name__)


class InputQueueMixin:
    """输入队列悬浮面板逻辑 Mixin.

    不持有数据，只持有行为。所有真实数据放在 AgentApp 的 self._pending_queue。
    """

    _logger = logging.getLogger(__name__)
    _queue_rendering: bool = False
    _pending_queue: deque = None  # 仅作类型注解，真实初始化在 AgentApp.__init__

    # ------------------------------------------------------------------
    # 初始化钩子（on_mount 时调用）
    # ------------------------------------------------------------------

    def _init_input_queue_panel(self) -> None:
        """初始化队列悬浮面板状态（on_mount 阶段安全调用）.

        - 设置初始可见状态（若启动时已有队列则显示，否则隐藏）。
        """
        try:
            queue_len = len(getattr(self, "_pending_queue", None) or [])
            if hasattr(self, "_widget_cache"):
                panel = self._widget_cache.get("input_queue_panel")
                if panel is None:
                    try:
                        panel = self.query_one("#input-queue-panel")
                        self._widget_cache["input_queue_panel"] = panel
                    except Exception:
                        panel = None
                if panel is not None:
                    panel.set_class(queue_len > 0, "visible")
            # 首帧不立即重建 children（布局期 height=0）；交给 on_mount 后后续 _update_queue_display 触发
        except Exception as e:
            self._logger.debug(f"Failed to init input queue panel: {e}")

    # ------------------------------------------------------------------
    # 公开刷新入口（供其他 Mixin 调用）
    # ------------------------------------------------------------------

    def _refresh_input_queue(self) -> None:
        """调度面板刷新（延迟到下一帧，避免布局期挂载失败）."""
        if getattr(self, "_queue_rendering", False):
            return
        try:
            if hasattr(self, "call_next"):
                self.call_next(self._render_input_queue_panel)
            elif hasattr(self, "app") and self.app is not None and hasattr(self.app, "call_next"):
                self.app.call_next(self._render_input_queue_panel)
            else:
                self._render_input_queue_panel()
        except Exception as e:
            self._logger.debug(f"Failed to schedule queue refresh: {e}")

    # ------------------------------------------------------------------
    # 核心渲染（内部实现）
    # ------------------------------------------------------------------

    def _render_input_queue_panel(self) -> None:
        """按当前 _pending_queue 内容重建 #input-queue-list 子节点.

        必须在 call_next 中调用（C3-3：防止布局期 height=0）。
        """
        if getattr(self, "_queue_rendering", False):
            return
        try:
            self._queue_rendering = True
            pending = getattr(self, "_pending_queue", None)
            if pending is None:
                return
            queue_len = len(pending)
            cache = getattr(self, "_widget_cache", {}) or {}

            # ---- 取面板 widget（cache 优先）
            panel = cache.get("input_queue_panel")
            if panel is None:
                try:
                    panel = self.query_one("#input-queue-panel")
                    cache["input_queue_panel"] = panel
                except Exception:
                    panel = None
            if panel is None:
                return

            list_widget = cache.get("input_queue_list")
            if list_widget is None:
                try:
                    list_widget = self.query_one("#input-queue-list", Vertical)
                    cache["input_queue_list"] = list_widget
                except Exception:
                    list_widget = None
            if list_widget is None:
                return

            count_widget = cache.get("input_queue_count")
            if count_widget is None:
                try:
                    count_widget = self.query_one("#input-queue-count", Static)
                    cache["input_queue_count"] = count_widget
                except Exception:
                    count_widget = None

            # ---- 空队列 → 隐藏
            if queue_len == 0:
                panel.set_class(False, "visible")
                try:
                    list_widget.remove_children()
                except Exception:
                    pass
                if count_widget is not None:
                    try:
                        count_widget.update(t("tui.queue.count", "⏳ 0 条排队", n=0))
                    except Exception:
                        pass
                return

            # ---- 非空队列 → 显示 + 更新计数
            panel.set_class(True, "visible")
            if count_widget is not None:
                try:
                    count_widget.update(
                        t("tui.queue.count", "⏳ {n} 条排队", n=queue_len)
                    )
                except Exception:
                    pass

            # ---- 清空旧 children（C3-7：不使用 recompose，只用 DOM 子节点增删）
            try:
                list_widget.remove_children()
            except Exception:
                pass

            # ---- 重建新 children
            items = list(pending)
            new_widgets: list = []
            for idx, text in enumerate(items):
                row = self._build_single_queue_item(idx, text)
                if row is not None:
                    new_widgets.append(row)
            if new_widgets:
                try:
                    list_widget.mount(*new_widgets)
                except Exception as e:
                    self._logger.debug(f"Failed to mount queue list children: {e}")
        except Exception as e:
            self._logger.debug(f"Failed to render input queue panel: {e}")
        finally:
            self._queue_rendering = False

    def _build_single_queue_item(self, index: int, text: str):
        """构建单个队列项 Horizontal 容器（未挂载）.

        Args:
            index: 在队列中的 0-based 索引
            text: 用户输入字符串

        Returns:
            Horizontal widget（classes=.queue-item [+ .first for index==0）
        """
        try:
            is_first = index == 0
            n_display = index + 1

            # 序号（首项带 ▶）
            if is_first:
                index_text = f"▶ {n_display}"
            else:
                index_text = f"  {n_display} "

            # 内容截断（> 200 字 或 > 3 行时加 …）
            display_text = self._truncate_queue_content(text)

            # 删除按钮 tooltip（不显示在 widget 文本里，仅留作将来扩展）
            # _ = t("tui.queue.delete_item_tooltip", "删除此条")

            classes = "queue-item first" if is_first else "queue-item"

            row = Horizontal(
                Static(index_text, classes="queue-index"),
                Static(display_text, classes="queue-content"),
                Static(" ✕", classes=f"queue-delete-btn queue-delete-{index}"),
                classes=classes,
            )

            # 把 index 写到删除按钮的属性，事件处理器里读（spec Task4 推荐方式）
            try:
                delete_btn = row.query(".queue-delete-btn").first()
                delete_btn.data_queue_index = index
            except Exception:
                # 退而求其次：写在整个 row 的属性上
                row.data_queue_index = index

            return row
        except Exception as e:
            self._logger.debug(f"Failed to build queue item {index}: {e}")
            return None

    @staticmethod
    def _truncate_queue_content(text: str, max_chars: int = 200, max_lines: int = 3) -> str:
        """内容截断：超长加 … 标识（单条最多 3 行，每行最多 80 字量级）."""
        if not text:
            return ""
        # 先按行截断
        lines = text.split("\n")
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            truncated = "\n".join(lines)
            if not truncated.endswith("…") and not truncated.endswith("..."):
                truncated = truncated.rstrip() + "…"
            text = truncated
        # 再按字符数截断
        if len(text) > max_chars:
            text = text[:max_chars].rstrip()
            if not text.endswith("…") and not text.endswith("..."):
                text = text + "…"
        return text

    # ------------------------------------------------------------------
    # 单项删除（事件回调）
    # ------------------------------------------------------------------

    def _on_queue_item_delete(self, index: int) -> None:
        """从 _pending_queue 中删除指定索引的项（删除按钮逻辑，0-based）.

        - 校验索引合法性
        - 用 list 中转实现 deque 中间删除（deque 原生只支持 O(k) 的 rotate + popleft）
        - 刷新面板 + 同步状态栏
        - 删除后若队列空且输入框被禁用，恢复输入框
        """
        pending = getattr(self, "_pending_queue", None)
        if pending is None or not isinstance(pending, deque):
            return
        if index < 0 or index >= len(pending):
            return
        try:
            items = list(pending)
            removed = items.pop(index)
            pending.clear()
            pending.extend(items)
            # i18n 提示：已移除排队项
            if hasattr(self, "notify_animated"):
                try:
                    self.notify_animated(
                        t("tui.queue.item_removed", "已移除排队项"),
                    )
                except Exception:
                    pass
            # 刷新面板 + 状态栏
            self._refresh_input_queue()
            if hasattr(self, "_update_queue_display"):
                try:
                    self._update_queue_display(queue_len_override=len(pending))
                except Exception:
                    pass
            # 队列空时恢复输入框
            if len(pending) == 0 and not getattr(self, "_agent_busy", False):
                text_area = None
                if hasattr(self, "_widget_cache"):
                    text_area = self._widget_cache.get("user_input")
                if text_area is None:
                    try:
                        from .imports import TextArea
                        text_area = self.query_one("#user-input", TextArea)
                    except Exception:
                        text_area = None
                if text_area is not None:
                    try:
                        text_area.disabled = False
                        text_area.text = ""
                        if hasattr(text_area, "placeholder"):
                            text_area.placeholder = t(
                                "tui.input.placeholder", "输入消息...Enter 发送"
                            )
                    except Exception:
                        pass
        except Exception as e:
            self._logger.debug(f"Failed to delete queue item {index}: {e}")
            # 兜底：继续尝试刷新状态栏，至少计数同步
            if hasattr(self, "_update_queue_display"):
                try:
                    self._update_queue_display(queue_len_override=len(pending))
                except Exception:
                    pass

    def _on_queue_delete_clicked(self, event: Click) -> None:
        """Click 事件分发器（由主类 @on(Click, '.queue-delete-btn') 调用）.

        读取被点击 widget 的 data_queue_index 属性，调用 _on_queue_item_delete。
        """
        try:
            ctrl = getattr(event, "control", None)
            if ctrl is None:
                return
            index = getattr(ctrl, "data_queue_index", None)
            if index is None:
                # 尝试父级查找
                parent = getattr(ctrl, "parent", None)
                if parent is not None:
                    index = getattr(parent, "data_queue_index", None)
            if index is None:
                # 尝试从 id 解析（queue-delete-N 形式）
                import re

                cid = getattr(ctrl, "id", "") or ""
                m = re.match(r"^queue-delete-(\d+)$", cid)
                if m:
                    index = int(m.group(1))
            if isinstance(index, int):
                self._on_queue_item_delete(index)
        except Exception as e:
            self._logger.debug(f"Queue delete click handler failed: {e}")

    # ------------------------------------------------------------------
    # 全量清空（事件回调）
    # ------------------------------------------------------------------

    def _on_queue_clear_all(self, event=None) -> None:
        """清空全部队列项.

        由主类 @on(Click, '#input-queue-clear-all') 调用（事件可传 event（带 selector 防止全局 Click 捕获（C3-8）。
        """
        pending = getattr(self, "_pending_queue", None)
        if pending is None:
            return
        if len(pending) == 0:
            return
        try:
            pending.clear()
            # i18n 提示：队列已清空
            if hasattr(self, "notify_animated"):
                try:
                    self.notify_animated(
                        t("tui.queue.cleared", "队列已清空"),
                    )
                except Exception:
                    pass
            # 刷新面板 + 状态栏
            self._refresh_input_queue()
            if hasattr(self, "_update_queue_display"):
                try:
                    self._update_queue_display(queue_len_override=0)
                except Exception:
                    pass
            # 恢复输入框（非 busy 状态下）
            if not getattr(self, "_agent_busy", False):
                text_area = None
                if hasattr(self, "_widget_cache"):
                    text_area = self._widget_cache.get("user_input")
                if text_area is None:
                    try:
                        from .imports import TextArea
                        text_area = self.query_one("#user-input", TextArea)
                    except Exception:
                        text_area = None
                if text_area is not None:
                    try:
                        text_area.disabled = False
                        text_area.text = ""
                        if hasattr(text_area, "placeholder"):
                            text_area.placeholder = t(
                                "tui.input.placeholder", "输入消息...Enter 发送"
                            )
                    except Exception:
                        pass
        except Exception as e:
            self._logger.debug(f"Failed to clear queue: {e}")
