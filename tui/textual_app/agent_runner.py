#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AgentRunnerMixin — Agent 执行 / 流式输出 / 思考回调 / 输入历史

🚪 Access - 💬 TUI - Textual App - Agent Runner

v8.x 从 ``tui/textual_app/app.py`` L2108–2439 抽出：
- ``_on_send_button_pressed`` / ``_on_text_area_submitted``
- ``_render_markdown_content``  Markdown 渲染
- ``_append_message``           追加消息（含工具名提取）
- ``_navigate_input_history``   上下方向键导航
- ``_history_prev`` / ``_history_next`` / ``_submit_from_history``
- ``_submit_user_input``
- ``_call_agent_async``         异步调用 agent
- ``_agent_result_callback``    future 完成回调
- ``_get_agent``                懒加载 agent
- ``_on_agent_stream_delta``    流式 delta
- ``_on_agent_thinking``        思考 delta
- ``_complete_agent_stream``    完成流式
- ``_show_typewriter_message``  助手消息回显

依赖主类的 ``self._agent`` / ``self._agent_executor`` / ``self._agent_busy` /
``self._widget_cache`` / ``self._pending_queue`` / ``self._input_history`` 等。
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque

from .imports import ChatContainer, Markdown, TextArea

logger = logging.getLogger(__name__)


class AgentRunnerMixin:
    """Agent 执行与流式回调 Mixin."""

    _logger = logging.getLogger(__name__)
    _widget_cache: dict = {}
    _agent = None
    _agent_executor = None
    _agent_future = None
    _agent_start_time: float = 0.0
    _agent_busy: bool = False
    _input_history: list = []
    _history_index: int = -1
    _current_input: str = ""
    _current_streaming_id = None
    _current_thinking: str = ""
    _used_tools: set = set()
    _current_token_count: int = 0

    # ------------------------------------------------------------------
    # 输入提交
    # ------------------------------------------------------------------

    def _on_send_button_pressed(self) -> None:
        self._submit_user_input()

    def _on_text_area_submitted(self) -> None:
        self._submit_user_input()

    def _submit_user_input(self) -> None:
        text_area = self.query_one("#user-input", TextArea)
        user_input = text_area.text.strip()

        if not user_input:
            return

        if user_input not in self._input_history:
            self._input_history.insert(0, user_input)
            if len(self._input_history) > 100:
                self._input_history = self._input_history[:100]

        self._history_index = -1
        self._current_input = ""
        text_area.text = ""
        self._append_message("user", user_input)
        self._logger.debug(f"User input: {user_input[:50]}...")
        self.app.call_later(lambda: self._call_agent_async(user_input))

    # ------------------------------------------------------------------
    # Markdown 渲染 & 消息追加
    # ------------------------------------------------------------------

    def _render_markdown_content(self, content: str) -> str:
        """使用 Textual 原生 Markdown 组件渲染内容."""
        if not content:
            return content

        try:
            # 使用 Textual 原生 Markdown 组件渲染
            markdown_widget = Markdown(content)
            # 获取渲染结果（返回 Rich Text 对象）
            return markdown_widget._content
        except Exception:
            return content

    def _append_message(
        self, role: str, content: str, render_markdown: bool = True
    ) -> None:
        # 使用缓存的 widget（优化性能）
        chat_area = self._widget_cache.get("chat_area")
        if chat_area is None:
            chat_area = self.query_one("#chat-area", ChatContainer)

        # 提取 tool_name 并跟踪工具
        tool_name = None
        if role == "tool" and content:
            # 尝试从 content 中提取工具名
            # 常见格式: "ToolName: result" 或 "Using tool: ToolName"
            lines = content.split("\n")
            first_line = lines[0] if lines else ""
            if ": " in first_line:
                tool_name = first_line.split(":")[0].strip()
            elif "using tool" in first_line.lower():
                # 格式: "Using tool: ToolName"
                parts = first_line.lower().split("using tool")
                if len(parts) > 1:
                    tool_name = (
                        parts[1].strip().split()[0] if parts[1].strip() else None
                    )
            if tool_name:
                self._used_tools.add(tool_name)

        # ChatView 使用 append_message 正确传递 role
        if hasattr(chat_area, "append_message"):
            chat_area.append_message(role, content, tool_name=tool_name)
        elif hasattr(chat_area, "write"):
            chat_area.write(f"{content}\n")

        # 同时保存到 session_store（用于 token 计数）
        self.save_message(role, content)

        # 更新工具显示
        self._update_used_tools()

    # ------------------------------------------------------------------
    # 输入历史导航
    # ------------------------------------------------------------------

    def _navigate_input_history(self, direction: int) -> None:
        """输入框上下键触发的历史导航回调.

        Args:
            direction: -1 表示向上（更早的历史），
                1 表示向下（更新的历史或还原当前输入）
        """
        if direction < 0:
            self._history_prev()
        else:
            self._history_next()

    def _history_prev(self) -> None:
        text_area = self.query_one("#user-input", TextArea)

        if not self._input_history:
            return

        if self._history_index == -1:
            self._current_input = text_area.text

        if self._history_index < len(self._input_history) - 1:
            self._history_index += 1
            text_area.text = self._input_history[self._history_index]

    def _history_next(self) -> None:
        text_area = self.query_one("#user-input", TextArea)

        if self._history_index == -1:
            return

        if self._history_index > 0:
            self._history_index -= 1
            text_area.text = self._input_history[self._history_index]
        else:
            self._history_index = -1
            text_area.text = self._current_input

    def _submit_from_history(self) -> None:
        text_area = self.query_one("#user-input", TextArea)
        user_input = text_area.text.strip()

        if not user_input:
            return

        if user_input not in self._input_history:
            self._input_history.insert(0, user_input)
            if len(self._input_history) > 100:
                self._input_history = self._input_history[:100]

        self._history_index = -1
        self._current_input = ""
        text_area.text = ""
        self._append_message("user", user_input)
        self._logger.debug(f"User input: {user_input[:50]}...")
        self.app.call_later(lambda: self._call_agent_async(user_input))

    # ------------------------------------------------------------------
    # Agent 异步执行
    # ------------------------------------------------------------------

    def _call_agent_async(self, user_input: str) -> None:
        """使用持久事件循环在子线程中运行异步 agent."""
        self.set_agent_status("busy")
        self._start_loading_animation()

        def on_stream_delta(text: str):
            self.app.call_later(self._on_agent_stream_delta, text)

        def on_thinking(text: str):
            self.app.call_later(self._on_agent_thinking, text)

        def run_agent():
            """在子线程中运行异步 agent."""
            try:
                agent = self._get_agent()
                if agent:
                    agent.set_stream_callback(on_stream_delta)
                    agent.set_thinking_callback(on_thinking)

                    # 获取或创建线程局部的事件循环
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_closed():
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                    try:
                        response = agent.chat(user_input, enable_stream=True)
                        if asyncio.iscoroutine(response):
                            response = loop.run_until_complete(response)
                        return response
                    finally:
                        # 不关闭循环，让 thread-local 的 loop 在下次复用
                        pass
                else:
                    return "Agent 未初始化，请检查配置"
            except Exception as e:
                return f"错误: {str(e)}"

        future = self._agent_executor.submit(run_agent)

        self._agent_future = future
        self._agent_start_time = time.time()
        self._current_thinking = ""

        # ponytail: done_callback instead of fixed-interval polling — no CPU waste
        def _on_done(f):
            self.app.call_later(self._agent_result_callback)

        future.add_done_callback(_on_done)

    def _agent_result_callback(self) -> None:
        """Called on main thread when agent future completes."""
        future = getattr(self, "_agent_future", None)
        if future is None:
            return

        self._stop_loading_animation()
        self.set_agent_status("online")

        elapsed = time.time() - getattr(self, "_agent_start_time", time.time())
        elapsed_minutes = int(elapsed // 60)
        elapsed_seconds = int(elapsed % 60)

        try:
            response = future.result()
            if response:
                if hasattr(response, "content"):
                    content = str(response.content)
                else:
                    content = str(response)
            else:
                content = "（无回复）"

            # ⚠️ 必须在 _complete_agent_stream() **清空流式状态之前** 判断
            # 是否实际走了流式输出；否则 _complete_agent_stream 把
            # _current_streaming_id 置 None 后，再判断 not _current_streaming_id
            # 永远为 True，导致「流式第一条 + typewriter 第二条」双重追加。
            chat_area = self._widget_cache.get("chat_area")
            did_stream = bool(getattr(self, "_current_streaming_id", None)) or (
                chat_area is not None
                and hasattr(chat_area, "is_streaming")
                and chat_area.is_streaming()
            )

            self._complete_agent_stream()

            if not did_stream:
                self._show_typewriter_message(content)

            time_widget = self._widget_cache.get("status_time")
            if time_widget:
                if elapsed_minutes > 0:
                    time_widget.update(f"│ {elapsed_minutes}m {elapsed_seconds}s ")
                else:
                    time_widget.update(f"│ {elapsed_seconds}s ")

            if self._session_store:
                self._session_store.flush_pending_messages()
            self.call_later(self._update_token_count)
        except Exception as e:
            self._stop_loading_animation()
            self.set_agent_status("error")
            self._append_message("system", f"❌ 处理失败: {str(e)}")
            self._current_streaming_id = None

        self._agent_future = None
        self._agent_busy = False

        # 处理队列中的下一条消息
        if self._pending_queue:
            next_input = self._pending_queue.popleft()
            self._append_message("user", next_input)
            # 更新队列显示（pop 后传入新的队列长度以正确反映剩余排队消息）
            self._update_queue_display(queue_len_override=len(self._pending_queue))
            self._call_agent_async(next_input)
        else:
            # 队列已空，恢复输入框
            self._update_queue_display()

    # ------------------------------------------------------------------
    # Agent 懒加载
    # ------------------------------------------------------------------

    def _get_agent(self):
        if hasattr(self, "_agent") and self._agent:
            return self._agent
        if getattr(self, "_agent", None) is not None:
            return self._agent
        try:
            from agent.agent import create_agent_from_config

            self._agent = create_agent_from_config()
            if self._agent:
                self._logger.info("Agent lazily created from config")
        except Exception as e:
            self._logger.warning(f"Failed to lazy-create agent: {e}")
        return getattr(self, "_agent", None)

    # ------------------------------------------------------------------
    # 流式回调
    # ------------------------------------------------------------------

    def _on_agent_stream_delta(self, text: str) -> None:
        """处理 Agent 流式输出增量."""
        chat_area = self._widget_cache.get("chat_area")
        if chat_area is None:
            chat_area = self.query_one("#chat-area", ChatContainer)

        if chat_area and hasattr(chat_area, "start_streaming"):
            if (
                not hasattr(self, "_current_streaming_id")
                or not self._current_streaming_id
            ):
                self._current_streaming_id = chat_area.start_streaming("assistant")

            if hasattr(chat_area, "append_streaming_text"):
                chat_area.append_streaming_text(text)

    def _on_agent_thinking(self, text: str) -> None:
        """处理 Agent 思考内容."""
        self._current_thinking = getattr(self, "_current_thinking", "") + text

        chat_area = self._widget_cache.get("chat_area")
        if chat_area is None:
            chat_area = self.query_one("#chat-area", ChatContainer)

        if chat_area and hasattr(chat_area, "append_streaming_thinking"):
            chat_area.append_streaming_thinking(text)
            if hasattr(chat_area, "current_streaming_id"):
                streaming_id = chat_area.current_streaming_id
                if streaming_id and not getattr(self, "_current_streaming_id", None):
                    self._current_streaming_id = streaming_id

    def _complete_agent_stream(self) -> None:
        """完成 Agent 流式输出."""
        chat_area = self._widget_cache.get("chat_area")
        if chat_area is None:
            chat_area = self.query_one("#chat-area", ChatContainer)

        if chat_area and hasattr(chat_area, "complete_streaming"):
            if hasattr(chat_area, "is_streaming") and chat_area.is_streaming():
                chat_area.complete_streaming()
            elif getattr(self, "_current_streaming_id", None):
                chat_area.complete_streaming()

        self._current_streaming_id = None

    def _show_typewriter_message(self, content: str) -> None:
        """显示 Agent 回复消息."""
        chat_area = self._widget_cache.get("chat_area")
        if chat_area is None:
            chat_area = self.query_one("#chat-area", ChatContainer)

        if chat_area:
            if hasattr(chat_area, "add_assistant_message"):
                chat_area.add_assistant_message(content)
            elif hasattr(chat_area, "write"):
                chat_area.write(f"\nAgent: {content}\n")


__all__ = ["AgentRunnerMixin"]