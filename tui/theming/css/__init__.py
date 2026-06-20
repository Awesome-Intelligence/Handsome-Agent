"""CSS 样式模块化架构

🚪 Access - 💬 CLI - Theming - CSS 样式系统

这个模块提供了 TUI 应用的样式系统，包括：
- base.css: 基础变量和设计令牌
- layout.css: 布局规则
- components.css: 组件样式
- animations.css: 动画定义
"""

from pathlib import Path
from typing import List


def get_stylesheets() -> List[str]:
    """
    获取所有样式表文件路径

    Returns:
        样式表文件路径列表，按加载顺序排列
    """
    css_dir = Path(__file__).parent
    return [
        str(css_dir / "base.css"),
        str(css_dir / "layout.css"),
        str(css_dir / "components.css"),
        str(css_dir / "animations.css"),
    ]


def get_theme_css(theme_id: str) -> str:
    """
    获取主题 CSS 文件内容

    Args:
        theme_id: 主题 ID (default, awesome)

    Returns:
        主题 CSS 文件内容，如果不存在则返回空字符串
    """
    theme_path = Path(__file__).parent / "themes" / f"{theme_id}.css"
    if theme_path.exists():
        return theme_path.read_text(encoding="utf-8")
    return ""


__all__ = [
    "get_stylesheets",
    "get_theme_css",
]
