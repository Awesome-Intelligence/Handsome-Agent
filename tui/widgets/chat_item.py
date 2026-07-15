#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChatItem - 单条消息 widget（oterm 风格）

🚪 Access - 💬 TUI - Widgets - ChatItem

参考 E:\\oterm-study\\src\\oterm\\app\\widgets\\chat.py 的 ChatItem 实现：

- reactive 字段（text / thinking / thoughts_collapsed / author），
  状态变化走 Textual 的自动批处理与 watcher。
- append_text / append_thinking 用 ``Markdown.get_stream(...).write(delta)``
  增量写入 —— MarkdownStream 内部批处理，**不**每次 token 全文重新解析。
- ``self.set_reactive(...)`` 同步状态但**不**触发 watcher 的全文重渲染。
- compose() 一次性声明所有子 widget（思考标签 / 思考 body / 回复），
  避免"迟到思考"场景下拆 widget 重建 DOM。
- 用户文本 Static 显式 ``markup=False`` 跳过 Rich markup 解析。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Literal

from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Markdown, Static
from textual.widgets.markdown import MarkdownStream

# 仅 ChatItem 关心用户提示符字符；与 oterm 一致用 ❯。
_PROMPT_MARKER = "❯"

# 单条消息可挂的 tool_call 数量上限。
# 超过此数量后新增的 tool_call 不再渲染（不影响模型能力，仅 UI 折叠）。
_MAX_TOOL_CALLS_PER_ITEM = 8


Author = Literal["user", "assistant", "system", "tool", "error"]


class ChatItem(Widget):
    """聊天中的一条消息。

    文本与思考的流式输出均走 ``MarkdownStream.write``，避免每次 token
    都重新解析 Markdown。``text`` / ``thinking`` 字段是 reactive，
    通过 ``set_reactive`` 在流式过程中静默同步，watcher 只在真正需要
    chrome 刷新时触发。

    Attributes:
        text: 当前累积的文本内容。
        thinking: 当前累积的思考内容。
        thoughts_collapsed: 思考块是否折叠。
        author: 消息角色，取值见 ``Author`` 字面量。
    """

    text: reactive[str] = reactive("")
    thinking: reactive[str] = reactive("")
    thoughts_collapsed: reactive[bool] = reactive(True)
    author: reactive[str] = reactive("")
    tool_name: reactive[str] = reactive("")

    DEFAULT_CSS = """
    ChatItem {
        width: 100%;
        height: auto;
        margin: 0 0 1 0;
        layout: horizontal;
        content-align: left middle;
    }

    ChatItem.user {
        content-align: right middle;
    }

    ChatItem.user .text-wrapper {
        width: auto;
        max-width: 80%;
        background: #3a3a3a;
        padding: 0 1;
    }

    ChatItem .text-wrapper {
        width: 100%;
        height: auto;
    }

    ChatItem .text {
        width: 1fr;
        height: auto;
    }

    ChatItem .prompt-marker {
        width: auto;
        padding: 0 1 0 0;
        color: $accent;
    }

    ChatItem .response-column {
        width: 1fr;
        height: auto;
    }

    ChatItem .thinking-label {
        width: auto;
        height: auto;
        color: $secondary;
        text-style: italic;
    }

    ChatItem .thinking-body {
        width: 1fr;
        height: auto;
        margin: 0 0 1 0;
        color: $text-muted;
    }

    ChatItem .response {
        width: 1fr;
        height: auto;
    }

    ChatItem.tool .tool-name {
        color: $warning;
        text-style: bold;
    }

    ChatItem.error .prompt-marker {
        color: $error;
    }
    """

    @dataclass
    class ThinkingToggled(Message):
        """思考块展开/折叠时发送，供上层订阅。"""

        item: "ChatItem"
        collapsed: bool

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._response_stream: MarkdownStream | None = None
        self._thinking_stream: MarkdownStream | None = None
        self._tool_calls: dict[str, "ToolCallItem"] = {}
        self._frozen: bool = False
        self._user_toggled: bool = False

    def watch_author(self, author: str) -> None:
        """当 author 改变时，更新 ChatItem 上的 CSS 类。"""
        for role in ("user", "assistant", "system", "tool", "error"):
            self.remove_class(role)
        if author:
            self.add_class(author)

    def on_mount(self) -> None:
        """mount 后确保 author 类被正确添加。"""
        if self.author:
            self.add_class(self.author)

    # ------------------------------------------------------------------
    # 渲染结构
    # ------------------------------------------------------------------

    def compose(self):  # type: ignore[override]
        """声明式组合子 widget。

        user / system / tool / error 仅 Static 一条；
        assistant 一次声明 thinking-label / thinking-body / response 三个，
        避免迟到的思考流需要拆 widget 重建 DOM。
        """
        author = self.author
        if author == "user":
            with Horizontal(classes="text-wrapper"):
                yield Static(self.text, markup=False, classes="text")
        elif author == "tool":
            yield Static(_PROMPT_MARKER, classes="prompt-marker")
            with Vertical(classes="response-column"):
                yield Static(f"🔧 {self.tool_name or 'tool'}", classes="tool-name")
                yield Static(self.text, markup=False, classes="text")
        elif author == "error":
            yield Static(_PROMPT_MARKER, classes="prompt-marker")
            yield Static(self.text, markup=False, classes="text")
        elif author == "system":
            yield Static(_PROMPT_MARKER, classes="prompt-marker")
            yield Static(self.text, markup=False, classes="text")
        else:  # assistant
            yield Static(_PROMPT_MARKER, classes="prompt-marker")
            with Vertical(classes="response-column"):
                yield Static("", classes="thinking-label")
                yield Markdown(classes="thinking-body")
                yield Markdown(classes="response")

    # ------------------------------------------------------------------
    # 流式入口（agent 调用）
    # ------------------------------------------------------------------

    async def append_text(self, delta: str) -> None:
        """流式追加一段回复文本。

        Args:
            delta: 本次增量（可为空字符串）。
        """
        if self.author != "assistant" or not delta:
            return
        if self._response_stream is None:
            try:
                response = self.query_one(".response", Markdown)
            except NoMatches:
                return
            self._response_stream = Markdown.get_stream(response)
        self.set_reactive(ChatItem.text, self.text + delta)
        await self._response_stream.write(delta)

    async def append_thinking(self, delta: str) -> None:
        """流式追加一段思考内容。

        Args:
            delta: 本次增量（可为空字符串）。
        """
        if self.author != "assistant" or not delta:
            return
        first_chunk = self._thinking_stream is None
        if self._thinking_stream is None:
            try:
                body = self.query_one(".thinking-body", Markdown)
            except NoMatches:
                return
            self._thinking_stream = Markdown.get_stream(body)
        self.set_reactive(ChatItem.thinking, self.thinking + delta)
        if first_chunk:
            self._refresh_thinking_chrome()
            if self.thoughts_collapsed and not self._user_toggled:
                self.set_reactive(ChatItem.thoughts_collapsed, False)
        await self._thinking_stream.write(delta)

    async def finish_stream(self) -> None:
        """流结束时的清理与最终落盘。

        ``MarkdownStream.stop()`` 会 await 内部 task，task 外层 finally
        会把残余 ``_pending`` 全部 ``append`` 到 Markdown widget。因此
        stop 完成后整篇文本已经在 Markdown 里，不需要再 ``Markdown.update``
        触发一次完整 re-parse —— 紧接着 ``_freeze_markdown`` 会把整棵
        Markdown 子树换成单个 ``Static(RichMarkdown(...))``，中间任何
        update 都是浪费。
        """
        if not self._user_toggled and self.thinking:
            self.set_reactive(ChatItem.thoughts_collapsed, True)
        if self._response_stream is not None:
            await self._response_stream.stop()
            self._response_stream = None
        if self._thinking_stream is not None:
            await self._thinking_stream.stop()
            self._thinking_stream = None
        await self._freeze_markdown()

    async def _freeze_markdown(self) -> None:
        """把完成的 Markdown 子树折叠成单个 Static。

        Textual 的 ``Markdown`` 会把每个块渲染成一个独立子 widget，历史
        消息累积后 widget 数随轮数线性膨胀，拖慢布局 arrange / 重绘 /
        样式级联。流结束后用 Rich 的 Markdown 渲染成**单个** ``Static``
        顶替，widget 数从 O(块) 降到 O(1)。

        整体走 ``app.batch_update()`` —— 4 个异步 mount/remove 合并为
        1 次 layout pass，避免每次操作单独触发 arrange。空内容（``text``
        或 ``thinking`` 为空字符串）不挂 Static，仅 remove 原 Markdown。

        ponytail: 冻结后该条消息失去 Markdown widget 的行内交互与
        MarkdownFence 限高 —— 历史消息只需展示 + 思考折叠，够用。
        已知上限：超长代码块不再自动限高，需要时对 .response Static
        单独设 max-height 即可。
        """
        if self.author != "assistant":
            return
        # 延迟 import，避免无 rich 时启动失败。
        from rich.markdown import Markdown as RichMarkdown

        response = body = None
        try:
            response = self.query_one(".response", Markdown)
        except NoMatches:
            pass
        try:
            body = self.query_one(".thinking-body", Markdown)
        except NoMatches:
            pass

        frozen_resp = frozen_body = None
        if response is not None and self.text:
            frozen_resp = Static(RichMarkdown(self.text), classes="response")
        if body is not None and self.thinking:
            frozen_body = Static(RichMarkdown(self.thinking), classes="thinking-body")
            # 保留当前显隐状态（折叠时 display=False）。
            frozen_body.display = body.display
            # 如果有正文且思考已折叠，确保 frozen_body 也是隐藏的。
            if self.text and self.thoughts_collapsed:
                frozen_body.display = False

        # batch 内 4 个操作合并为 1 次 layout pass。
        with self.app.batch_update():
            if frozen_resp is not None:
                await self.mount(frozen_resp, before=response)
            if response is not None:
                await response.remove()
            if frozen_body is not None:
                await self.mount(frozen_body, before=body)
            if body is not None:
                await body.remove()
        # 标记冻结：此后 watch_text/watch_thinking 直接跳过，
        # 不再对已变成 Static 的节点做 Markdown.update。
        self._frozen = True

    def cancel_streams(self) -> None:
        """取消进行中的流，不等待。

        用于异常路径（不希望在 except 中 await）。直接取 MarkdownStream
        内部的 task 字段取消 —— 引用了 textual 私有字段，但 oterm 也是
        这么做的（已验证在当前 textual 版本下可用）。
        """
        for stream in (self._response_stream, self._thinking_stream):
            task = getattr(stream, "_task", None)
            if task is not None:
                task.cancel()
        self._response_stream = None
        self._thinking_stream = None

    # ------------------------------------------------------------------
    # watcher：只在真正需要 chrome 变化时触发
    # ------------------------------------------------------------------

    async def watch_text(self, text: str) -> None:  # type: ignore[override]
        if self.author != "assistant" or self._frozen:
            return
        try:
            response = self.query_one(".response", Markdown)
        except NoMatches:
            return
        await response.update(text)
        self._refresh_thinking_chrome()

    async def watch_thinking(self, thinking: str) -> None:  # type: ignore[override]
        if self.author != "assistant" or self._frozen:
            return
        try:
            body = self.query_one(".thinking-body", Markdown)
        except NoMatches:
            return
        await body.update(thinking)
        self._refresh_thinking_chrome()

    def watch_thoughts_collapsed(self) -> None:  # type: ignore[override]
        self._refresh_thinking_chrome()

    def _refresh_thinking_chrome(self) -> None:
        """刷新思考块的标签文字与显隐。

        仅在 assistant 模式下有意义；user/tool/error/system 不渲染思考区。
        """
        if self.author != "assistant":
            return
        try:
            label = self.query_one(".thinking-label", Static)
            # 冻结后 body 由 Markdown 变为 Static，故按通用 Widget 查询，
            # 保证历史消息的思考折叠仍可切换。
            body = self.query_one(".thinking-body", Widget)
        except NoMatches:
            return
        has_thinking = bool(self.thinking)
        label.display = has_thinking
        if not has_thinking:
            body.display = False
            return
        label.update("thought")
        body.display = not self.thoughts_collapsed

    # ------------------------------------------------------------------
    # 工具调用（折叠式）
    # ------------------------------------------------------------------

    async def add_tool_call(
        self,
        tool_call_id: str,
        tool_name: str,
        args: Any,
    ) -> None:
        """挂载一个 tool_call widget 到 response 之前。

        Args:
            tool_call_id: 模型返回的工具调用唯一 ID。
            tool_name: 工具名称。
            args: 参数（任意可序列化对象）。
        """
        if self.author != "assistant":
            return
        if tool_call_id in self._tool_calls:
            return
        if len(self._tool_calls) >= _MAX_TOOL_CALLS_PER_ITEM:
            return
        try:
            response = self.query_one(".response", Markdown)
        except NoMatches:
            return
        item = ToolCallItem(tool_name=tool_name, args=args)
        self._tool_calls[tool_call_id] = item
        await self.mount(item, before=response)

    def update_tool_result(self, tool_call_id: str, content: Any) -> None:
        """为已挂载的 tool_call 写入结果。"""
        item = self._tool_calls.get(tool_call_id)
        if item is None:
            return
        item.set_result(content)

    # ------------------------------------------------------------------
    # 思考点击展开
    # ------------------------------------------------------------------

    def on_click(self, event) -> None:  # type: ignore[override]
        """点击思考标签时切换展开/折叠。"""
        cur = event.widget
        while cur is not None and cur is not self:
            if cur.has_class("thinking-label"):
                if self.thinking:
                    self._user_toggled = True
                    self.thoughts_collapsed = not self.thoughts_collapsed
                    self.post_message(
                        self.ThinkingToggled(self, self.thoughts_collapsed)
                    )
                return
            cur = cur.parent  # type: ignore[assignment]
        # 其余点击：复制文本到剪贴板（与 oterm 一致）。
        if self.text:
            self.app.copy_to_clipboard(self.text)


class ToolCallItem(Widget):
    """可折叠的工具调用条目。

    头部显示 ``▸ tool call: <name>``，body 显示参数；结果到达后再补上。
    """

    collapsed: reactive[bool] = reactive(True)

    DEFAULT_CSS = """
    ToolCallItem {
        width: 1fr;
        height: auto;
        margin: 0 0 1 0;
    }

    ToolCallItem .tool-call-header {
        width: 1fr;
        height: auto;
        color: $warning;
        text-style: bold;
    }

    ToolCallItem .tool-call-body {
        width: 1fr;
        height: auto;
        padding: 0 2;
    }
    """

    _NO_RESULT: ClassVar[Any] = object()

    def __init__(
        self,
        tool_name: str,
        args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.tool_name = tool_name
        self.args = args
        self.result: Any = self._NO_RESULT

    def compose(self):  # type: ignore[override]
        # 默认折叠态不挂 body —— 展开时再懒挂，省 1 widget / 折叠 tool call。
        yield Static("", classes="tool-call-header")

    def _ensure_body(self) -> Static:
        """懒挂并返回 body Static（折叠态被移除后会重新挂）。"""
        try:
            return self.query_one(".tool-call-body", Static)
        except NoMatches:
            body = Static("", classes="tool-call-body")
            self.mount(body)
            return body

    def on_mount(self) -> None:
        self._refresh()

    def set_result(self, content: Any) -> None:
        self.result = content
        self._refresh()

    def on_click(self, event) -> None:  # type: ignore[override]
        self.collapsed = not self.collapsed
        event.stop()

    def watch_collapsed(self) -> None:  # type: ignore[override]
        self._refresh()

    def _refresh(self) -> None:
        try:
            header = self.query_one(".tool-call-header", Static)
        except NoMatches:
            return
        arrow = "▸" if self.collapsed else "▾"
        header.update(f"{arrow} tool call: {self.tool_name}")
        if self.collapsed:
            # 折叠态：摘掉 body widget（如已挂），display 留给 CSS 默认。
            try:
                self.query_one(".tool-call-body", Static).remove()
            except NoMatches:
                pass
            return
        body = self._ensure_body()
        # 延迟 import rich 模块，避免无 rich 时启动失败
        from rich.console import Group
        from rich.json import JSON
        from rich.text import Text

        def _format_value(value: Any) -> Any:
            if isinstance(value, (dict, list)):
                return JSON.from_data(value, indent=2)
            if isinstance(value, str):
                try:
                    import json

                    return JSON.from_data(json.loads(value), indent=2)
                except (ValueError, TypeError):
                    return Text(_truncate(value, 1500))
            if value is None:
                return Text("(none)", style="dim italic")
            return Text(_truncate(repr(value), 1500))

        fields: list[Any] = [
            Text("args:", style="bold cyan"),
            _format_value(self.args),
            Text(""),
        ]
        if self.result is not self._NO_RESULT:
            fields.extend(
                [
                    Text("result:", style="bold cyan"),
                    _format_value(self.result),
                    Text(""),
                ]
            )
        body.update(Group(*fields))
        body.display = True


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


__all__ = ["ChatItem", "ToolCallItem", "Author"]
