"""测试 Textual 主题切换"""
from textual.app import App, ComposeResult
from textual.widgets import Static, Header, Footer
from textual.theme import Theme


class ThemeTestApp(App):
    """简单的测试应用"""
    
    # 定义自定义主题
    themes = [
        Theme("default", primary="#B180D7", dark=True),  # 紫色
        Theme("awesome", primary="#A9FC6E", dark=True),   # 绿色
    ]
    
    CSS = """
    Screen {
        background: $background;
    }
    #test-widget {
        height: auto;
        padding: 2;
        border: solid $primary;
        color: $foreground;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("主题切换测试 - 按 't' 切换主题", id="test-widget")
        yield Footer()
    
    def on_mount(self) -> None:
        # 注册自定义主题
        for theme in self.themes:
            self.register_theme(theme)
        print(f"[DEBUG] available_themes: {list(self.available_themes.keys())}")
        print(f"[DEBUG] current theme: {self.theme}")
    
    def key_t(self) -> None:
        """切换主题"""
        theme_ids = [t.name for t in self.themes]
        current = self.theme
        
        print(f"[DEBUG] key_t pressed, current: {current}")
        print(f"[DEBUG] theme_ids: {theme_ids}")
        
        if current not in theme_ids:
            # 如果当前不是我们的主题，切换到第一个
            next_theme = theme_ids[0]
        else:
            idx = theme_ids.index(current)
            next_theme = theme_ids[(idx + 1) % len(theme_ids)]
        
        print(f"[DEBUG] switching to: {next_theme}")
        self.theme = next_theme
        print(f"[DEBUG] after switch: {self.theme}")


if __name__ == "__main__":
    app = ThemeTestApp()
    app.run()
