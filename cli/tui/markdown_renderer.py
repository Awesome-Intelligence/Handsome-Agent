#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown Renderer - 重新导出自 cli.tui.core.markdown_renderer

🚪 Access - 💬 CLI - Textual UI - Markdown 渲染器

此文件已迁移到 cli/tui/core/markdown_renderer.py，此文件提供向后兼容。

新代码请使用:
    from cli.tui.core.markdown_renderer import ...
"""

# 重新导出自新位置
from cli.tui.core.markdown_renderer import (
    MarkdownRenderer,
    HandsomeAgentRenderer,
    HandsomeAgentMarkdown,
    RichFormatter,
    markdown_to_rich,
    is_markdown_available,
    get_markdown_features,
    MISTUNE_AVAILABLE,
    PYGMENTS_AVAILABLE,
)

__all__ = [
    "MarkdownRenderer",
    "HandsomeAgentRenderer",
    "HandsomeAgentMarkdown",
    "RichFormatter",
    "markdown_to_rich",
    "is_markdown_available",
    "get_markdown_features",
    "MISTUNE_AVAILABLE",
    "PYGMENTS_AVAILABLE",
]
