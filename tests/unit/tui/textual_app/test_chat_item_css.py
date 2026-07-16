#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ChatItem 用户消息气泡主题联动回归。

🚪 Access - 💬 Tests - TUI - ChatItem CSS

用户消息气泡 ``ChatItem.user .text-wrapper`` 的 ``background`` 与
``color`` 都必须引用主题变量（``$xxx``），切主题时气泡的背景和文字应一起
跟随主题变化；硬编码 hex/rgba 会让所有主题看起来一样。
"""

from __future__ import annotations

import re


def _get_chat_item_css() -> str:
    """从 chat_item.py 的源码里抓 ChatItem.DEFAULT_CSS 字符串。"""
    import tui.widgets.chat_item as ci

    src = open(ci.__file__, encoding="utf-8").read()
    m = re.search(r"DEFAULT_CSS\s*=\s*\"\"\"(.*?)\"\"\"", src, re.DOTALL)
    assert m is not None, "ChatItem 没有 DEFAULT_CSS 字符串"
    return m.group(1)


def _selector_body(css: str, selector: str) -> str | None:
    """取 ``<selector> { ... }`` 的 body 字符串。"""
    m = re.search(
        rf"{re.escape(selector)}\s*\{{([^}}]*)",
        css,
        re.DOTALL,
    )
    return m.group(1) if m else None


def test_user_text_wrapper_background_uses_theme_variable() -> None:
    body = _selector_body(_get_chat_item_css(), "ChatItem.user .text-wrapper")
    assert body is not None, "缺少 ChatItem.user .text-wrapper 规则"
    m = re.search(r"background:\s*([^;]+);", body)
    assert m, "ChatItem.user .text-wrapper 缺少 background 声明"
    value = m.group(1).strip()
    assert value.startswith("$"), (
        f"用户气泡背景硬编码为 {value!r}，切主题不会跟随。"
        f"请改用 $primary 30% 等主题变量。"
    )


def test_user_text_wrapper_color_uses_theme_variable() -> None:
    """用户气泡字体颜色也必须是主题变量（默认前景色跟随主题）。"""
    body = _selector_body(_get_chat_item_css(), "ChatItem.user .text-wrapper")
    assert body is not None, "缺少 ChatItem.user .text-wrapper 规则"
    m = re.search(r"color:\s*([^;]+);", body)
    assert m, "ChatItem.user .text-wrapper 缺少 color 声明"
    value = m.group(1).strip()
    assert value.startswith("$"), (
        f"用户气泡颜色硬编码为 {value!r}，应使用 $foreground 跟随主题。"
    )
