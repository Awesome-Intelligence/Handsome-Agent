"""
技能详情弹窗 - 显示技能或 Bundle 的完整信息
"""

from __future__ import annotations

from typing import Optional

try:
    from textual.app import ComposeResult
    from textual.screen import ModalScreen
    from textual.binding import Binding
    from textual.containers import Vertical, Horizontal, Container
    from textual.widgets import Static, Button
    from textual.widgets import TextArea
    from textual.events import Click
    from textual import on
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    ModalScreen = object

from common.logging_manager import get_access_logger


# ============================================================================
# CSS 样式
# ============================================================================

SKILL_DETAIL_CSS = """
SkillDetailScreen {
    align: center middle;
    background: $primary 30%;
}

#detail-container {
    width: 90%;
    height: auto;
    max-height: 85%;
    background: $surface 85%;
    padding: 0;
}

#detail-header {
    height: auto;
    padding: 0 1;
    background: $primary 20%;
    border-bottom: solid $primary;
}

#detail-name {
    width: 100%;
    padding: 0;
}

#detail-meta {
    width: 100%;
    padding: 0;
    color: $text-muted;
}

#detail-content {
    width: 100%;
    height: 1fr;
    padding: 1;
    overflow-y: auto;
}

#detail-footer {
    width: 100%;
    height: 1;
    layout: horizontal;
    content-align: center middle;
}

.detail-footer-item {
    width: auto;
    color: $text-muted;
    padding: 0 1;
}

.detail-footer-item:hover {
    color: $accent;
    background: $surface;
}

.detail-footer-separator {
    width: auto;
    color: $text-disabled;
}

#detail-description {
    width: 100%;
    padding: 0;
}

SkillDetailScreen .detail-section-title {
    color: $primary;
    padding: 0;
}

SkillDetailScreen Button {
    width: 100%;
}
"""


# ============================================================================
# SkillDetailScreen 类
# ============================================================================

class SkillDetailScreen(ModalScreen if TEXTUAL_AVAILABLE else object):
    """技能/Bundle 详情弹窗.

    Attributes:
        item_data: 技能或 Bundle 的数据字典
    """

    CSS = SKILL_DETAIL_CSS

    BINDINGS = [
        Binding("escape", "close", "关闭", show=True),
    ]

    def __init__(self, item_data: dict, **kwargs):
        """初始化技能详情弹窗.

        Args:
            item_data: 技能或 Bundle 的数据字典
            **kwargs: 传递给父类的其他参数
        """
        super().__init__(**kwargs)
        self._item_data = item_data
        self._logger = get_access_logger("SkillDetailScreen", sublayer="tui")

    def compose(self) -> ComposeResult:
        """组合详情界面布局.

        Returns:
            ComposeResult: 组件生成器
        """
        item_type = self._item_data.get("type", "skill")
        name = self._item_data.get("name", "未知")
        description = self._item_data.get("description", "无描述")
        state = self._item_data.get("state", "active")
        pinned = self._item_data.get("pinned", False)
        use_count = self._item_data.get("use_count", 0)
        category = self._item_data.get("category", "general")
        path = self._item_data.get("path", "")
        skills_count = self._item_data.get("skills_count", 0)

        # 状态图标
        state_icons = {
            "active": "🟢",
            "stale": "🟡",
            "archived": "⚪",
        }
        state_icon = state_icons.get(state, "🟢")
        pinned_mark = "📌 " if pinned else ""

        with Container(id="detail-container"):
            # 头部：名称和元信息
            with Vertical(id="detail-header"):
                if item_type == "skill":
                    yield Static(f"{pinned_mark}{state_icon} [bold]{name}[/bold]", id="detail-name")
                    meta_parts = [f"类型: 技能", f"分类: {category}"]
                    if use_count > 0:
                        meta_parts.append(f"使用次数: {use_count}")
                    if path:
                        meta_parts.append(f"路径: {path}")
                    yield Static(" | ".join(meta_parts), id="detail-meta")
                else:
                    yield Static(f"📦 [bold]{name}[/bold]", id="detail-name")
                    yield Static(f"类型: Bundle | 包含 {skills_count} 个技能", id="detail-meta")

            # 描述部分
            with Vertical(id="detail-content"):
                yield Static("[bold]描述[/bold]", classes="detail-section-title")
                yield Static(description if description else "无描述", id="detail-description")

            # 底部提示
            with Horizontal(id="detail-footer"):
                yield Static("Esc 关闭", id="detail-footer-close", classes="detail-footer-item")

    def on_mount(self) -> None:
        """组件挂载时设置焦点."""
        pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮按下时关闭弹窗."""
        if event.button.id == "btn-close":
            self.action_close()

    def action_close(self) -> None:
        """关闭弹窗."""
        self.dismiss()

    def on_click(self, event) -> None:
        """点击背景时关闭"""
        if event.widget is self:
            self.action_close()

    @on(Click, "#detail-footer-close")
    def _handle_footer_close_click(self, event: Static.Click) -> None:
        """点击 footer 关闭按钮"""
        event.stop()
        self.action_close()
