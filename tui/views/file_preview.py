#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FilePreviewScreen - 文件预览弹窗

🚪 Access - 💬 CLI - TUI Views - FilePreviewScreen

使用 Textual TextArea 组件实现文件内容预览，支持：
- 语法高亮（自动检测文件类型）
- 行号显示
- 滚动浏览
- 只读模式
- 快捷键关闭 (Esc/q)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

# Textual 组件导入
try:
    from textual.app import ComposeResult
    from textual.screen import ModalScreen
    from textual.widgets import TextArea, Static, Button
    from textual.containers import Container, Vertical, Horizontal
    from textual.binding import Binding
    from textual.events import Click
    from textual import on
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    ModalScreen = object

from common.logging_manager import get_access_logger


# ============================================================================
# 语言检测映射
# ============================================================================

LANGUAGE_MAP = {
    # Python
    ".py": "python",
    ".pyw": "python",
    ".pyi": "python",
    
    # JavaScript/TypeScript
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    
    # Web
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".less": "less",
    ".vue": "vue",
    ".svelte": "svelte",
    
    # Data formats
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".csv": "csv",
    
    # Markdown
    ".md": "markdown",
    ".markdown": "markdown",
    ".rst": "rst",
    
    # Shell
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "zsh",
    ".ps1": "powershell",
    ".psm1": "powershell",
    
    # Config
    ".ini": "ini",
    ".conf": "conf",
    ".cfg": "conf",
    ".env": "dotenv",
    
    # Programming languages
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".scala": "scala",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".lua": "lua",
    ".pl": "perl",
    ".pm": "perl",
    ".sql": "sql",
    
    # Other
    ".txt": None,
    ".log": None,
    ".gitignore": "gitignore",
    ".dockerignore": "dockerignore",
}

# 文件名特殊映射（无扩展名文件）
FILENAME_MAP = {
    "Makefile": "makefile",
    "Dockerfile": "dockerfile",
    "dockerfile": "dockerfile",
    "Jenkinsfile": "groovy",
    "Vagrantfile": "ruby",
    "Gemfile": "ruby",
    "Rakefile": "ruby",
    "Procfile": "yaml",
    ".gitignore": "gitignore",
    ".dockerignore": "dockerignore",
    ".editorconfig": "editorconfig",
    ".prettierrc": "json",
    ".eslintrc": "json",
    "requirements.txt": "pip_requirements",
    "Pipfile": "toml",
    "pyproject.toml": "toml",
    "setup.py": "python",
    "setup.cfg": "ini",
    "tox.ini": "ini",
}


def detect_language(file_path: Path) -> Optional[str]:
    """根据文件路径检测语法高亮语言.

    Args:
        file_path: 文件路径

    Returns:
        语言标识符（如 "python", "javascript"），None 表示无高亮
    """
    filename = file_path.name
    
    # 先检查文件名映射
    if filename in FILENAME_MAP:
        return FILENAME_MAP[filename]
    
    # 检查扩展名
    ext = file_path.suffix.lower()
    if ext in LANGUAGE_MAP:
        return LANGUAGE_MAP[ext]
    
    return None


def get_file_size_display(size: int) -> str:
    """格式化文件大小显示.

    Args:
        size: 文件大小（字节）

    Returns:
        格式化的大小字符串
    """
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.1f} GB"


# ============================================================================
# FilePreviewScreen CSS
# ============================================================================

FILE_PREVIEW_CSS = """
FilePreviewScreen {
    align: center middle;
    background: $primary 30%;
}

#preview-container {
    width: 90%;
    height: 85%;
    background: $surface 85%;
    padding: 0;
}

#preview-header {
    height: auto;
    padding: 0 1;
    background: $primary 20%;
    border-bottom: solid $primary;
}

#file-path {
    color: $text;
    text-style: bold;
}

#file-info {
    color: $text-muted;
    text-align: right;
}

#preview-content {
    height: 1fr;
    padding: 0;
}

#preview-footer {
    height: 1;
    layout: horizontal;
    content-align: center middle;
}

.preview-footer-item {
    width: auto;
    color: $text-muted;
    padding: 0 1;
}

.preview-footer-item:hover {
    color: $accent;
    background: $surface;
}

.preview-footer-separator {
    width: auto;
    color: $text-disabled;
}

#preview-textarea {
    height: 100%;
    width: 100%;
    background: $surface;
    border: none;
}

#hint-text {
    color: $text-muted;
    text-align: center;
}
"""


# ============================================================================
# FilePreviewScreen 类
# ============================================================================

class FilePreviewScreen(ModalScreen if TEXTUAL_AVAILABLE else object):
    """文件预览弹窗.

    使用 TextArea 组件显示文件内容，支持语法高亮和滚动浏览。

    Attributes:
        file_path: 要预览的文件路径
    """

    CSS = FILE_PREVIEW_CSS

    BINDINGS = [
        Binding("escape", "close", "关闭", show=True),
    ]

    def __init__(self, file_path: Path, **kwargs):
        """初始化文件预览.

        Args:
            file_path: 要预览的文件路径
            **kwargs: 传递给父类的其他参数
        """
        super().__init__(**kwargs)
        self.file_path = file_path
        self._logger = get_access_logger("FilePreviewScreen", sublayer="tui")
        self._file_content: str = ""
        self._file_size: int = 0
        self._line_count: int = 0
        self._language: Optional[str] = None

    def compose(self) -> ComposeResult:
        """组合预览界面布局.

        Returns:
            ComposeResult: 组件生成器
        """
        with Container(id="preview-container"):
            # 头部：文件路径和信息
            with Horizontal(id="preview-header"):
                yield Static(self._get_path_display(), id="file-path")
                yield Static(self._get_info_display(), id="file-info")
            
            # 内容：TextArea 显示文件
            with Vertical(id="preview-content"):
                yield TextArea(
                    self._file_content,
                    id="preview-textarea",
                    language=self._language,
                    read_only=True,
                    show_line_numbers=True,
                    soft_wrap=False,
                )
            
            # 底部：提示信息
            with Horizontal(id="preview-footer"):
                yield Static("Esc/q 关闭", id="preview-footer-close", classes="preview-footer-item")
                yield Static("|", classes="preview-footer-separator")
                yield Static("↑↓ 滚动", classes="preview-footer-item")
                yield Static("|", classes="preview-footer-separator")
                yield Static("Ctrl+↑↓ 快速滚动", classes="preview-footer-item")

    def _get_path_display(self) -> str:
        """获取文件路径显示文本."""
        # 显示相对路径或绝对路径
        try:
            cwd = Path.cwd()
            if self.file_path.is_relative_to(cwd):
                return f"📄 {self.file_path.relative_to(cwd)}"
        except (ValueError, TypeError):
            pass
        return f"📄 {self.file_path}"

    def _get_info_display(self) -> str:
        """获取文件信息显示文本."""
        lang_display = self._language or "纯文本"
        return f"{lang_display} | {get_file_size_display(self._file_size)} | {self._line_count} 行"

    def on_mount(self) -> None:
        """组件挂载时加载文件内容."""
        self._load_file()
        self._update_display()

    def _load_file(self) -> None:
        """加载文件内容."""
        try:
            # 检查文件大小，限制大文件
            self._file_size = self.file_path.stat().st_size
            
            # 大于 5MB 的文件只显示前 5000 行
            max_size = 5 * 1024 * 1024  # 5MB
            if self._file_size > max_size:
                self._logger.warning(f"Large file detected: {self.file_path} ({self._file_size} bytes)")
                with open(self.file_path, "r", encoding="utf-8", errors="replace") as f:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= 5000:
                            lines.append(f"\n... 文件过大，仅显示前 5000 行 ...")
                            break
                        lines.append(line)
                    self._file_content = "".join(lines)
                    self._line_count = 5000
            else:
                with open(self.file_path, "r", encoding="utf-8", errors="replace") as f:
                    self._file_content = f.read()
                    self._line_count = self._file_content.count("\n") + 1
            
            # 检测语言
            self._language = detect_language(self.file_path)
            
            self._logger.info(f"Loaded file: {self.file_path} ({self._line_count} lines, {self._language})")
            
        except FileNotFoundError:
            self._file_content = f"❌ 文件不存在: {self.file_path}"
            self._logger.error(f"File not found: {self.file_path}")
        except PermissionError:
            self._file_content = f"❌ 无权限访问: {self.file_path}"
            self._logger.error(f"Permission denied: {self.file_path}")
        except Exception as e:
            self._file_content = f"❌ 加载失败: {str(e)}"
            self._logger.error(f"Failed to load file: {self.file_path} - {e}")

    def _update_display(self) -> None:
        """更新界面显示."""
        try:
            # 更新 TextArea 内容
            textarea = self.query_one("#preview-textarea", TextArea)
            textarea.load_text(self._file_content)
            if self._language:
                textarea.language = self._language
            
            # 更新头部信息
            path_widget = self.query_one("#file-path", Static)
            path_widget.update(self._get_path_display())
            
            info_widget = self.query_one("#file-info", Static)
            info_widget.update(self._get_info_display())
            
        except Exception as e:
            self._logger.debug(f"Failed to update display: {e}")

    def action_close(self) -> None:
        """关闭预览窗口."""
        self.dismiss()
        self._logger.debug("File preview closed")

    def on_click(self, event) -> None:
        """点击背景时关闭"""
        if event.widget is self:
            self.action_close()

    @on(Click, "#preview-footer-close")
    def _handle_footer_close_click(self, event: Static.Click) -> None:
        """点击 footer 关闭按钮"""
        event.stop()
        self.action_close()


# ============================================================================
# 模块导出
# ============================================================================

__all__ = [
    "FilePreviewScreen",
    "detect_language",
    "LANGUAGE_MAP",
    "FILENAME_MAP",
]