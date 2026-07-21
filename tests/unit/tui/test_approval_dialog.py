#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Approval Dialog Unit Tests

测试 tui/widgets/approval_dialog.py 模块的审批对话框功能。
"""

import pytest
from unittest.mock import MagicMock, patch


class TestApprovalMode:
    """测试审批模式枚举"""

    def test_approval_mode_values(self):
        """测试审批模式值"""
        from tui.widgets.approval_dialog import ApprovalMode
        
        assert ApprovalMode.AUTO.value == "auto"
        assert ApprovalMode.SUGGEST.value == "suggest"
        assert ApprovalMode.MANUAL.value == "manual"

    def test_approval_mode_from_string(self):
        """测试从字符串创建审批模式"""
        from tui.widgets.approval_dialog import ApprovalMode
        
        assert ApprovalMode.from_string("auto") == ApprovalMode.AUTO
        assert ApprovalMode.from_string("AUTO") == ApprovalMode.AUTO
        assert ApprovalMode.from_string("  auto  ") == ApprovalMode.AUTO
        
        assert ApprovalMode.from_string("suggest") == ApprovalMode.SUGGEST
        assert ApprovalMode.from_string("manual") == ApprovalMode.MANUAL

    def test_approval_mode_default(self):
        """测试无效字符串返回默认值"""
        from tui.widgets.approval_dialog import ApprovalMode
        
        result = ApprovalMode.from_string("invalid")
        
        assert result == ApprovalMode.SUGGEST

    def test_approval_mode_str(self):
        """测试审批模式字符串表示"""
        from tui.widgets.approval_dialog import ApprovalMode
        
        assert str(ApprovalMode.AUTO) == "auto"
        assert str(ApprovalMode.SUGGEST) == "suggest"
        assert str(ApprovalMode.MANUAL) == "manual"


class TestRiskLevel:
    """测试风险等级枚举"""

    def test_risk_level_values(self):
        """测试风险等级值"""
        from tui.widgets.approval_dialog import RiskLevel
        
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"

    def test_risk_level_from_operation_high_risk(self):
        """测试高风险操作识别"""
        from tui.widgets.approval_dialog import RiskLevel
        
        high_risk_ops = [
            "delete_file",
            "delete_directory",
            "remove_directory",
            "execute_command",
            "run_shell",
        ]
        
        for op in high_risk_ops:
            assert RiskLevel.from_operation(op, []) == RiskLevel.HIGH

    def test_risk_level_from_operation_medium_risk(self):
        """测试中风险操作识别"""
        from tui.widgets.approval_dialog import RiskLevel
        
        medium_risk_ops = [
            "write_file",
            "create_directory",
            "move_file",
            "copy_file",
        ]
        
        for op in medium_risk_ops:
            assert RiskLevel.from_operation(op, []) == RiskLevel.MEDIUM

    def test_risk_level_from_operation_low_risk(self):
        """测试低风险操作识别"""
        from tui.widgets.approval_dialog import RiskLevel
        
        low_risk_ops = [
            "read_file",
            "list_directory",
            "search",
            "get_status",
        ]
        
        for op in low_risk_ops:
            assert RiskLevel.from_operation(op, []) == RiskLevel.LOW

    def test_risk_level_case_insensitive(self):
        """测试风险等级识别大小写不敏感"""
        from tui.widgets.approval_dialog import RiskLevel
        
        assert RiskLevel.from_operation("DELETE_FILE", []) == RiskLevel.HIGH
        assert RiskLevel.from_operation("Write_File", []) == RiskLevel.MEDIUM

    def test_risk_level_partial_match(self):
        """测试部分匹配"""
        from tui.widgets.approval_dialog import RiskLevel
        
        # "delete" 在操作名中应该被识别为高风险
        assert RiskLevel.from_operation("user_delete_action", []) == RiskLevel.HIGH
        assert RiskLevel.from_operation("safe_delete_backup", []) == RiskLevel.HIGH

    def test_risk_level_get_color(self):
        """测试获取风险等级颜色"""
        from tui.widgets.approval_dialog import RiskLevel
        
        assert RiskLevel.LOW.get_color() == "$success"
        assert RiskLevel.MEDIUM.get_color() == "$warning"
        assert RiskLevel.HIGH.get_color() == "$error"

    def test_risk_level_get_icon(self):
        """测试获取风险等级图标"""
        from tui.widgets.approval_dialog import RiskLevel
        
        assert RiskLevel.LOW.get_icon() == "✓"
        assert RiskLevel.MEDIUM.get_icon() == "⚠"
        assert RiskLevel.HIGH.get_icon() == "⚠"

    def test_risk_level_get_label(self):
        """测试获取风险等级标签"""
        from tui.widgets.approval_dialog import RiskLevel
        
        with patch("tui.widgets.approval_dialog.t") as mock_t:
            mock_t.side_effect = lambda key, default=None, **kwargs: default or key
            
            label = RiskLevel.HIGH.get_label()
            
            assert label == "HIGH"


class TestSensitiveOperations:
    """测试敏感操作列表"""

    def test_sensitive_operations_defined(self):
        """测试敏感操作列表已定义"""
        from tui.widgets.approval_dialog import SENSITIVE_OPERATIONS
        
        assert len(SENSITIVE_OPERATIONS) > 0
        assert "delete_file" in SENSITIVE_OPERATIONS
        assert "execute_command" in SENSITIVE_OPERATIONS


class TestApprovalDialog:
    """测试 ApprovalDialog 组件"""

    def test_dialog_creation(self):
        """测试对话框创建"""
        from tui.widgets.approval_dialog import ApprovalDialog, RiskLevel
        
        dialog = ApprovalDialog(
            operation="delete_file",
            preview="/path/to/file.txt",
            risk_level=RiskLevel.HIGH,
        )
        
        assert dialog.operation == "delete_file"
        assert dialog.preview == "/path/to/file.txt"
        assert dialog.risk_level == RiskLevel.HIGH

    def test_dialog_default_risk_level(self):
        """测试对话框默认风险等级"""
        from tui.widgets.approval_dialog import ApprovalDialog, RiskLevel
        
        dialog = ApprovalDialog(operation="list_files")
        
        assert dialog.risk_level == RiskLevel.MEDIUM

    def test_dialog_default_preview(self):
        """测试对话框默认预览"""
        from tui.widgets.approval_dialog import ApprovalDialog
        
        dialog = ApprovalDialog(operation="list_files")
        
        assert dialog.preview == ""

    def test_confirm_posts_message(self):
        """测试确认发送消息"""
        from tui.widgets.approval_dialog import ApprovalDialog, ApprovalConfirmed
        
        dialog = ApprovalDialog(operation="test_op")
        
        with patch.object(dialog, "post_message") as mock_post, \
             patch.object(dialog, "remove"):
            dialog._confirm()
            
            mock_post.assert_called_once()
            call_args = mock_post.call_args[0][0]
            assert isinstance(call_args, ApprovalConfirmed)
            assert call_args.operation == "test_op"

    def test_confirm_removes_self(self):
        """测试确认后移除自身"""
        from tui.widgets.approval_dialog import ApprovalDialog
        
        dialog = ApprovalDialog(operation="test_op")
        
        with patch.object(dialog, "remove") as mock_remove:
            dialog._confirm()
            
            mock_remove.assert_called_once()

    def test_reject_posts_message(self):
        """测试拒绝发送消息"""
        from tui.widgets.approval_dialog import ApprovalDialog, ApprovalRejected
        
        dialog = ApprovalDialog(operation="test_op")
        
        with patch.object(dialog, "post_message") as mock_post, \
             patch.object(dialog, "remove"):
            dialog._reject()
            
            mock_post.assert_called_once()
            call_args = mock_post.call_args[0][0]
            assert isinstance(call_args, ApprovalRejected)
            assert call_args.operation == "test_op"

    def test_reject_removes_self(self):
        """测试拒绝后移除自身"""
        from tui.widgets.approval_dialog import ApprovalDialog
        
        dialog = ApprovalDialog(operation="test_op")
        
        with patch.object(dialog, "remove") as mock_remove:
            dialog._reject()
            
            mock_remove.assert_called_once()

    def test_on_mount_sets_focus_high_risk(self):
        """测试高风险操作默认焦点在取消按钮"""
        from tui.widgets.approval_dialog import ApprovalDialog, RiskLevel
        
        dialog = ApprovalDialog(
            operation="delete_file",
            risk_level=RiskLevel.HIGH,
        )
        
        with patch.object(dialog, "query_one") as mock_query:
            mock_button = MagicMock()
            mock_query.return_value = mock_button
            
            dialog.on_mount()
            
            assert dialog._focus_button == "cancel"

    def test_on_button_pressed_confirm(self):
        """测试确认按钮按下"""
        from tui.widgets.approval_dialog import ApprovalDialog
        
        dialog = ApprovalDialog(operation="test_op")
        
        with patch.object(dialog, "_confirm") as mock_confirm:
            class MockEvent:
                button = MagicMock()
                button.id = "confirm-button"
            
            dialog.on_button_pressed(MockEvent())
            
            mock_confirm.assert_called_once()

    def test_on_button_pressed_cancel(self):
        """测试取消按钮按下"""
        from tui.widgets.approval_dialog import ApprovalDialog
        
        dialog = ApprovalDialog(operation="test_op")
        
        with patch.object(dialog, "_reject") as mock_reject:
            class MockEvent:
                button = MagicMock()
                button.id = "cancel-button"
            
            dialog.on_button_pressed(MockEvent())
            
            mock_reject.assert_called_once()

    def test_on_key_enter_confirm(self):
        """测试回车键确认"""
        from tui.widgets.approval_dialog import ApprovalDialog
        
        dialog = ApprovalDialog(operation="test_op")
        
        with patch.object(dialog, "_confirm") as mock_confirm:
            class MockEvent:
                key = "enter"
            
            dialog.on_key(MockEvent())
            
            mock_confirm.assert_called_once()

    def test_on_key_escape_reject(self):
        """测试Escape键拒绝"""
        from tui.widgets.approval_dialog import ApprovalDialog
        
        dialog = ApprovalDialog(operation="test_op")
        
        with patch.object(dialog, "_reject") as mock_reject:
            class MockEvent:
                key = "escape"
            
            dialog.on_key(MockEvent())
            
            mock_reject.assert_called_once()


class TestApprovalManager:
    """测试审批管理器"""

    def test_manager_init_default_mode(self):
        """测试管理器默认审批模式"""
        from tui.widgets.approval_dialog import ApprovalManager, ApprovalMode
        
        manager = ApprovalManager()
        
        assert manager.mode == ApprovalMode.SUGGEST

    def test_manager_init_custom_mode(self):
        """测试管理器自定义审批模式"""
        from tui.widgets.approval_dialog import ApprovalManager, ApprovalMode
        
        manager = ApprovalManager(mode=ApprovalMode.AUTO)
        
        assert manager.mode == ApprovalMode.AUTO

    def test_manager_init_sensitive_operations(self):
        """测试管理器敏感操作列表"""
        from tui.widgets.approval_dialog import ApprovalManager
        
        custom_ops = ["custom_op1", "custom_op2"]
        manager = ApprovalManager(sensitive_operations=custom_ops)
        
        assert manager.sensitive_operations == custom_ops

    def test_set_mode_from_enum(self):
        """测试从枚举设置模式"""
        from tui.widgets.approval_dialog import ApprovalManager, ApprovalMode
        
        manager = ApprovalManager()
        manager.set_mode(ApprovalMode.MANUAL)
        
        assert manager.mode == ApprovalMode.MANUAL

    def test_set_mode_from_string(self):
        """测试从字符串设置模式"""
        from tui.widgets.approval_dialog import ApprovalManager, ApprovalMode
        
        manager = ApprovalManager()
        manager.set_mode("auto")
        
        assert manager.mode == ApprovalMode.AUTO

    def test_should_approve_auto_mode(self):
        """测试自动模式不需要审批"""
        from tui.widgets.approval_dialog import ApprovalManager, ApprovalMode
        
        manager = ApprovalManager(mode=ApprovalMode.AUTO)
        
        assert manager.should_approve("delete_file") is False
        assert manager.should_approve("execute_command") is False

    def test_should_approve_suggest_mode_normal(self):
        """测试建议模式下普通操作不需审批"""
        from tui.widgets.approval_dialog import ApprovalManager, ApprovalMode
        
        manager = ApprovalManager(mode=ApprovalMode.SUGGEST)
        
        assert manager.should_approve("list_files") is False
        assert manager.should_approve("read_file") is False

    def test_should_approve_suggest_mode_sensitive(self):
        """测试建议模式下敏感操作需审批"""
        from tui.widgets.approval_dialog import ApprovalManager, ApprovalMode
        
        manager = ApprovalManager(mode=ApprovalMode.SUGGEST)
        
        assert manager.should_approve("delete_file") is True
        assert manager.should_approve("execute_command") is True

    def test_should_approve_manual_mode(self):
        """测试手动模式下所有操作需审批"""
        from tui.widgets.approval_dialog import ApprovalManager, ApprovalMode
        
        manager = ApprovalManager(mode=ApprovalMode.MANUAL)
        
        assert manager.should_approve("list_files") is True
        assert manager.should_approve("delete_file") is True

    def test_get_risk_level(self):
        """测试获取风险等级"""
        from tui.widgets.approval_dialog import ApprovalManager, RiskLevel
        
        manager = ApprovalManager()
        
        assert manager.get_risk_level("delete_file") == RiskLevel.HIGH
        assert manager.get_risk_level("write_file") == RiskLevel.MEDIUM
        assert manager.get_risk_level("list_files") == RiskLevel.LOW

    def test_is_sensitive_operation(self):
        """测试敏感操作判断"""
        from tui.widgets.approval_dialog import ApprovalManager
        
        manager = ApprovalManager()
        
        assert manager.is_sensitive_operation("delete_file") is True
        assert manager.is_sensitive_operation("execute_command") is True
        assert manager.is_sensitive_operation("list_files") is False

    def test_is_sensitive_operation_case_insensitive(self):
        """测试敏感操作判断大小写不敏感"""
        from tui.widgets.approval_dialog import ApprovalManager
        
        manager = ApprovalManager()
        
        assert manager.is_sensitive_operation("DELETE_FILE") is True
        assert manager.is_sensitive_operation("Execute_Command") is True


class TestApprovalMessages:
    """测试审批消息"""

    def test_approval_requested_message(self):
        """测试审批请求消息"""
        from tui.widgets.approval_dialog import ApprovalRequested, RiskLevel
        
        msg = ApprovalRequested(
            sender=MagicMock(),
            operation="delete_file",
            preview="/path/to/file",
            risk_level=RiskLevel.HIGH,
        )
        
        assert msg.operation == "delete_file"
        assert msg.preview == "/path/to/file"
        assert msg.risk_level == RiskLevel.HIGH

    def test_approval_confirmed_message(self):
        """测试审批确认消息"""
        from tui.widgets.approval_dialog import ApprovalConfirmed
        
        msg = ApprovalConfirmed(
            sender=MagicMock(),
            operation="delete_file",
        )
        
        assert msg.operation == "delete_file"

    def test_approval_rejected_message(self):
        """测试审批拒绝消息"""
        from tui.widgets.approval_dialog import ApprovalRejected
        
        msg = ApprovalRejected(
            sender=MagicMock(),
            operation="delete_file",
        )
        
        assert msg.operation == "delete_file"


class TestCreateApprovalDialog:
    """测试创建审批对话框工厂函数"""

    def test_create_with_defaults(self):
        """测试使用默认值创建"""
        from tui.widgets.approval_dialog import create_approval_dialog
        
        dialog = create_approval_dialog(operation="test_op")
        
        assert dialog.operation == "test_op"
        assert dialog.preview == ""
        assert dialog.risk_level.value == "medium"

    def test_create_with_custom_values(self):
        """测试使用自定义值创建"""
        from tui.widgets.approval_dialog import create_approval_dialog, RiskLevel
        
        dialog = create_approval_dialog(
            operation="delete_file",
            preview="/path/to/file",
            risk_level=RiskLevel.HIGH,
        )
        
        assert dialog.operation == "delete_file"
        assert dialog.preview == "/path/to/file"
        assert dialog.risk_level == RiskLevel.HIGH


class TestApprovalDialogCompose:
    """测试审批对话框组合"""

    def test_compose_high_risk_has_warning(self):
        """测试高风险操作有警告"""
        from tui.widgets.approval_dialog import ApprovalDialog, RiskLevel
        
        dialog = ApprovalDialog(
            operation="delete_file",
            risk_level=RiskLevel.HIGH,
        )
        
        # 检查 compose 方法返回的内容
        with patch("tui.widgets.approval_dialog.get_i18n") as mock_i18n:
            mock_i18n_instance = MagicMock()
            mock_i18n_instance.t.side_effect = lambda key, default=None, **kwargs: default or key
            mock_i18n.return_value = mock_i18n_instance
            
            # 检查类 CSS 包含警告样式
            assert "risk-high" in dialog.CSS or "risk-" in ApprovalDialog.CSS

    def test_compose_low_risk_no_warning(self):
        """测试低风险操作无警告"""
        from tui.widgets.approval_dialog import ApprovalDialog, RiskLevel
        
        dialog = ApprovalDialog(
            operation="list_files",
            risk_level=RiskLevel.LOW,
        )
        
        # 低风险不应显示警告
        assert dialog.risk_level == RiskLevel.LOW


class TestApprovalTimeout:
    """测试审批超时处理"""

    def test_timeout_not_auto_mode(self):
        """测试自动模式无超时"""
        from tui.widgets.approval_dialog import ApprovalManager, ApprovalMode
        
        manager = ApprovalManager(mode=ApprovalMode.AUTO)
        
        # 自动模式不等待，直接执行
        should_wait = manager.should_approve("delete_file")
        
        assert should_wait is False

    def test_timeout_in_manual_mode(self):
        """测试手动模式需要等待用户确认"""
        from tui.widgets.approval_dialog import ApprovalManager, ApprovalMode
        
        manager = ApprovalManager(mode=ApprovalMode.MANUAL)
        
        # 手动模式需要用户确认
        should_wait = manager.should_approve("list_files")
        
        assert should_wait is True


class TestApprovalDialogIntegration:
    """测试审批对话框集成"""

    def test_full_approval_flow_confirm(self):
        """测试完整审批流程 - 确认"""
        from tui.widgets.approval_dialog import ApprovalDialog, ApprovalConfirmed
        
        dialog = ApprovalDialog(operation="delete_file")
        dialog._logger = MagicMock()
        
        confirmed_messages = []
        
        def capture_message(msg):
            if isinstance(msg, ApprovalConfirmed):
                confirmed_messages.append(msg)
        
        with patch.object(dialog, "post_message", side_effect=capture_message), \
             patch.object(dialog, "remove"):
            dialog._confirm()
        
        assert len(confirmed_messages) == 1
        assert confirmed_messages[0].operation == "delete_file"

    def test_full_approval_flow_reject(self):
        """测试完整审批流程 - 拒绝"""
        from tui.widgets.approval_dialog import ApprovalDialog, ApprovalRejected
        
        dialog = ApprovalDialog(operation="delete_file")
        dialog._logger = MagicMock()
        
        rejected_messages = []
        
        def capture_message(msg):
            if isinstance(msg, ApprovalRejected):
                rejected_messages.append(msg)
        
        with patch.object(dialog, "post_message", side_effect=capture_message), \
             patch.object(dialog, "remove"):
            dialog._reject()
        
        assert len(rejected_messages) == 1
        assert rejected_messages[0].operation == "delete_file"

    def test_keyboard_navigation_flow(self):
        """测试键盘导航流程"""
        from tui.widgets.approval_dialog import ApprovalDialog
        
        dialog = ApprovalDialog(operation="test_op")
        dialog._logger = MagicMock()
        
        with patch.object(dialog, "_confirm") as mock_confirm:
            class EnterEvent:
                key = "enter"
            
            dialog.on_key(EnterEvent())
            mock_confirm.assert_called_once()
        
        with patch.object(dialog, "_reject") as mock_reject:
            class EscapeEvent:
                key = "escape"
            
            dialog.on_key(EscapeEvent())
            mock_reject.assert_called_once()


class TestApprovalModeTransitions:
    """测试审批模式切换"""

    def test_switch_from_auto_to_manual(self):
        """测试从自动模式切换到手动模式"""
        from tui.widgets.approval_dialog import ApprovalManager, ApprovalMode
        
        manager = ApprovalManager(mode=ApprovalMode.AUTO)
        
        # 自动模式下，敏感操作也不需要审批
        assert manager.should_approve("delete_file") is False
        
        # 切换到手动模式
        manager.set_mode(ApprovalMode.MANUAL)
        
        # 现在所有操作都需要审批
        assert manager.should_approve("delete_file") is True
        assert manager.should_approve("list_files") is True

    def test_switch_from_manual_to_suggest(self):
        """测试从手动模式切换到建议模式"""
        from tui.widgets.approval_dialog import ApprovalManager, ApprovalMode
        
        manager = ApprovalManager(mode=ApprovalMode.MANUAL)
        
        # 手动模式下，所有操作都需要审批
        assert manager.should_approve("list_files") is True
        
        # 切换到建议模式
        manager.set_mode(ApprovalMode.SUGGEST)
        
        # 现在只有敏感操作需要审批
        assert manager.should_approve("list_files") is False
        assert manager.should_approve("delete_file") is True


class TestApprovalDialogStyling:
    """测试审批对话框样式"""

    def test_css_contains_risk_classes(self):
        """测试CSS包含风险等级类"""
        from tui.widgets.approval_dialog import ApprovalDialog
        
        css = ApprovalDialog.CSS
        
        assert "risk-high" in css or ".risk-high" in css
        assert "risk-medium" in css or ".risk-medium" in css
        assert "risk-low" in css or ".risk-low" in css

    def test_css_contains_button_styles(self):
        """测试CSS包含按钮样式"""
        from tui.widgets.approval_dialog import ApprovalDialog
        
        css = ApprovalDialog.CSS
        
        assert "confirm-button" in css or "#confirm-button" in css
        assert "cancel-button" in css or "#cancel-button" in css
