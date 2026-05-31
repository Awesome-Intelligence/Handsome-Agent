"""Interactive Select 测试"""
import pytest
from unittest.mock import patch, MagicMock
import sys


class TestInteractiveSelect:
    """Interactive Select 功能测试"""
    
    def test_hide_cursor(self, capsys):
        """测试隐藏光标"""
        from cli.interactive_select import _hide_cursor
        
        _hide_cursor()
        
        captured = capsys.readouterr()
        assert '\033[?25l' in captured.out
    
    def test_show_cursor(self, capsys):
        """测试显示光标"""
        from cli.interactive_select import _show_cursor
        
        _show_cursor()
        
        captured = capsys.readouterr()
        assert '\033[?25h' in captured.out
    
    def test_has_inquirer_true(self):
        """测试 inquirer 可用"""
        with patch.dict('sys.modules', {'inquirer': MagicMock()}):
            from cli import interactive_select
            # 重新导入以更新 HAS_INQUIRER
            import importlib
            importlib.reload(interactive_select)
            # 如果 inquirer 可导入则 HAS_INQUIRER 应该为 True
            try:
                import inquirer
                assert interactive_select.HAS_INQUIRER == True
            except ImportError:
                pass
    
    def test_select_option_fallback(self):
        """测试降级选择方案"""
        from cli.interactive_select import _fallback_select
        
        # Mock sys.stdin
        with patch('sys.stdin') as mock_stdin:
            mock_stdin.isatty.return_value = False
            
            # 应该返回默认选项
            options = [("a", "Option A"), ("b", "Option B")]
            result = _fallback_select(options, "选择", default_idx=0)
            
            # 降级方案返回 0
            assert result == 0
    
    def test_select_option_safe(self):
        """测试安全的选择函数"""
        from cli.interactive_select import select_option_safe
        
        options = [
            ("a", "Option A"),
            ("b", "Option B"),
            ("c", "Option C")
        ]
        
        result = select_option_safe(options, default_idx=0)
        
        # 应该返回一个索引
        assert isinstance(result, int)
        assert 0 <= result < len(options)
    
    def test_select_option_safe_empty(self):
        """测试空选项列表"""
        from cli.interactive_select import select_option_safe
        
        result = select_option_safe([], default_idx=0)
        
        assert result is None
    
    def test_print_config_summary_no_config(self, capsys):
        """测试打印配置摘要（无配置）"""
        # Mock has_existing_config 返回 False
        with patch('cli.setup_wizard.has_existing_config', return_value=False):
            from cli.interactive_select import print_config_summary
            
            print_config_summary()
            
            # 不应该打印任何内容
            captured = capsys.readouterr()
            assert "📋 当前配置:" not in captured.out
    
    def test_print_config_summary_with_config(self, capsys, tmp_path):
        """测试打印配置摘要（有配置）"""
        # 创建临时配置文件
        import json
        config_file = tmp_path / ".handsome_agent" / "config.json"
        config_file.parent.mkdir()
        
        test_config = {
            "language": "zh",
            "llm": {"provider": "openai"}
        }
        with open(config_file, 'w') as f:
            json.dump(test_config, f)
        
        # Mock 配置文件路径
        with patch.dict('os.environ', {'HOME': str(tmp_path)}):
            with patch('cli.setup_wizard.has_existing_config', return_value=True):
                with patch('cli.setup_wizard.load_config', return_value=test_config):
                    from cli.interactive_select import print_config_summary
                    
                    print_config_summary()
                    
                    captured = capsys.readouterr()
                    assert "📋 当前配置:" in captured.out or "🌐 显示语言" in captured.out
    
    def test_select_with_native_empty_options(self, tmp_path):
        """测试原生选择（空选项）"""
        from cli.interactive_select import _select_with_native
        
        result = _select_with_native([], "测试")
        
        assert result is None
    
    def test_select_with_native_single_option(self, tmp_path):
        """测试原生选择（单个选项）"""
        from cli.interactive_select import _select_with_native
        
        options = [("test", "Test Option")]
        
        # Mock _get_key_native 返回 ENTER
        with patch('cli.interactive_select._get_key_native', return_value='ENTER'):
            result = _select_with_native(options, "测试")
            
            assert result == 0
    
    def test_select_with_native_keyboard_navigation(self, tmp_path):
        """测试键盘导航"""
        from cli.interactive_select import _select_with_native
        
        options = [("a", "A"), ("b", "B"), ("c", "C")]
        
        # 模拟键盘：DOWN, DOWN, ENTER
        key_presses = ['DOWN', 'DOWN', 'ENTER']
        from itertools import cycle
        
        with patch('cli.interactive_select._get_key_native', side_effect=cycle(key_presses)):
            result = _select_with_native(options, "测试")
            
            # 应该在第三个选项
            assert result == 2
    
    def test_select_with_native_quit(self, tmp_path):
        """测试退出"""
        from cli.interactive_select import _select_with_native
        
        options = [("a", "A"), ("b", "B")]
        
        with patch('cli.interactive_select._get_key_native', return_value='q'):
            result = _select_with_native(options, "测试")
            
            assert result is None
    
    def test_select_with_native_number_input(self, tmp_path):
        """测试数字输入"""
        from cli.interactive_select import _select_with_native
        
        options = [("a", "A"), ("b", "B"), ("c", "C")]
        
        with patch('cli.interactive_select._get_key_native', return_value='2'):
            result = _select_with_native(options, "测试")
            
            assert result == 1  # 索引 1 (选项 "b")
    
    def test_select_with_native_invalid_number(self, tmp_path):
        """测试无效数字输入"""
        from cli.interactive_select import _select_with_native
        
        options = [("a", "A"), ("b", "B")]
        
        call_count = [0]
        def mock_key():
            call_count[0] += 1
            if call_count[0] <= 2:
                return '5'  # 无效数字
            return 'ENTER'  # 然后确认
        
        with patch('cli.interactive_select._get_key_native', side_effect=mock_key):
            result = _select_with_native(options, "测试")
            
            # 应该忽略无效数字，继续等待输入
            assert result == 0  # 默认选择
    
    def test_select_with_native_key_up(self, tmp_path):
        """测试向上导航（循环）"""
        from cli.interactive_select import _select_with_native
        
        options = [("a", "A"), ("b", "B"), ("c", "C")]
        
        with patch('cli.interactive_select._get_key_native', return_value='UP'):
            result = _select_with_native(options, "测试")
            
            # UP 应该循环到最后一个选项
            assert result == 2
    
    def test_print_menu_with_logo_basic(self, tmp_path, capsys):
        """测试带 Logo 的菜单打印"""
        from cli.interactive_select import print_menu_with_logo
        
        options = [("a", "Option A"), ("b", "Option B")]
        
        # Mock inquirer 不可用，使用原生实现
        with patch('cli.interactive_select.HAS_INQUIRER', False):
            with patch('cli.interactive_select._get_key_native', return_value='ENTER'):
                result = print_menu_with_logo(options, "测试菜单")
                
                # 应该返回 0
                assert result == 0
    
    def test_print_menu_with_logo_empty_options(self, tmp_path, capsys):
        """测试空选项列表"""
        from cli.interactive_select import print_menu_with_logo
        
        result = print_menu_with_logo([], "空菜单")
        
        assert result is None
    
    def test_select_option_with_title(self, tmp_path):
        """测试带标题的选择"""
        from cli.interactive_select import select_option
        
        options = [("a", "A"), ("b", "B")]
        
        with patch('cli.interactive_select.HAS_INQUIRER', False):
            with patch('cli.interactive_select._get_key_native', return_value='ENTER'):
                result = select_option(options, title="选择", show_config=True)
                
                assert result == 0
    
    def test_select_option_without_title(self, tmp_path):
        """测试不带标题的选择"""
        from cli.interactive_select import select_option
        
        options = [("a", "A"), ("b", "B")]
        
        with patch('cli.interactive_select.HAS_INQUIRER', False):
            with patch('cli.interactive_select._get_key_native', return_value='ENTER'):
                result = select_option(options, show_config=False)
                
                assert result == 0
    
    def test_select_option_with_current_value(self, tmp_path):
        """测试带当前值的选择"""
        from cli.interactive_select import select_option
        
        options = [("a", "A"), ("b", "B"), ("c", "C")]
        
        with patch('cli.interactive_select.HAS_INQUIRER', False):
            with patch('cli.interactive_select._get_key_native', return_value='ENTER'):
                result = select_option(options, current_value="b")
                
                assert result == 1  # 应该在 "b" 上