#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ChatItem 流结束后的 Markdown 冻结行为测试。

🧪 Test - 验证 finish_stream 把多子 widget 的 Markdown 折叠成单个 Static，
消除历史消息随轮数增长的 widget 膨胀（TUI 卡顿结构性优化）。
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from textual.app import App
from textual.widgets import Markdown, Static


class _Harness(App):
    """最小宿主，仅用于挂载单个 ChatItem。"""

    def compose(self):
        return []


@pytest.mark.asyncio
async def test_finish_stream_freezes_markdown_into_single_static():
    """流式期间是活的 Markdown；finish_stream 后应无 Markdown、留单个 Static。"""
    from tui.widgets.chat_item import ChatItem

    app = _Harness()
    async with app.run_test():
        item = ChatItem()
        item.author = "assistant"
        await app.mount(item)

        await item.append_text("# 标题\n\n正文 **加粗**")
        # 流式中：response 仍是 Markdown widget（会展开成多个块 widget）。
        assert len(item.query(Markdown)) >= 1

        await item.finish_stream()

        # 冻结后：不再有任何 Markdown 子 widget，widget 数塌缩为 O(1)。
        assert len(item.query(Markdown)) == 0
        # .response 变为承载 Rich Markdown 的单个 Static。
        response = item.query_one(".response", Static)
        assert response is not None


@pytest.mark.asyncio
async def test_finish_stream_freezes_thinking_and_preserves_hidden_state():
    """思考块冻结后仍是隐藏态（已折叠），且不再是 Markdown。"""
    from tui.widgets.chat_item import ChatItem

    app = _Harness()
    async with app.run_test():
        item = ChatItem()
        item.author = "assistant"
        await app.mount(item)

        await item.append_thinking("推理过程")
        await item.append_text("最终答案")  # 有正文 -> 思考默认折叠隐藏
        await item.finish_stream()

        assert len(item.query(Markdown)) == 0
        thinking = item.query_one(".thinking-body", Static)
        # 有正文时思考默认折叠，冻结应保留隐藏状态。
        assert thinking.display is False


@pytest.mark.asyncio
async def test_watch_text_after_freeze_does_not_crash():
    """冻结后 .response 变 Static，watcher 触发不应抛 WrongType。"""
    from tui.widgets.chat_item import ChatItem

    app = _Harness()
    async with app.run_test():
        item = ChatItem()
        item.author = "assistant"
        await app.mount(item)

        await item.append_text("正文")
        await item.finish_stream()

        # 直接给 reactive 赋值会触发 watch_text；冻结后应安全跳过。
        item.text = ""
        item.text = "又来一次"
        item.thinking = "再触发思考 watcher"
        # 走到这里没抛异常即通过。
        assert item._frozen is True


# =============================================================================
# 优化新增测试（TUI 卡顿结构性优化）
# =============================================================================


@pytest.mark.asyncio
async def test_finish_stream_skips_redundant_markdown_update():
    """finish_stream 期间不应调 Markdown.update —— MarkdownStream.stop()
    已 flush 全部 pending，_freeze_markdown 会把整棵换掉，中间的 update
    重复 parse + mount_all 是浪费。"""
    from tui.widgets.chat_item import ChatItem

    app = _Harness()
    async with app.run_test():
        item = ChatItem()
        item.author = "assistant"
        await app.mount(item)

        await item.append_text("# 标题\n\n正文")

        # 计数 finish_stream 期间的 Markdown.update 调用。
        with patch.object(
            Markdown, "update", wraps=Markdown.update, autospec=True
        ) as update_spy:
            await item.finish_stream()

        assert update_spy.call_count == 0, (
            "Markdown.update 在 finish_stream 中被调用："
            f"{update_spy.call_count} 次（应为 0）"
        )


@pytest.mark.asyncio
async def test_freeze_uses_single_batch_update_window():
    """_freeze_markdown 把 4 个 mount/remove 操作合并在 1 个 batch_update
    窗口内，避免每个操作触发独立 layout pass。"""
    from tui.widgets.chat_item import ChatItem

    app = _Harness()
    async with app.run_test():
        item = ChatItem()
        item.author = "assistant"
        await app.mount(item)

        await item.append_text("# 标题")
        await item.append_thinking("思考片段")

        # 在 freeze 前后记录 _batch_count，断言 freeze 期间 batch_count
        # 的峰值稳定在 1（而不是 4）。
        observed: list[int] = []

        original_begin = app._begin_batch
        original_end = app._end_batch

        def tracked_begin() -> None:
            original_begin()
            observed.append(app._batch_count)

        def tracked_end() -> None:
            original_end()
            observed.append(app._batch_count)

        app._begin_batch = tracked_begin  # type: ignore[method-assign]
        app._end_batch = tracked_end  # type: ignore[method-assign]

        try:
            await item.finish_stream()
        finally:
            app._begin_batch = original_begin  # type: ignore[method-assign]
            app._end_batch = original_end  # type: ignore[method-assign]

        # _freeze_markdown 自身开了 1 个 batch_update。其它路径（流式
        # append 等）也可能 begin/end。断言观察期内 _batch_count 的峰值
        # 不超过 1 即可（无嵌套 batch）。
        if observed:
            assert max(observed) == 1, (
                "freeze 期间出现嵌套 batch_update 窗口："
                f"峰值 {max(observed)}（应为 1）"
            )
        # 收尾后 _batch_count 必须归 0。
        assert app._batch_count == 0


@pytest.mark.asyncio
async def test_clear_messages_batches_removes():
    """clear_messages 应在 1 个 batch_update 窗口内完成所有 child remove。"""
    from tui.widgets.chat_container import ChatContainer
    from tui.widgets.chat_item import ChatItem

    app = _Harness()
    async with app.run_test() as pilot:
        container = ChatContainer()
        await app.mount(container)
        await pilot.pause()

        # 挂 5 条消息到内部的 messageContainer
        message_container = container._get_message_container()
        for i in range(5):
            item = ChatItem()
            item.author = "user"
            item.text = f"msg-{i}"
            await message_container.mount(item)
            container._items.append(item)
        await pilot.pause()

        # 记录 _batch_count 在 clear_messages 期间的值
        observed: list[int] = []

        original_begin = app._begin_batch
        original_end = app._end_batch

        def tracked_begin() -> None:
            original_begin()
            observed.append(app._batch_count)

        def tracked_end() -> None:
            original_end()
            observed.append(app._batch_count)

        app._begin_batch = tracked_begin  # type: ignore[method-assign]
        app._end_batch = tracked_end  # type: ignore[method-assign]

        try:
            container.clear_messages()
            await pilot.pause()
        finally:
            app._begin_batch = original_begin  # type: ignore[method-assign]
            app._end_batch = original_end  # type: ignore[method-assign]

        assert len(message_container.children) == 0
        assert container._items == []
        # 应当开过 1 个 batch_update 窗口（begin 把 count 推到 1，end 拉回 0）。
        assert 1 in observed, (
            f"clear_messages 未走 batch_update：observed={observed}"
        )
        # 收尾归 0。
        assert app._batch_count == 0


@pytest.mark.asyncio
async def test_tool_call_collapsed_has_no_body_widget():
    """ToolCallItem 折叠态不挂 body widget —— 展开时懒挂，折叠时摘除。"""
    from tui.widgets.chat_item import ChatItem, ToolCallItem

    app = _Harness()
    async with app.run_test() as pilot:
        item = ChatItem()
        item.author = "assistant"
        await app.mount(item)

        tc = ToolCallItem(tool_name="echo", args={"msg": "hi"})
        await item.mount(tc)
        await pilot.pause()

        # 默认 collapsed=True，body 应不存在。
        assert tc.collapsed is True
        assert len(tc.query(".tool-call-body")) == 0

        # 展开：body 懒挂出现。
        tc.collapsed = False
        await pilot.pause()
        assert len(tc.query(".tool-call-body")) == 1

        # 再次折叠：body 被摘除。
        tc.collapsed = True
        await pilot.pause()
        assert len(tc.query(".tool-call-body")) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

