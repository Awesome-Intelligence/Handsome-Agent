#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown Renderer for Textual TUI.

🚪 Access - 💬 CLI - Textual UI - Markdown 渲染器

提供 Markdown 渲染功能，支持：
- 标准 Markdown 语法（标题、列表、链接、图片等）
- 代码高亮（语法高亮）
- 表格渲染
- 任务列表
- 自定义样式

依赖:
- mistune (推荐): pip install mistune
- pygments (可选，用于代码高亮): pip install pygments

Usage::

    from cli.tui.core.markdown_renderer import MarkdownRenderer, markdown_to_rich

    renderer = MarkdownRenderer()
    rich_content = renderer.render(markdown_text)
"""

from __future__ import annotations

import re
from typing import Optional

# 降级机制
MISTUNE_AVAILABLE = True
MISTUNE_IMPORT_ERROR: str | None = None

try:
    import mistune
except ImportError as e:
    MISTUNE_AVAILABLE = False
    MISTUNE_IMPORT_ERROR = str(e)

# Pygments 用于代码高亮
PYGMENTS_AVAILABLE = True
PYGMENTS_IMPORT_ERROR: str | None = None

try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, TextLexer
    from pygments.formatters import Terminal256Formatter
except ImportError as e:
    PYGMENTS_AVAILABLE = False
    PYGMENTS_IMPORT_ERROR = str(e)


# ============================================================================
# Rich 格式化工具
# ============================================================================

class RichFormatter:
    """将 Markdown 转换为 Rich 格式文本的工具类."""

    # ANSI 颜色代码 (用于终端)
    COLORS = {
        # 标题颜色
        "h1": "#58a6ff",  # 蓝色
        "h2": "#3fb950",  # 绿色
        "h3": "#a371f7",  # 紫色
        "h4": "#f0883e",  # 橙色
        "h5": "#f85149",  # 红色
        "h6": "#8b949e",  # 灰色
        # 其他颜色
        "link": "#58a6ff",
        "code": "#f0883e",
        "code_bg": "#161b22",
        "blockquote": "#8b949e",
        "blockquote_border": "#30363d",
        "table_header": "#c9d1d9",
        "table_border": "#30363d",
        "list_marker": "#58a6ff",
        "task_checked": "#3fb950",
        "task_unchecked": "#6e7681",
        "hr": "#30363d",
        "emphasis": "#c9d1d9",
        "strong": "#ffffff",
        "strikethrough": "#6e7681",
    }

    @classmethod
    def format_h1(cls, text: str) -> str:
        """格式化一级标题."""
        return f"[bold {cls.COLORS['h1']}]▌ {text}[/]\n"

    @classmethod
    def format_h2(cls, text: str) -> str:
        """格式化二级标题."""
        return f"[bold {cls.COLORS['h2']}]## {text}[/]\n"

    @classmethod
    def format_h3(cls, text: str) -> str:
        """格式化三级标题."""
        return f"[bold {cls.COLORS['h3']}]### {text}[/]\n"

    @classmethod
    def format_h4(cls, text: str) -> str:
        """格式化四级标题."""
        return f"[bold {cls.COLORS['h4']}]#### {text}[/]\n"

    @classmethod
    def format_h5(cls, text: str) -> str:
        """格式化五级标题."""
        return f"[bold {cls.COLORS['h5']}]##### {text}[/]\n"

    @classmethod
    def format_h6(cls, text: str) -> str:
        """格式化六级标题."""
        return f"[bold {cls.COLORS['h6']}]###### {text}[/]\n"

    @classmethod
    def format_code(cls, code: str, language: str = "") -> str:
        """格式化行内代码."""
        return f"[{cls.COLORS['code']}]{code}[/]"

    @classmethod
    def format_code_block(cls, code: str, language: str = "") -> str:
        """格式化代码块."""
        if PYGMENTS_AVAILABLE and language:
            try:
                lexer = get_lexer_by_name(language)
            except:
                lexer = TextLexer()
            formatter = Terminal256Formatter(style="monokai")
            highlighted = highlight(code, lexer, formatter)
            return f"\n{highlighted}\n"

        # 无高亮时的简单格式化
        lines = code.split("\n")
        formatted_lines = []
        for line in lines:
            formatted_lines.append(f"  {line}")
        return "\n".join(formatted_lines)

    @classmethod
    def format_link(cls, text: str, url: str) -> str:
        """格式化链接."""
        return f"[{cls.COLORS['link']}]{text}[/{cls.COLORS['link']}]"

    @classmethod
    def format_bold(cls, text: str) -> str:
        """格式化粗体."""
        return f"[bold {cls.COLORS['strong']}]{text}[/]"

    @classmethod
    def format_italic(cls, text: str) -> str:
        """格式化斜体."""
        return f"[italic]{text}[/]"

    @classmethod
    def format_strikethrough(cls, text: str) -> str:
        """格式化删除线."""
        return f"[strike {cls.COLORS['strikethrough']}]{text}[/]"

    @classmethod
    def format_blockquote(cls, text: str) -> str:
        """格式化引用块."""
        lines = text.split("\n")
        formatted = []
        for line in lines:
            formatted.append(f"[{cls.COLORS['blockquote']}]│ {line}[/]")
        return "\n".join(formatted)

    @classmethod
    def format_list_item(cls, text: str, ordered: bool = False, index: int = 1) -> str:
        """格式化列表项."""
        marker = f"{index}." if ordered else "•"
        return f"[{cls.COLORS['list_marker']}]{marker}[/] {text}"

    @classmethod
    def format_task_item(cls, text: str, checked: bool) -> str:
        """格式化任务列表项."""
        checkbox = "[✓]" if checked else "[ ]"
        color = cls.COLORS["task_checked"] if checked else cls.COLORS["task_unchecked"]
        return f"[{color}]{checkbox}[/] {text}"

    @classmethod
    def format_hr(cls) -> str:
        """格式化水平线."""
        return f"[{cls.COLORS['hr']}]" + "─" * 50 + "[/]\n"

    @classmethod
    def format_table(cls, header: list, rows: list, alignments: list = None) -> str:
        """格式化表格."""
        if not header:
            return ""

        # 计算每列宽度
        col_widths = [len(h) for h in header]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(cell))

        # 限制最大宽度
        col_widths = [min(w, 30) for w in col_widths]

        result = []

        # 表头
        header_line = "│"
        for i, h in enumerate(header):
            width = col_widths[i]
            header_line += f" [{cls.COLORS['table_header']}]{h:<{width}}[/] │"
        result.append(header_line)

        # 分隔线
        sep_line = "├" + "┼".join("─" * (w + 2) for w in col_widths) + "┤"
        result.append(f"[{cls.COLORS['table_border']}]{sep_line}[/]")

        # 数据行
        for row in rows:
            row_line = "│"
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    width = col_widths[i]
                    row_line += f" {cell:<{width}} │"
            result.append(row_line)

        return "\n".join(result)


# ============================================================================
# Mistune Markdown 渲染器
# ============================================================================

class HandsomeAgentRenderer:
    """Handsome Agent 自定义 Mistune 渲染器.

    将 Markdown 转换为 Rich 格式文本。
    """

    def __init__(self):
        self._links: dict = {}
        self._images: dict = {}

    def reset(self):
        """重置渲染器状态."""
        self._links.clear()
        self._images.clear()

    def heading(self, text: str, level: int, raw: str = None) -> str:
        """渲染标题."""
        formatters = {
            1: RichFormatter.format_h1,
            2: RichFormatter.format_h2,
            3: RichFormatter.format_h3,
            4: RichFormatter.format_h4,
            5: RichFormatter.format_h5,
            6: RichFormatter.format_h6,
        }
        formatter = formatters.get(level, RichFormatter.format_h1)
        # 移除 Rich 标记中的换行符
        clean_text = text.strip()
        return formatter(clean_text) + "\n"

    def paragraph(self, text: str) -> str:
        """渲染段落."""
        return f"{text}\n\n"

    def text(self, text: str) -> str:
        """渲染纯文本（处理内联样式）。"""
        return text

    def strong(self, text: str) -> str:
        """渲染粗体."""
        return RichFormatter.format_bold(text)

    def emphasis(self, text: str) -> str:
        """渲染斜体."""
        return RichFormatter.format_italic(text)

    def strikethrough(self, text: str) -> str:
        """渲染删除线."""
        return RichFormatter.format_strikethrough(text)

    def codespan(self, code: str) -> str:
        """渲染行内代码."""
        return RichFormatter.format_code(code)

    def code(self, code: str, language: str = None, attrs: dict = None) -> str:
        """渲染代码块."""
        lang = language or ""
        return RichFormatter.format_code_block(code, lang)

    def block_code(self, code: str, language: str = None, attrs: dict = None) -> str:
        """渲染块级代码."""
        lang = language or ""
        return RichFormatter.format_code_block(code, lang)

    def link(self, text: str, url: str, title: str = None) -> str:
        """渲染链接."""
        if title:
            return f'{RichFormatter.format_link(text, url)} "{title}"'
        return RichFormatter.format_link(text, url)

    def image(self, src: str, title: str = None, alt: str = None) -> str:
        """渲染图片（终端中显示为占位符）。"""
        alt_text = alt or "image"
        title_text = f' "{title}"' if title else ""
        return f"[{RichFormatter.COLORS['link']}]{alt_text}[/{RichFormatter.COLORS['link']}]{title_text}"

    def blockquote(self, text: str) -> str:
        """渲染引用块."""
        return RichFormatter.format_blockquote(text) + "\n"

    def list(self, text: str, ordered: bool, start: int = None) -> str:
        """渲染列表."""
        return text

    def list_item(self, text: str, ordered: bool, index: int) -> str:
        """渲染列表项."""
        return RichFormatter.format_list_item(text.strip(), ordered, index) + "\n"

    def task_list_item(self, text: str, checked: bool) -> str:
        """渲染任务列表项."""
        return RichFormatter.format_task_item(text.strip(), checked) + "\n"

    def thematic_break(self, attrs: dict = None) -> str:
        """渲染水平线."""
        return RichFormatter.format_hr()

    def table(self, text: str, header: str, body: str, columns: list = None, alignments: list = None) -> str:
        """渲染表格."""
        # 解析表头行
        header_cells = self._parse_table_row(header)
        # 解析数据行
        body_rows = []
        for line in body.split("\n"):
            if line.strip():
                body_rows.append(self._parse_table_row(line))

        return RichFormatter.format_table(header_cells, body_rows, alignments) + "\n\n"

    def _parse_table_row(self, row: str) -> list:
        """解析表格行."""
        # 移除首尾的 | 字符并分割
        row = row.strip("| \n")
        cells = [cell.strip() for cell in row.split("|")]
        return [c for c in cells if c]

    def html(self, html: str) -> str:
        """渲染 HTML（直接输出）。"""
        return html

    def inline_html(self, html: str) -> str:
        """渲染行内 HTML."""
        return html


# 仅在 mistune 可用时定义 Markdown 解析器
if MISTUNE_AVAILABLE:
    class HandsomeAgentMarkdown(mistune.Markdown):
        """Handsome Agent 自定义 Markdown 解析器."""

        def __init__(self, renderer=None, **kwargs):
            if renderer is None:
                renderer = HandsomeAgentRenderer()
            super().__init__(renderer=renderer, **kwargs)
else:
    # 降级：提供一个空的占位类
    class HandsomeAgentMarkdown:
        """降级：mistune 不可用时的占位类."""
        def __init__(self, **kwargs):
            pass
        
        def __call__(self, text):
            return text


# ============================================================================
# Markdown 渲染器类
# ============================================================================

class MarkdownRenderer:
    """Markdown 渲染器.

    提供统一的 Markdown 渲染接口。
    """

    def __init__(self, enable_code_highlight: bool = True):
        """初始化 Markdown 渲染器.

        Args:
            enable_code_highlight: 是否启用代码语法高亮
        """
        self._enable_code_highlight = enable_code_highlight
        self._markdown: Optional[HandsomeAgentMarkdown] = None

        if MISTUNE_AVAILABLE:
            self._init_markdown()

    def _init_markdown(self) -> None:
        """初始化 Markdown 解析器."""
        self._markdown = HandsomeAgentMarkdown(
            renderer=HandsomeAgentRenderer(),
            inline_rules=[],  # 使用默认规则
            block_rules=[],   # 使用默认规则
        )

    def is_available(self) -> bool:
        """检查 Markdown 渲染是否可用."""
        return MISTUNE_AVAILABLE

    def get_install_hint(self) -> str:
        """获取安装提示."""
        return (
            "要启用 Markdown 渲染，请安装 mistune:\n"
            "  pip install mistune\n"
            "要启用代码高亮，请同时安装 pygments:\n"
            "  pip install pygments"
        )

    def render(self, text: str) -> str:
        """将 Markdown 文本渲染为 Rich 格式.

        Args:
            text: Markdown 格式的文本

        Returns:
            Rich 格式的文本（可被 Rich 库解析）
        """
        if not text:
            return ""

        if not MISTUNE_AVAILABLE:
            # 返回原始文本
            return text

        # 预处理 Markdown 文本
        text = self._preprocess(text)

        try:
            # 渲染 Markdown
            rendered = self._markdown(text)

            # 后处理渲染结果
            rendered = self._postprocess(rendered)

            return rendered
        except Exception:
            # 出错时返回原始文本
            return text

    def _preprocess(self, text: str) -> str:
        """预处理 Markdown 文本."""
        # 保留代码块内容（不进行其他转换）
        # 这是简化的处理，实际可能需要更复杂的逻辑

        # 规范化换行符
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        return text

    def _postprocess(self, text: str) -> str:
        """后处理渲染结果."""
        # 清理多余的空行
        text = re.sub(r"\n{3,}", "\n\n", text)

        # 清理行尾空格
        text = re.sub(r" +\n", "\n", text)

        return text

    def render_inline(self, text: str) -> str:
        """渲染行内 Markdown（无块级元素）。

        Args:
            text: 行内 Markdown 文本

        Returns:
            渲染后的文本
        """
        if not text:
            return ""

        if not MISTUNE_AVAILABLE:
            return text

        try:
            # 只处理行内元素的简化逻辑
            # 移除代码块和引用块等块级元素标记
            lines = text.split("\n")
            rendered_lines = []

            for line in lines:
                # 移除标题标记
                line = re.sub(r"^#{1,6}\s+", "", line)
                # 移除引用标记
                line = re.sub(r"^>\s*", "", line)
                # 移除列表标记
                line = re.sub(r"^[\*\-\+]\s+", "• ", line)
                line = re.sub(r"^\d+\.\s+", lambda m: f"{m.group().strip()} ", line)
                rendered_lines.append(line)

            return "\n".join(rendered_lines)
        except Exception:
            return text


# ============================================================================
# 便捷函数
# ============================================================================

def markdown_to_rich(text: str, enable_highlight: bool = True) -> str:
    """将 Markdown 转换为 Rich 格式文本.

    这是一个便捷函数。

    Args:
        text: Markdown 格式的文本
        enable_highlight: 是否启用代码高亮

    Returns:
        Rich 格式的文本
    """
    renderer = MarkdownRenderer(enable_code_highlight=enable_highlight)
    return renderer.render(text)


def is_markdown_available() -> bool:
    """检查 Markdown 渲染是否可用."""
    return MISTUNE_AVAILABLE


def get_markdown_features() -> dict:
    """获取 Markdown 功能特性.

    Returns:
        功能特性字典
    """
    return {
        "mistune": MISTUNE_AVAILABLE,
        "pygments": PYGMENTS_AVAILABLE,
        "code_highlight": MISTUNE_AVAILABLE and PYGMENTS_AVAILABLE,
    }


# ============================================================================
# 模块导出
# ============================================================================

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
