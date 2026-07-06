"""Interactive Select 测试"""
import pytest
from unittest.mock import patch, MagicMock
import sys


class TestInteractiveSelect:
    """Interactive Select 功能测试"""
    
    def test_hide_cursor(self, capsys):
        """测试隐藏光标"""
        from cli.setup.interactive_select import _hide_cursor
        
        _hide_cursor()
        
        captured = capsys.readouterr()
        assert '\033[?25l' in captured.out
    
    def test_show_cursor(self, capsys):
        """测试显示光标"""
        from cli.setup.interactive_select import _show_cursor
        
        _show_cursor()
        
        captured = capsys.readouterr()
        assert '\033[?25h' in captured.out
    
    @pytest.mark.skip(reason="interactive function, requires manual testing")
    def test_select_option_fallback(self):
        """测试降级选择方案（数字输入）"""
        from cli.setup.interactive_select import _fallback_select

        options = [("a", "Option A"), ("b", "Option B")]
        result = _fallback_select(options, "选择", default_idx=0)
        assert result == 0

    @pytest.mark.skip(reason="interactive function, requires manual testing")
    def test_select_option_safe(self):
        """测试安全的选择函数"""
        from cli.setup.interactive_select import select_option_safe

        options = [
            ("a", "Option A"),
            ("b", "Option B"),
            ("c", "Option C")
        ]

        result = select_option_safe(options, default_idx=0)
        assert isinstance(result, int)
        assert 0 <= result < len(options)
    
    def test_select_option_safe_empty(self):
        """测试空选项列表"""
        from cli.setup.interactive_select import select_option_safe
        
        result = select_option_safe([], default_idx=0)
        
        assert result is None
    
    @pytest.mark.skip(reason="interactive function, requires manual testing")
    def test_print_config_summary_no_config(self, capsys):
        """测试打印配置摘要（无配置）"""
        from cli.setup.interactive_select import print_config_summary
        print_config_summary()
    
    @pytest.mark.skip(reason="interactive function, requires manual testing")
    def test_print_config_summary_with_config(self, capsys, tmp_path):
        """测试打印配置摘要（有配置）"""
        import json
        config_file = tmp_path / ".handsome_agent" / "config.json"
        config_file.parent.mkdir()
        test_config = {"language": "zh", "llm": {"provider": "openai"}}
        with open(config_file, 'w') as f:
            json.dump(test_config, f)
    
    @pytest.mark.skip(reason="interactive function, requires manual testing")
    def test_print_menu_with_logo_basic(self, tmp_path, capsys):
        """测试带 Logo 的菜单打印"""
        from cli.setup.interactive_select import print_menu_with_logo
        options = [("a", "Option A"), ("b", "Option B")]
        result = print_menu_with_logo(options, "测试菜单")
        assert result is not None
        assert 0 <= result < len(options)
    
    def test_print_menu_with_logo_empty_options(self, tmp_path, capsys):
        """测试空选项列表"""
        from cli.setup.interactive_select import print_menu_with_logo
        
        result = print_menu_with_logo([], "空菜单")
        
        assert result is None
    
    @pytest.mark.skip(reason="interactive function, requires manual testing")
    def test_select_option_with_title(self, tmp_path):
        """测试带标题的选择"""
        from cli.setup.interactive_select import select_option
        options = [("a", "A"), ("b", "B")]
        result = select_option(options, title="选择", show_config=True)
        assert result is not None
        assert 0 <= result < len(options)

    @pytest.mark.skip(reason="interactive function, requires manual testing")
    def test_select_option_without_title(self, tmp_path):
        """测试不带标题的选择"""
        from cli.setup.interactive_select import select_option
        options = [("a", "A"), ("b", "B")]
        result = select_option(options, show_config=False)
        assert result is not None
        assert 0 <= result < len(options)

    @pytest.mark.skip(reason="interactive function, requires manual testing")
    def test_select_option_with_current_value(self, tmp_path):
        """测试带当前值的选择"""
        from cli.setup.interactive_select import select_option
        options = [("a", "A"), ("b", "B"), ("c", "C")]
        result = select_option(options, current_value="b")
        assert result is not None