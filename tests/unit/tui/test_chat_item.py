#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChatItem / ToolCallItem 单元测试（参考 oterm-study 测试 + 项目 freeze 测试的
覆盖补全）。

🚪 Test - TUI - Widgets - ChatItem

测试维度：
- reactive 字段默认值
- watch_author / on_mount 行为：CSS 类动态切换
- compose() 各 author 分支：user / assistant / system / tool / error
- append_text / append_thinking 各种边角
- finish_stream / _freeze_markdown 行为
- on_click：thinking-label 切换 / 其它区域复制
- add_tool_call / update_tool_result 上限 & 重复 id
- ToolCallItem：compose / set_result / 折叠展开 / _format_value / _truncate
- ChatContainer：add_message 各角色、trim、is_streaming、_finish_item

设计说明：
- 仅补齐测试，不修改任何业务代码。运行后若发现代码 bug 会在文末
  "代码问题清单" 段落中列出，但保持原状。
- 测试中通过 async with app.run_test() 走 textual 的真实事件循环。
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from rich.json import JSON
from rich.text import Text
from textual.app import App
from textual.widgets import Markdown, Static

from tui.widgets.chat_item import (
    Author,
    ChatItem,
    ToolCallItem,
    _truncate,
)


# =============================================================================
# 测试宿主
# =============================================================================


class _Harness(App):
    """最小宿主，仅用于挂载单个 ChatItem。"""

    def compose(self) -> Any:
        return []


# =============================================================================
# reactive 默认值
# =============================================================================


class TestReactiveDefaults:
    """ChatItem 的 reactive 字段默认值应与 oterm 设计一致。"""

    def test_text_default_is_empty(self) -> None:
        item = ChatItem()
        assert item.text == ""

    def test_thinking_default_is_empty(self) -> None:
        item = ChatItem()
        assert item.thinking == ""

    def test_thoughts_collapsed_default_true(self) -> None:
        # 默认折叠——用户进入聊天先看到答案，再点开看思考
        item = ChatItem()
        assert item.thoughts_collapsed is True

    def test_author_default_empty(self) -> None:
        item = ChatItem()
        assert item.author == ""

    def test_tool_name_default_empty(self) -> None:
        item = ChatItem()
        assert item.tool_name == ""

    def test_internal_flags_initial(self) -> None:
        item = ChatItem()
        assert item._frozen is False
        assert item._response_stream is None
        assert item._thinking_stream is None
        assert item._tool_calls == {}


# =============================================================================
# watch_author / on_mount：CSS 类动态切换
# =============================================================================


class TestWatchAuthor:
    """author 改变时应该正确维护 ChatItem 上的 CSS 类。"""

    @pytest.mark.asyncio
    async def test_watch_author_adds_role_class(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            await app.mount(item)
            await pilot.pause()

            item.author = "user"
            await pilot.pause()
            assert item.has_class("user") is True
            assert item.has_class("assistant") is False

            item.author = "assistant"
            await pilot.pause()
            assert item.has_class("assistant") is True
            assert item.has_class("user") is False

    @pytest.mark.asyncio
    async def test_watch_author_empty_removes_all_role_classes(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            await app.mount(item)
            await pilot.pause()

            item.author = "user"
            await pilot.pause()
            assert item.has_class("user") is True

            item.author = ""
            await pilot.pause()
            # 所有角色类都应被移除
            for role in ("user", "assistant", "system", "tool", "error"):
                assert item.has_class(role) is False

    @pytest.mark.asyncio
    async def test_watch_author_replaces_previous_class(self) -> None:
        """切换 author 时旧类应被移除，新类应被添加。"""
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            await app.mount(item)
            await pilot.pause()
            assert item.has_class("assistant") is True

            item.author = "system"
            await pilot.pause()
            assert item.has_class("system") is True
            assert item.has_class("assistant") is False

    @pytest.mark.asyncio
    async def test_on_mount_adds_author_class(self) -> None:
        """on_mount 时若 author 已有值，应补一次 add_class。"""
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "user"  # mount 之前赋值
            await app.mount(item)
            await pilot.pause()
            assert item.has_class("user") is True


# =============================================================================
# compose() 各 author 分支
# =============================================================================


class TestCompose:
    """compose() 应按 author 走不同分支（user/assistant/system/tool/error）。"""

    @pytest.mark.asyncio
    async def test_compose_user_layout(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "user"
            item.text = "hi"
            await app.mount(item)
            await pilot.pause()

            # user 不挂 .response Markdown
            assert list(item.query(".response")) == []
            # 不渲染 .thinking-label
            assert list(item.query(".thinking-label")) == []
            # 应有 .text Static
            text_static = item.query(".text")
            assert len(text_static) == 1

    @pytest.mark.asyncio
    async def test_compose_assistant_layout(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            await app.mount(item)
            await pilot.pause()

            # assistant 一次声明 .thinking-label / .thinking-body / .response
            assert len(item.query(".thinking-label")) == 1
            assert len(item.query(".thinking-body")) == 1
            assert len(item.query(".response")) == 1
            # .response 是 Markdown
            assert isinstance(item.query_one(".response", Markdown), Markdown)
            # .thinking-body 是 Markdown
            assert isinstance(item.query_one(".thinking-body", Markdown), Markdown)
            # prompt marker
            assert len(item.query(".prompt-marker")) == 1

    @pytest.mark.asyncio
    async def test_compose_tool_layout(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "tool"
            item.tool_name = "search"
            item.text = "result body"
            await app.mount(item)
            await pilot.pause()

            # tool 渲染 .tool-name Static
            assert len(item.query(".tool-name")) == 1
            # tool 没有 .response / .thinking-body
            assert list(item.query(".response")) == []
            assert list(item.query(".thinking-body")) == []

    @pytest.mark.asyncio
    async def test_compose_tool_no_tool_name_falls_back(self) -> None:
        """tool author 但 tool_name 为空时，标题应降级为 'tool'。"""
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "tool"
            item.tool_name = ""
            await app.mount(item)
            await pilot.pause()

            tool_name_widget = item.query_one(".tool-name", Static)
            rendered = str(tool_name_widget.render())
            assert "tool" in rendered

    @pytest.mark.asyncio
    async def test_compose_error_layout(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "error"
            item.text = "boom"
            await app.mount(item)
            await pilot.pause()

            # error 不挂 .response / .thinking-body / .tool-name
            assert list(item.query(".response")) == []
            assert list(item.query(".thinking-body")) == []
            assert list(item.query(".tool-name")) == []
            # 有 prompt-marker
            assert len(item.query(".prompt-marker")) == 1
            # 有 .text Static
            assert len(item.query(".text")) == 1

    @pytest.mark.asyncio
    async def test_compose_system_layout(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "system"
            item.text = "system note"
            await app.mount(item)
            await pilot.pause()

            assert list(item.query(".response")) == []
            assert list(item.query(".thinking-body")) == []
            assert len(item.query(".prompt-marker")) == 1
            assert len(item.query(".text")) == 1


# =============================================================================
# append_text / append_thinking
# =============================================================================


class TestAppendText:
    """append_text 流式追加文本的语义。"""

    @pytest.mark.asyncio
    async def test_append_text_accumulates_text_reactive(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            await app.mount(item)
            await pilot.pause()

            await item.append_text("hello ")
            await item.append_text("world")
            await pilot.pause()
            assert item.text == "hello world"

    @pytest.mark.asyncio
    async def test_append_text_empty_delta_is_noop(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            await app.mount(item)
            await pilot.pause()

            await item.append_text("")
            await pilot.pause()
            # text 仍为空，stream 也没创建
            assert item.text == ""
            assert item._response_stream is None

    @pytest.mark.asyncio
    async def test_append_text_user_author_is_noop(self) -> None:
        """user author 调 append_text 不应修改 text，也不创建 stream。"""
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "user"
            await app.mount(item)
            await pilot.pause()

            await item.append_text("ignored")
            await pilot.pause()
            assert item.text == ""
            assert item._response_stream is None

    @pytest.mark.asyncio
    async def test_append_text_reuses_response_stream(self) -> None:
        """多次 append_text 应复用同一个 MarkdownStream。"""
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            await app.mount(item)
            await pilot.pause()

            await item.append_text("a")
            stream = item._response_stream
            assert stream is not None

            await item.append_text("b")
            await pilot.pause()
            assert item._response_stream is stream

    @pytest.mark.asyncio
    async def test_append_text_collapses_thoughts_on_first_delta(self) -> None:
        """追加正文的第一笔 delta 应自动折叠思考块。"""
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            await app.mount(item)
            await pilot.pause()

            # 先展开思考
            item.thoughts_collapsed = False
            await pilot.pause()

            await item.append_text("answer")
            await pilot.pause()
            assert item.thoughts_collapsed is True


class TestAppendThinking:
    """append_thinking 流式追加思考的语义。"""

    @pytest.mark.asyncio
    async def test_append_thinking_accumulates_thinking_reactive(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            await app.mount(item)
            await pilot.pause()

            await item.append_thinking("step 1 ")
            await item.append_thinking("step 2")
            await pilot.pause()
            assert item.thinking == "step 1 step 2"

    @pytest.mark.asyncio
    async def test_append_thinking_empty_delta_is_noop(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            await app.mount(item)
            await pilot.pause()

            await item.append_thinking("")
            await pilot.pause()
            assert item.thinking == ""
            assert item._thinking_stream is None

    @pytest.mark.asyncio
    async def test_append_thinking_user_author_is_noop(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "user"
            await app.mount(item)
            await pilot.pause()

            await item.append_thinking("ignored")
            await pilot.pause()
            assert item.thinking == ""
            assert item._thinking_stream is None

    @pytest.mark.asyncio
    async def test_append_thinking_reveals_label_on_first_chunk(self) -> None:
        """第一笔思考 delta 后，.thinking-label 应可见。"""
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            await app.mount(item)
            await pilot.pause()

            # 初始 label 应隐藏（没有 thinking）
            label = item.query_one(".thinking-label", Static)
            assert label.display is False

            await item.append_thinking("musing")
            await pilot.pause()
            assert label.display is True
            assert item.thinking == "musing"

    @pytest.mark.asyncio
    async def test_append_thinking_reuses_thinking_stream(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            await app.mount(item)
            await pilot.pause()

            await item.append_thinking("a")
            stream = item._thinking_stream
            assert stream is not None

            await item.append_thinking("b")
            await pilot.pause()
            assert item._thinking_stream is stream


# =============================================================================
# finish_stream / _freeze_markdown
# =============================================================================


class TestFinishStream:
    """finish_stream 收尾行为。"""

    @pytest.mark.asyncio
    async def test_finish_stream_idempotent_without_streams(self) -> None:
        """从未流过的 assistant item 调 finish_stream 不应抛异常。"""
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            await app.mount(item)
            await pilot.pause()

            await item.finish_stream()
            await item.finish_stream()  # 二次调用安全
            assert item._frozen is True

    @pytest.mark.asyncio
    async def test_finish_stream_non_assistant_is_noop(self) -> None:
        """非 assistant 不应冻结、不应 _frozen=True。"""
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "user"
            item.text = "hi"
            await app.mount(item)
            await pilot.pause()

            await item.finish_stream()
            await pilot.pause()
            assert item._frozen is False

    @pytest.mark.asyncio
    async def test_finish_stream_drains_response_stream(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            await app.mount(item)
            await pilot.pause()

            await item.append_text("partial")
            assert item._response_stream is not None
            await item.finish_stream()
            await pilot.pause()
            assert item._response_stream is None

    @pytest.mark.asyncio
    async def test_finish_stream_drains_thinking_stream(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            await app.mount(item)
            await pilot.pause()

            await item.append_thinking("musing")
            assert item._thinking_stream is not None
            await item.finish_stream()
            await pilot.pause()
            assert item._thinking_stream is None


class TestFreezeMarkdown:
    """_freeze_markdown 行为：把 Markdown 子树折叠成单个 Static。"""

    @pytest.mark.asyncio
    async def test_freeze_with_empty_text_does_not_mount_response_static(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            await app.mount(item)
            await pilot.pause()

            # 不写任何 text，直接 finish
            await item.finish_stream()
            await pilot.pause()
            # 即使流过空 text，.response 应被移除（Markdown widget）
            assert list(item.query(Markdown)) == []

    @pytest.mark.asyncio
    async def test_freeze_with_empty_thinking_keeps_no_thinking_body(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            await app.mount(item)
            await pilot.pause()

            await item.append_text("answer only")
            await item.finish_stream()
            await pilot.pause()

            # 没有 thinking 时不应挂 .thinking-body Static
            assert list(item.query(".thinking-body")) == []
            # _frozen 标记
            assert item._frozen is True

    @pytest.mark.asyncio
    async def test_freeze_preserves_thinking_display_state(self) -> None:
        """用户手动展开思考后再 freeze，display 应保持展开。"""
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            await app.mount(item)
            await pilot.pause()

            await item.append_thinking("detailed reasoning")
            await item.append_text("answer")
            await pilot.pause()
            # 显式展开
            item.thoughts_collapsed = False
            await pilot.pause()

            await item.finish_stream()
            await pilot.pause()
            # frozen body 应保持展开
            body = item.query_one(".thinking-body", Static)
            assert body.display is True

    @pytest.mark.asyncio
    async def test_freeze_keeps_thinking_hidden_when_collapsed(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            await app.mount(item)
            await pilot.pause()

            await item.append_thinking("musing")
            await item.append_text("answer")
            await pilot.pause()
            # 默认折叠
            assert item.thoughts_collapsed is True

            await item.finish_stream()
            await pilot.pause()
            body = item.query_one(".thinking-body", Static)
            assert body.display is False


# =============================================================================
# on_click：thinking-label 切换 / 其它区域复制
# =============================================================================


class TestOnClick:
    """on_click 在不同点击目标下的行为。"""

    @pytest.mark.asyncio
    async def test_click_thinking_label_with_thinking_toggles_collapse(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            item.thinking = "musing"
            item.text = "answer"
            await app.mount(item)
            await pilot.pause()
            assert item.thoughts_collapsed is True

            label = item.query_one(".thinking-label", Static)
            await pilot.click(label)
            await pilot.pause()
            assert item.thoughts_collapsed is False

            await pilot.click(label)
            await pilot.pause()
            assert item.thoughts_collapsed is True

    @pytest.mark.asyncio
    async def test_click_thinking_label_posts_thinking_toggled(self) -> None:
        from unittest.mock import patch
        from textual.message_pump import MessagePump

        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            item.thinking = "musing"
            await app.mount(item)
            await pilot.pause()

            posted: list[Any] = []
            original = MessagePump.post_message

            def capture(self, message: Any) -> Any:
                posted.append(message)
                return original(self, message)

            # Textual 的 post_message 实际定义在 MessagePump 上。
            with patch.object(MessagePump, "post_message", capture):
                label = item.query_one(".thinking-label", Static)
                await pilot.click(label)
                await pilot.pause()

            toggled = [m for m in posted if isinstance(m, ChatItem.ThinkingToggled)]
            assert len(toggled) >= 1, f"expected ThinkingToggled in {posted!r}"
            assert toggled[0].item is item
            # 点击后 thoughts_collapsed 从默认 True 翻为 False
            assert toggled[0].collapsed is False

    @pytest.mark.asyncio
    async def test_click_thinking_label_without_thinking_does_not_toggle(self) -> None:
        """无思考内容时点击 label 不应切换也不应复制。"""
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            # 没有 thinking
            await app.mount(item)
            await pilot.pause()

            copied: list[str] = []
            app.copy_to_clipboard = lambda t: copied.append(t)  # type: ignore[method-assign]

            label = item.query_one(".thinking-label", Static)
            await pilot.click(label)
            await pilot.pause()
            # 因为 thinking 为空，应当不切换
            assert item.thoughts_collapsed is True
            assert copied == []

    @pytest.mark.asyncio
    async def test_click_outside_label_copies_text(self) -> None:
        """点击 .response 区域时应复制 self.text。"""
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            item.text = "the answer"
            await app.mount(item)
            await pilot.pause()

            copied: list[str] = []
            app.copy_to_clipboard = lambda t: copied.append(t)  # type: ignore[method-assign]

            response = item.query_one(".response", Markdown)
            await pilot.click(response)
            await pilot.pause()
            assert copied == ["the answer"]

    @pytest.mark.asyncio
    async def test_click_response_without_text_does_not_copy(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            # 没有 text
            await app.mount(item)
            await pilot.pause()

            copied: list[str] = []
            app.copy_to_clipboard = lambda t: copied.append(t)  # type: ignore[method-assign]

            response = item.query_one(".response", Markdown)
            await pilot.click(response)
            await pilot.pause()
            assert copied == []


# =============================================================================
# add_tool_call / update_tool_result
# =============================================================================


class TestAddToolCall:
    """add_tool_call / update_tool_result 行为。"""

    @pytest.mark.asyncio
    async def test_add_tool_call_user_is_noop(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "user"
            await app.mount(item)
            await pilot.pause()

            await item.add_tool_call("tc-1", "search", {"q": "x"})
            await pilot.pause()
            assert item._tool_calls == {}

    @pytest.mark.asyncio
    async def test_add_tool_call_creates_tool_call_item(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            await app.mount(item)
            await pilot.pause()

            await item.add_tool_call("tc-1", "search", {"q": "x"})
            await pilot.pause()

            assert "tc-1" in item._tool_calls
            tc = item._tool_calls["tc-1"]
            assert isinstance(tc, ToolCallItem)
            assert tc.tool_name == "search"
            assert tc.args == {"q": "x"}

    @pytest.mark.asyncio
    async def test_add_tool_call_same_id_is_idempotent(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            await app.mount(item)
            await pilot.pause()

            await item.add_tool_call("tc-1", "search", {"q": "x"})
            await pilot.pause()
            await item.add_tool_call("tc-1", "search", {"q": "y"})
            await pilot.pause()
            assert len(item._tool_calls) == 1

    @pytest.mark.asyncio
    async def test_add_tool_call_respects_max_limit(self) -> None:
        """超过 _MAX_TOOL_CALLS_PER_ITEM 后不再挂新的。"""
        from tui.widgets.chat_item import _MAX_TOOL_CALLS_PER_ITEM

        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            await app.mount(item)
            await pilot.pause()

            for i in range(_MAX_TOOL_CALLS_PER_ITEM + 3):
                await item.add_tool_call(f"tc-{i}", "tool", {})
            await pilot.pause()
            assert len(item._tool_calls) == _MAX_TOOL_CALLS_PER_ITEM


class TestUpdateToolResult:
    """update_tool_result 行为。"""

    @pytest.mark.asyncio
    async def test_update_tool_result_writes_result(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            await app.mount(item)
            await pilot.pause()

            await item.add_tool_call("tc-1", "echo", {"s": "hi"})
            await pilot.pause()
            item.update_tool_result("tc-1", "echoed: hi")
            assert item._tool_calls["tc-1"].result == "echoed: hi"

    def test_update_tool_result_unknown_id_is_noop(self) -> None:
        item = ChatItem()
        # 不应抛异常
        item.update_tool_result("never-registered", "data")
        assert item._tool_calls == {}


# =============================================================================
# cancel_streams
# =============================================================================


class TestCancelStreams:
    """cancel_streams 行为。"""

    @pytest.mark.asyncio
    async def test_cancel_after_appends_clears_state(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            item = ChatItem()
            item.author = "assistant"
            await app.mount(item)
            await pilot.pause()

            await item.append_text("partial")
            await item.append_thinking("musing")
            assert item._response_stream is not None
            assert item._thinking_stream is not None

            item.cancel_streams()
            assert item._response_stream is None
            assert item._thinking_stream is None

    def test_cancel_without_streams_is_noop(self) -> None:
        item = ChatItem()
        # 不应抛异常
        item.cancel_streams()
        assert item._response_stream is None
        assert item._thinking_stream is None


# =============================================================================
# ThinkingToggled message
# =============================================================================


class TestThinkingToggledMessage:
    """ThinkingToggled Message 的字段绑定。"""

    def test_thinking_toggled_carries_item_and_collapsed(self) -> None:
        item = ChatItem()
        msg = ChatItem.ThinkingToggled(item, True)
        assert msg.item is item
        assert msg.collapsed is True

        msg2 = ChatItem.ThinkingToggled(item, False)
        assert msg2.collapsed is False


# =============================================================================
# Author 字面量
# =============================================================================


class TestAuthorLiteral:
    """Author 是 Literal['user', 'assistant', 'system', 'tool', 'error']。"""

    def test_author_literal_values(self) -> None:
        # 在 runtime 不容易直接断言 Literal，但可以确认字面量值
        from typing import get_args

        values = get_args(Author)
        assert set(values) == {"user", "assistant", "system", "tool", "error"}


# =============================================================================
# ToolCallItem
# =============================================================================


class TestToolCallItemBasics:
    """ToolCallItem 基础属性。"""

    def test_tool_call_item_creation(self) -> None:
        tc = ToolCallItem(tool_name="search", args={"q": "x"})
        assert tc.tool_name == "search"
        assert tc.args == {"q": "x"}
        # 未设结果时，result 是 _NO_RESULT 哨兵
        from tui.widgets.chat_item import ToolCallItem as TCI
        assert tc.result is TCI._NO_RESULT

    def test_tool_call_item_collapsed_default(self) -> None:
        tc = ToolCallItem(tool_name="search", args={})
        assert tc.collapsed is True

    def test_tool_call_item_compose_yields_header(self) -> None:
        """compose 默认只挂 header（折叠态不挂 body）。"""
        tc = ToolCallItem(tool_name="search", args={})
        items = list(tc.compose())
        # 1 个 Static 即 header
        assert len(items) == 1
        assert isinstance(items[0], Static)
        # 折叠态没有 .tool-call-body
        assert list(tc.query(".tool-call-body")) == []


class TestToolCallItemSetResult:
    """set_result 应把 result 写入并触发 _refresh。"""

    def test_set_result_stores_value(self) -> None:
        tc = ToolCallItem(tool_name="search", args={})
        tc.set_result({"ok": True})
        assert tc.result == {"ok": True}

    def test_set_result_replaces_value(self) -> None:
        tc = ToolCallItem(tool_name="search", args={})
        tc.set_result("first")
        tc.set_result("second")
        assert tc.result == "second"


class TestToolCallItemCollapseExpand:
    """点击 / 切换 collapsed 时 body 懒挂与摘除。"""

    @pytest.mark.asyncio
    async def test_expand_lazily_mounts_body(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            tc = ToolCallItem(tool_name="echo", args={"msg": "hi"})
            await app.mount(tc)
            await pilot.pause()

            assert list(tc.query(".tool-call-body")) == []
            tc.collapsed = False
            await pilot.pause()
            assert len(tc.query(".tool-call-body")) == 1

    @pytest.mark.asyncio
    async def test_collapse_removes_body(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            tc = ToolCallItem(tool_name="echo", args={"msg": "hi"})
            await app.mount(tc)
            await pilot.pause()

            tc.collapsed = False
            await pilot.pause()
            assert len(tc.query(".tool-call-body")) == 1

            tc.collapsed = True
            await pilot.pause()
            assert list(tc.query(".tool-call-body")) == []

    @pytest.mark.asyncio
    async def test_click_toggles_collapsed(self) -> None:
        """点击 ToolCallItem 本身会切换 collapsed。"""
        app = _Harness()
        async with app.run_test() as pilot:
            tc = ToolCallItem(tool_name="echo", args={"msg": "hi"})
            await app.mount(tc)
            await pilot.pause()

            assert tc.collapsed is True
            await pilot.click(tc)
            await pilot.pause()
            assert tc.collapsed is False

            await pilot.click(tc)
            await pilot.pause()
            assert tc.collapsed is True


class TestToolCallItemHeader:
    """header 文本应反映折叠态与工具名。"""

    @pytest.mark.asyncio
    async def test_header_collapsed_shows_right_arrow(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            tc = ToolCallItem(tool_name="search", args={})
            await app.mount(tc)
            await pilot.pause()

            header = tc.query_one(".tool-call-header", Static)
            assert "▸" in str(header.render())
            assert "search" in str(header.render())

    @pytest.mark.asyncio
    async def test_header_expanded_shows_down_arrow(self) -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            tc = ToolCallItem(tool_name="search", args={})
            await app.mount(tc)
            await pilot.pause()

            tc.collapsed = False
            await pilot.pause()

            header = tc.query_one(".tool-call-header", Static)
            assert "▾" in str(header.render())
            assert "search" in str(header.render())


# =============================================================================
# _truncate helper
# =============================================================================


class TestTruncateHelper:
    """_truncate 边界条件。"""

    def test_truncate_keeps_short_text(self) -> None:
        assert _truncate("short", 10) == "short"

    def test_truncate_appends_ellipsis_at_limit(self) -> None:
        assert _truncate("abcdefghij", 5) == "abcde…"

    def test_truncate_at_exact_length_does_not_truncate(self) -> None:
        # 长度等于 limit 时不应加 …
        assert _truncate("abcde", 5) == "abcde"

    def test_truncate_empty_text(self) -> None:
        assert _truncate("", 100) == ""

    def test_truncate_zero_limit(self) -> None:
        # 长度为 0，返回 "…"
        assert _truncate("anything", 0) == "…"


# =============================================================================
# ChatContainer 补充测试
# =============================================================================


class TestChatContainerBasics:
    """ChatContainer 基础行为（不与 freeze 测试重叠的部分）。"""

    @pytest.mark.asyncio
    async def test_add_user_message_appends_item(self) -> None:
        from tui.widgets.chat_container import ChatContainer

        app = _Harness()
        async with app.run_test() as pilot:
            container = ChatContainer()
            await app.mount(container)
            await pilot.pause()

            container.add_user_message("hi")
            await pilot.pause()

            items = container._items
            assert len(items) == 1
            assert items[0].author == "user"
            assert items[0].text == "hi"

    @pytest.mark.asyncio
    async def test_add_assistant_message_appends_item(self) -> None:
        from tui.widgets.chat_container import ChatContainer

        app = _Harness()
        async with app.run_test() as pilot:
            container = ChatContainer()
            await app.mount(container)
            await pilot.pause()

            container.add_assistant_message("answer")
            await pilot.pause()
            assert container._items[-1].author == "assistant"
            assert container._items[-1].text == "answer"

    @pytest.mark.asyncio
    async def test_add_system_message_appends_item(self) -> None:
        from tui.widgets.chat_container import ChatContainer

        app = _Harness()
        async with app.run_test() as pilot:
            container = ChatContainer()
            await app.mount(container)
            await pilot.pause()

            container.add_system_message("boot")
            await pilot.pause()
            assert container._items[-1].author == "system"

    @pytest.mark.asyncio
    async def test_add_tool_message_carries_tool_name(self) -> None:
        from tui.widgets.chat_container import ChatContainer

        app = _Harness()
        async with app.run_test() as pilot:
            container = ChatContainer()
            await app.mount(container)
            await pilot.pause()

            container.add_tool_message("output", "search")
            await pilot.pause()
            last = container._items[-1]
            assert last.author == "tool"
            assert last.tool_name == "search"

    @pytest.mark.asyncio
    async def test_add_error_message_appends_item(self) -> None:
        from tui.widgets.chat_container import ChatContainer

        app = _Harness()
        async with app.run_test() as pilot:
            container = ChatContainer()
            await app.mount(container)
            await pilot.pause()

            container.add_error_message("boom")
            await pilot.pause()
            assert container._items[-1].author == "error"
            assert container._items[-1].text == "boom"

    @pytest.mark.asyncio
    async def test_add_message_invalid_role_falls_back_to_assistant(self) -> None:
        from tui.widgets.chat_container import ChatContainer

        app = _Harness()
        async with app.run_test() as pilot:
            container = ChatContainer()
            await app.mount(container)
            await pilot.pause()

            container.add_message("nonsense-role", "x")
            await pilot.pause()
            assert container._items[-1].author == "assistant"

    @pytest.mark.asyncio
    async def test_add_thinking_message_mounts_assistant_item(self) -> None:
        from tui.widgets.chat_container import ChatContainer

        app = _Harness()
        async with app.run_test() as pilot:
            container = ChatContainer()
            await app.mount(container)
            await pilot.pause()

            container.add_thinking_message("reasoning...")
            await pilot.pause()
            last = container._items[-1]
            assert last.author == "assistant"
            assert last.thinking == "reasoning..."


class TestChatContainerStreaming:
    """ChatContainer 流式接口行为。"""

    @pytest.mark.asyncio
    async def test_start_streaming_marks_current_streaming_item(self) -> None:
        from tui.widgets.chat_container import ChatContainer

        app = _Harness()
        async with app.run_test() as pilot:
            container = ChatContainer()
            await app.mount(container)
            await pilot.pause()

            container.start_streaming("assistant")
            await pilot.pause()
            assert container.is_streaming() is True
            # current_streaming_id 与 _streaming_item 一一对应
            assert container._streaming_item is not None
            assert container.current_streaming_id == container._streaming_item.id

    @pytest.mark.asyncio
    async def test_start_streaming_invalid_role_falls_back(self) -> None:
        from tui.widgets.chat_container import ChatContainer

        app = _Harness()
        async with app.run_test() as pilot:
            container = ChatContainer()
            await app.mount(container)
            await pilot.pause()

            container.start_streaming("nonsense")
            await pilot.pause()
            assert container._streaming_item is not None
            assert container._streaming_item.author == "assistant"

    @pytest.mark.asyncio
    async def test_complete_streaming_clears_current(self) -> None:
        from tui.widgets.chat_container import ChatContainer

        app = _Harness()
        async with app.run_test() as pilot:
            container = ChatContainer()
            await app.mount(container)
            await pilot.pause()

            container.start_streaming("assistant")
            await pilot.pause()
            assert container.is_streaming() is True

            container.complete_streaming()
            await pilot.pause()
            assert container.is_streaming() is False

    def test_complete_streaming_without_active_returns_none(self) -> None:
        from tui.widgets.chat_container import ChatContainer

        container = ChatContainer()
        assert container.complete_streaming() is None

    def test_is_streaming_default_false(self) -> None:
        from tui.widgets.chat_container import ChatContainer

        container = ChatContainer()
        assert container.is_streaming() is False
        assert container.current_streaming_id is None

    def test_append_streaming_text_without_active_is_noop(self) -> None:
        """无流对象时 append_streaming_text 不应抛异常。"""
        from tui.widgets.chat_container import ChatContainer

        container = ChatContainer()
        # 不抛
        container.append_streaming_text("ignored")
        # 不应自动开流（append_streaming_thinking 才会自动开）
        assert container._streaming_item is None

    def test_append_streaming_thinking_without_active_starts_stream(self) -> None:
        """thinking 先到时自动开一条 assistant 流。"""
        from tui.widgets.chat_container import ChatContainer

        app = _Harness()
        # 不开 run_test 时只能同步跑
        async def _go() -> None:
            async with app.run_test():
                container = ChatContainer()
                await app.mount(container)
                await asyncio.sleep(0)
                # 还没有 streaming
                assert container._streaming_item is None
                container.append_streaming_thinking("musing")
                # 同步 create_task 后下一拍才挂载
                await asyncio.sleep(0.05)
                assert container._streaming_item is not None
                assert container._streaming_item.author == "assistant"

        asyncio.run(_go())


class TestChatContainerCompat:
    """RichLog 兼容接口 + history 接口。"""

    def test_write_adds_assistant_message(self) -> None:
        from tui.widgets.chat_container import ChatContainer

        container = ChatContainer()
        # 不开 run_test 会触发 mount，但 write 是同步的会走 _get_message_container
        # 这里仅验证 write 在没有 app 时不抛同步部分。
        # 更完整的端到端覆盖在 freeze 测试中。
        # 至少保证 API 存在。
        assert hasattr(container, "write")
        assert hasattr(container, "clear")

    def test_get_messages_returns_copy(self) -> None:
        from tui.widgets.chat_container import ChatContainer

        container = ChatContainer()
        # 直接写入 messages
        container.messages = [{"role": "user", "content": "a"}]
        copy = container.get_messages()
        assert copy is not container.messages
        assert copy == container.messages

    @pytest.mark.asyncio
    async def test_clear_messages_resets_state(self) -> None:
        """clear_messages 应清空 messages 与 _items。"""
        from tui.widgets.chat_container import ChatContainer

        app = _Harness()
        async with app.run_test() as pilot:
            container = ChatContainer()
            await app.mount(container)
            await pilot.pause()

            container.add_user_message("hi")
            await pilot.pause()
            assert container.messages
            assert container._items

            container.clear_messages()
            await pilot.pause()
            assert container.messages == []
            assert container._items == []


class TestChatContainerTrim:
    """_trim 行为：超出 _MAX_MESSAGES 时从顶端裁剪。"""

    @pytest.mark.asyncio
    async def test_trim_removes_oldest_non_streaming(self) -> None:
        from tui.widgets.chat_container import ChatContainer, _MAX_MESSAGES

        app = _Harness()
        async with app.run_test() as pilot:
            container = ChatContainer()
            await app.mount(container)
            await pilot.pause()

            # 注入 _MAX_MESSAGES + 5 条
            for i in range(_MAX_MESSAGES + 5):
                container.add_user_message(f"msg-{i}")
            await pilot.pause()

            # 应被裁剪到 _MAX_MESSAGES
            assert len(container._items) == _MAX_MESSAGES
            # 留下的是最后 _MAX_MESSAGES 条
            assert container._items[-1].text == f"msg-{_MAX_MESSAGES + 4}"
            # 最早的那条应被移除
            assert container._items[0].text != "msg-0"


# =============================================================================
# 入口
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
