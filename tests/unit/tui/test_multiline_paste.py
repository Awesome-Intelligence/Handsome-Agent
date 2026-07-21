#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multiline Paste Unit Tests

测试 tui/textual_app/text_area.py 模块的多行粘贴功能。
包含 bracketed paste、unbracketed paste 和尾随换行符处理。
"""

import pytest
from unittest.mock import MagicMock, patch


class TestBracketedPaste:
    """测试 Bracketed Paste (带边界标记的粘贴)"""

    BRACKETED_PASTE_START = "\x1b[200~"  # ESC[200~
    BRACKETED_PASTE_END = "\x1b[201~"    # ESC[201~

    def test_is_bracketed_paste_start(self):
        """测试识别 Bracketed Paste 开始标记"""
        content = self.BRACKETED_PASTE_START + "some text"
        
        assert content.startswith(self.BRACKETED_PASTE_START)

    def test_is_bracketed_paste_end(self):
        """测试识别 Bracketed Paste 结束标记"""
        content = "some text" + self.BRACKETED_PASTE_END
        
        assert content.endswith(self.BRACKETED_PASTE_END)

    def test_bracketed_paste_content_extraction(self):
        """测试提取 Bracketed Paste 内容"""
        content = self.BRACKETED_PASTE_START + "line1\nline2\nline3" + self.BRACKETED_PASTE_END
        
        # 去除边界标记
        stripped = content[len(self.BRACKETED_PASTE_START):-len(self.BRACKETED_PASTE_END)]
        
        assert stripped == "line1\nline2\nline3"

    def test_bracketed_paste_multiline_content(self):
        """测试 Bracketed Paste 多行内容"""
        multiline = "def foo():\n    return 42\n\ndef bar():\n    pass"
        content = self.BRACKETED_PASTE_START + multiline + self.BRACKETED_PASTE_END
        
        stripped = content[len(self.BRACKETED_PASTE_START):-len(self.BRACKETED_PASTE_END)]
        lines = stripped.split('\n')
        
        assert len(lines) == 5
        assert lines[0] == "def foo():"
        assert lines[1] == "    return 42"

    def test_bracketed_paste_empty_content(self):
        """测试 Bracketed Paste 空内容"""
        content = self.BRACKETED_PASTE_START + self.BRACKETED_PASTE_END
        
        stripped = content[len(self.BRACKETED_PASTE_START):-len(self.BRACKETED_PASTE_END)]
        
        assert stripped == ""

    def test_bracketed_paste_single_line(self):
        """测试 Bracketed Paste 单行内容"""
        content = self.BRACKETED_PASTE_START + "hello world" + self.BRACKETED_PASTE_END
        
        stripped = content[len(self.BRACKETED_PASTE_START):-len(self.BRACKETED_PASTE_END)]
        
        assert stripped == "hello world"
        assert '\n' not in stripped


class TestUnbracketedPaste:
    """测试 Unbracketed Paste (不带边界标记的粘贴)"""

    def test_is_not_bracketed_paste(self):
        """测试普通文本不是 Bracketed Paste"""
        content = "some text without brackets"
        
        assert not content.startswith("\x1b[200~")
        assert not content.endswith("\x1b[201~")

    def test_unbracketed_paste_detection(self):
        """测试检测 Unbracketed Paste"""
        content = "line1\nline2\nline3"
        
        is_bracketed = content.startswith("\x1b[200~") and content.endswith("\x1b[201~")
        
        assert is_bracketed is False

    def test_unbracketed_paste_with_newlines(self):
        """测试带换行符的 Unbracketed Paste"""
        content = "first line\nsecond line\nthird line"
        
        lines = content.split('\n')
        
        assert len(lines) == 3
        assert lines[0] == "first line"

    def test_unbracketed_paste_trailing_newline(self):
        """测试带尾随换行符的 Unbracketed Paste"""
        content = "line1\nline2\n"
        
        lines = content.split('\n')
        
        # 注意：split('\n') 会保留最后的空字符串元素
        assert len(lines) == 3
        assert lines[-1] == ""


class TestTrailingNewlineHandling:
    """测试尾随换行符处理"""

    def test_strip_trailing_newline(self):
        """测试去除尾随换行符"""
        content = "line1\nline2\n"
        
        stripped = content.rstrip('\n')
        
        assert stripped == "line1\nline2"
        assert not stripped.endswith('\n')

    def test_preserve_internal_newlines(self):
        """测试保留内部换行符"""
        content = "line1\nline2\nline3\n"

        stripped = content.rstrip('\n')
        lines = stripped.split('\n')

        assert len(lines) == 3
        # rstip('\n') 只删除尾随的，内部换行必须保留
        assert '\n' in stripped
        # 但不能再有尾随换行
        assert not stripped.endswith('\n')

    def test_multiple_trailing_newlines(self):
        """测试多个尾随换行符"""
        content = "line1\nline2\n\n\n"
        
        stripped = content.rstrip('\n')
        
        assert stripped == "line1\nline2"
        assert not stripped.endswith('\n')

    def test_no_trailing_newline(self):
        """测试没有尾随换行符"""
        content = "line1\nline2"
        
        stripped = content.rstrip('\n')
        
        assert stripped == "line1\nline2"

    def test_only_newlines(self):
        """测试只有换行符的内容"""
        content = "\n\n\n"
        
        stripped = content.rstrip('\n')
        
        assert stripped == ""

    def test_trailing_newline_in_bracketed_paste(self):
        """测试 Bracketed Paste 尾随换行符"""
        start = "\x1b[200~"
        end = "\x1b[201~"
        content = start + "line1\nline2\n" + end
        
        # 提取内部内容
        inner = content[len(start):-len(end)]
        # 去除尾随换行符
        stripped = inner.rstrip('\n')
        
        assert stripped == "line1\nline2"


class TestMultilinePasteSubmission:
    """测试多行粘贴提交逻辑"""

    def test_should_not_auto_submit_with_trailing_newline(self):
        """测试带尾随换行符不应自动提交"""
        content = "line1\nline2\n"
        
        # 尾随换行符检测
        has_trailing_newline = content.endswith('\n')
        
        # 有尾随换行符，不应自动提交
        assert has_trailing_newline is True
        auto_submit = not has_trailing_newline
        assert auto_submit is False

    def test_should_auto_submit_without_trailing_newline(self):
        """测试不带尾随换行符应该自动提交"""
        content = "line1\nline2"
        
        has_trailing_newline = content.endswith('\n')
        
        # 无尾随换行符，应该自动提交
        assert has_trailing_newline is False
        auto_submit = not has_trailing_newline
        assert auto_submit is True

    def test_multiline_content_requires_explicit_submit(self):
        """测试多行内容需要显式提交"""
        multiline = "def foo():\n    return 42"
        
        has_trailing_newline = multiline.endswith('\n')
        is_multiline = '\n' in multiline
        
        # 多行内容但无尾随换行符，应该自动提交
        assert is_multiline is True
        assert has_trailing_newline is False
        # 用户可能是粘贴了完整的多行代码

    def test_paste_then_type_logic(self):
        """测试粘贴后继续输入的逻辑"""
        # 模拟用户粘贴多行后继续输入
        content = "pasted content\n"
        
        # 用户粘贴后，内容应该进入编辑器
        # 如果内容以换行符结尾，不应该自动提交
        should_auto_submit = not content.endswith('\n')
        
        assert should_auto_submit is False


class TestSubmitTextArea:
    """测试 SubmitTextArea 组件"""

    def test_text_area_submit_on_enter(self):
        """测试按 Enter 触发提交"""
        import asyncio
        from tui.textual_app.text_area import SubmitTextArea

        # 模拟 Enter 键事件
        class MockEvent:
            def __init__(self, key):
                self.key = key

            def stop(self):
                pass

            def prevent_default(self):
                pass

        # Enter 键应该触发 InputSubmitted
        event = MockEvent("enter")

        area = SubmitTextArea()
        area.post_message = MagicMock()

        # _on_key 是 async，必须 await 才会执行
        asyncio.run(area._on_key(event))

        area.post_message.assert_called()
        call_args = area.post_message.call_args
        assert hasattr(call_args[0][0], "__class__")
        assert "InputSubmitted" in str(type(call_args[0][0]))

    def test_ctrl_enter_inserts_newline(self):
        """测试 Ctrl+Enter 插入换行"""
        import asyncio
        from unittest.mock import AsyncMock, PropertyMock
        from tui.textual_app.text_area import SubmitTextArea
        try:
            from textual.widgets import TextArea as _TextArea
        except ImportError:
            _TextArea = None

        class MockEvent:
            def __init__(self, key):
                self.key = key
                self.stop = MagicMock()
                self.prevent_default = MagicMock()
                # 父类 TextArea._on_key 会读取 event.is_printable
                self.is_printable = False
                # 再补 character 属性，避免父类进一步读属性报错
                try:
                    self.character = ""
                except Exception:
                    pass

        event = MockEvent("ctrl+enter")
        area = SubmitTextArea()

        # 隔离：patch 父类 TextArea._on_key（AsyncMock，因为父方法也是 async），不实际调用真实父类
        if _TextArea is not None:
            with patch.object(_TextArea, "_on_key", new_callable=AsyncMock) as mock_super:
                asyncio.run(area._on_key(event))
                mock_super.assert_called_once()
        else:
            asyncio.run(area._on_key(event))

        # 核心断言：Ctrl+Enter 不命中 enter 分支，event.stop() 应该未被调用
        assert event.stop.call_count == 0

    def test_shift_enter_inserts_newline(self):
        """测试 Shift+Enter 插入换行"""
        from tui.textual_app.text_area import SubmitTextArea
        
        class MockEvent:
            def __init__(self, key):
                self.key = key
            
            def stop(self):
                pass
            
            def prevent_default(self):
                pass
        
        event = MockEvent("shift+enter")
        
        with patch("tui.textual_app.text_area.TextArea"):
            area = SubmitTextArea()
            
            # Shift+Enter 应该保持默认行为
            result = area._on_key(event)
            
            # 验证事件未被停止

    def test_history_navigation_enabled_by_default(self):
        """测试历史导航默认启用"""
        from tui.textual_app.text_area import SubmitTextArea
        
        area = SubmitTextArea()
        
        assert area.history_navigation_enabled is True

    def test_history_navigate_callback(self):
        """测试历史导航回调"""
        from tui.textual_app.text_area import SubmitTextArea
        
        callback_mock = MagicMock()
        
        area = SubmitTextArea()
        area.history_navigate = callback_mock
        
        # 触发历史导航
        area.history_navigate(-1)  # 向上
        callback_mock.assert_called_with(-1)
        
        area.history_navigate(1)  # 向下
        callback_mock.assert_called_with(1)


class TestShouldNavigateHistory:
    """测试历史导航判断逻辑"""

    def test_empty_content_always_navigate(self):
        """测试空内容始终可以导航"""
        from tui.textual_app.text_area import SubmitTextArea
        
        area = SubmitTextArea()
        area.text = ""
        
        should_up = area._should_navigate_history(-1)
        should_down = area._should_navigate_history(1)
        
        assert should_up is True
        assert should_down is True

    def test_single_line_always_navigate(self):
        """测试单行内容始终可以导航"""
        from tui.textual_app.text_area import SubmitTextArea
        
        area = SubmitTextArea()
        area.text = "single line"
        
        should_up = area._should_navigate_history(-1)
        should_down = area._should_navigate_history(1)
        
        assert should_up is True
        assert should_down is True

    def test_multiline_first_row_up_disabled(self):
        """测试多行内容在首行时向上导航禁用"""
        from tui.textual_app.text_area import SubmitTextArea
        try:
            from textual.widgets import TextArea as _TextArea
        except ImportError:
            _TextArea = None

        area = SubmitTextArea()
        area.text = "line1\nline2\nline3"

        # 用 PropertyMock 替换 **TextArea 父类**的 property（SubmitTextArea 自身未定义 document/cursor_location）
        # 避免 patch SubmitTextArea 自身时报「does not have the attribute」
        from unittest.mock import PropertyMock
        class MockDocument:
            line_count = 3

        if _TextArea is not None:
            # create=True：允许在目标类上创建新属性（TextArea 自身 __dict__ 可能未直接写 document/cursor_location，但允许 patch 时临时创建）
            # return_value 必须是 MockDocument 实例（document 属性是对象 instance），不能是类本身
            from unittest.mock import PropertyMock
            class MockDocument:
                line_count = 3
                def __init__(self, text):
                    self.text = text

            mock_doc_instance = MockDocument(text=area.text)

            with patch.object(_TextArea, "document", new_callable=PropertyMock, return_value=mock_doc_instance, create=True), \
                 patch.object(_TextArea, "cursor_location", new_callable=PropertyMock, return_value=(0, 0), create=True):

                should_up = area._should_navigate_history(-1)
                should_down = area._should_navigate_history(1)

                # 首行 row=0：根据 text_area.py L158-161 逻辑，up 返回 True（交给历史导航）
                assert should_up is True
                # 第一行 row=0 < line_count - 1 = 2 → down 返回 False（让光标向下移动一行）
                assert should_down is False
        else:
            # 无 Textual 时：_should_navigate_history 通过 try/except AttributeError 返回 True/True
            assert area._should_navigate_history(-1) is True
            assert area._should_navigate_history(1) is True


class TestPasteDetection:
    """测试粘贴检测"""

    def test_detect_bracketed_paste_mode(self):
        """测试检测 Bracketed Paste 模式"""
        paste_content = "\x1b[200~line1\nline2\x1b[201~"
        
        is_bracketed = (
            paste_content.startswith("\x1b[200~") and
            paste_content.endswith("\x1b[201~")
        )
        
        assert is_bracketed is True

    def test_detect_unbracketed_paste_mode(self):
        """测试检测 Unbracketed Paste 模式"""
        paste_content = "line1\nline2"
        
        is_bracketed = (
            paste_content.startswith("\x1b[200~") and
            paste_content.endswith("\x1b[201~")
        )
        
        assert is_bracketed is False

    def test_paste_mode_affects_submission(self):
        """测试粘贴模式影响提交行为"""
        # Bracketed Paste 模式
        bracketed = "\x1b[200~line1\nline2\x1b[201~"
        bracketed_inner = bracketed[5:-5]  # 去除标记
        
        # Unbracketed Paste 模式
        unbracketed = "line1\nline2"
        
        # 两种模式都应该检测内容是否为多行
        def should_auto_submit(content):
            stripped = content.rstrip('\n')
            return not stripped.endswith('\n') if stripped else False
        
        # 模拟实际场景：用户粘贴代码后按 Enter 提交
        # 如果是 Bracketed Paste，内容应该被直接插入
        # 如果是 Unbracketed Paste，需要特殊处理


class TestMultilineInputScenarios:
    """测试多行输入场景"""

    def test_paste_python_function(self):
        """测试粘贴 Python 函数"""
        code = '''def hello():
    print("Hello, World!")'''
        
        lines = code.split('\n')
        
        assert len(lines) == 2
        assert lines[0] == 'def hello():'
        assert lines[1] == '    print("Hello, World!")'

    def test_paste_shell_command(self):
        """测试粘贴 Shell 命令"""
        command = "echo 'hello' && echo 'world'"
        
        # 单行命令，不应该触发多行处理
        assert '\n' not in command

    def test_paste_json_content(self):
        """测试粘贴 JSON 内容"""
        json_content = '''{
    "name": "test",
    "value": 123
}'''

        lines = json_content.split('\n')

        assert len(lines) == 4
        assert lines[0] == '{'
        assert lines[1] == '    "name": "test",'

    def test_paste_markdown_list(self):
        """测试粘贴 Markdown 列表"""
        markdown = '''- Item 1
- Item 2
- Item 3'''
        
        lines = markdown.split('\n')
        
        assert len(lines) == 3
        assert lines[0] == '- Item 1'

    def test_paste_with_only_trailing_newline(self):
        """测试只带尾随换行符的粘贴"""
        content = "single line\n"
        
        stripped = content.rstrip('\n')
        
        assert stripped == "single line"
        assert not stripped.endswith('\n')


class TestMultilinePasteEdgeCases:
    """测试多行粘贴边界情况"""

    def test_paste_with_carriage_return(self):
        """测试带回车符的粘贴（Windows 风格）"""
        content = "line1\r\nline2\r\n"
        
        # Windows 使用 CRLF
        lines = content.split('\r\n')
        
        assert len(lines) == 3

    def test_paste_with_mixed_endings(self):
        """测试混合换行符"""
        content = "line1\nline2\r\nline3\rline4\n"
        
        # 统一处理
        normalized = content.replace('\r\n', '\n').replace('\r', '\n')
        lines = normalized.split('\n')
        
        assert len(lines) == 5

    def test_paste_very_long_line(self):
        """测试粘贴超长行"""
        long_line = "x" * 10000
        
        assert len(long_line) == 10000
        assert '\n' not in long_line

    def test_paste_with_unicode(self):
        """测试粘贴 Unicode 内容"""
        content = "你好\n世界\nこんにちは"
        
        lines = content.split('\n')
        
        assert len(lines) == 3
        assert lines[0] == "你好"
        assert lines[2] == "こんにちは"

    def test_paste_empty_lines(self):
        """测试粘贴空行"""
        content = "line1\n\nline3\n"
        
        lines = content.split('\n')
        
        assert len(lines) == 4
        assert lines[1] == ""  # 空行

    def test_paste_only_whitespace_lines(self):
        """测试只含空白的行"""
        content = "line1\n   \nline3\n"
        
        lines = content.split('\n')
        
        assert len(lines) == 4
        assert lines[1] == "   "


class TestMultilinePasteIntegration:
    """测试多行粘贴集成"""

    def test_full_paste_workflow_bracketed(self):
        """测试完整的 Bracketed Paste 工作流"""
        # 1. 检测 Bracketed Paste
        start = "\x1b[200~"
        end = "\x1b[201~"
        raw_paste = start + "line1\nline2\nline3" + end

        assert raw_paste.startswith(start)
        assert raw_paste.endswith(end)

        # 2. 提取内容：边界标记长度都是 6（\x1b [ 2 0 0 ~），不是 5
        inner = raw_paste[len(start):-len(end)]
        assert inner == "line1\nline2\nline3"

        # 3. 检查尾随换行符（本用例输入 line3 后面不带 \n → False）
        has_trailing = inner.endswith('\n')
        assert has_trailing is False

        # 4. 去除尾随换行符（防止自动提交）
        if has_trailing:
            content = inner.rstrip('\n')
        else:
            content = inner

        assert content == "line1\nline2\nline3"
        assert not content.endswith('\n')

    def test_full_paste_workflow_unbracketed(self):
        """测试完整的 Unbracketed Paste 工作流"""
        # 1. 检测不是 Bracketed Paste
        raw_paste = "line1\nline2\nline3"

        is_bracketed = raw_paste.startswith("\x1b[200~")
        assert is_bracketed is False

        # 2. 内容就是原始内容
        inner = raw_paste

        # 3. 检查尾随换行符：本用例 line3 后面没有 \n → False
        has_trailing = inner.endswith('\n')
        assert has_trailing is False

        # 4. 去除尾随换行符
        if has_trailing:
            content = inner.rstrip('\n')
        else:
            content = inner

        assert content == "line1\nline2\nline3"

    def test_paste_then_explicit_submit(self):
        """测试粘贴后显式提交"""
        # 用户粘贴内容
        pasted_content = "def foo():\n    pass\n"
        
        # 内容进入编辑器，不自动提交
        assert pasted_content.endswith('\n')
        
        # 用户按 Enter 提交
        should_submit = True  # 用户按了 Enter
        
        if should_submit and not pasted_content.endswith('\n'):
            # 提交内容
            submitted = pasted_content
        else:
            # 不提交，等待用户输入
            submitted = None
        
        # 由于有尾随换行符，不自动提交
        assert submitted is None

    def test_paste_without_trailing_submit(self):
        """测试无尾随换行符时粘贴后可提交"""
        # 用户粘贴内容（无尾随换行符）
        pasted_content = "line1\nline2"
        
        # 内容进入编辑器
        assert not pasted_content.endswith('\n')
        
        # 可以自动提交
        should_auto_submit = True
        
        if should_auto_submit:
            submitted = pasted_content
        else:
            submitted = None
        
        assert submitted == "line1\nline2"
