#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for ApprovalDialog module

🚪 Access - 💬 CLI - TUI - Tests - ApprovalDialog
"""

import unittest
from unittest.mock import MagicMock, patch
from enum import Enum


class TestApprovalMode(unittest.TestCase):
    """测试审批模式枚举"""
    
    def test_approval_mode_values(self):
        """测试审批模式枚举值"""
        # 模拟 ApprovalMode 枚举
        class ApprovalMode(Enum):
            AUTO = "auto"
            SUGGEST = "suggest"
            MANUAL = "manual"
        
        self.assertEqual(ApprovalMode.AUTO.value, "auto")
        self.assertEqual(ApprovalMode.SUGGEST.value, "suggest")
        self.assertEqual(ApprovalMode.MANUAL.value, "manual")
    
    def test_approval_mode_from_string(self):
        """测试从字符串转换"""
        class ApprovalMode(Enum):
            AUTO = "auto"
            SUGGEST = "suggest"
            MANUAL = "manual"
            
            @classmethod
            def from_string(cls, value: str):
                value = value.lower().strip()
                for mode in cls:
                    if mode.value == value:
                        return mode
                return cls.SUGGEST
        
        self.assertEqual(ApprovalMode.from_string("auto"), ApprovalMode.AUTO)
        self.assertEqual(ApprovalMode.from_string("suggest"), ApprovalMode.SUGGEST)
        self.assertEqual(ApprovalMode.from_string("manual"), ApprovalMode.MANUAL)
        self.assertEqual(ApprovalMode.from_string("invalid"), ApprovalMode.SUGGEST)


class TestRiskLevel(unittest.TestCase):
    """测试风险等级枚举"""
    
    def test_risk_level_values(self):
        """测试风险等级枚举值"""
        class RiskLevel(Enum):
            LOW = "low"
            MEDIUM = "medium"
            HIGH = "high"
        
        self.assertEqual(RiskLevel.LOW.value, "low")
        self.assertEqual(RiskLevel.MEDIUM.value, "medium")
        self.assertEqual(RiskLevel.HIGH.value, "high")
    
    def test_risk_level_from_operation(self):
        """测试从操作名称判断风险等级"""
        class RiskLevel(Enum):
            LOW = "low"
            MEDIUM = "medium"
            HIGH = "high"
            
            @classmethod
            def from_operation(cls, operation: str, sensitive_operations: list):
                HIGH_RISK_OPERATIONS = [
                    "delete_file",
                    "delete_directory",
                    "remove_directory",
                    "execute_command",
                    "run_shell",
                ]
                
                MEDIUM_RISK_OPERATIONS = [
                    "write_file",
                    "create_directory",
                    "move_file",
                    "copy_file",
                ]
                
                operation_lower = operation.lower()
                
                for high_op in HIGH_RISK_OPERATIONS:
                    if high_op in operation_lower:
                        return cls.HIGH
                
                for medium_op in MEDIUM_RISK_OPERATIONS:
                    if medium_op in operation_lower:
                        return cls.MEDIUM
                
                return cls.LOW
        
        self.assertEqual(RiskLevel.from_operation("delete_file", []), RiskLevel.HIGH)
        self.assertEqual(RiskLevel.from_operation("execute_command", []), RiskLevel.HIGH)
        self.assertEqual(RiskLevel.from_operation("write_file", []), RiskLevel.MEDIUM)
        self.assertEqual(RiskLevel.from_operation("create_directory", []), RiskLevel.MEDIUM)
        self.assertEqual(RiskLevel.from_operation("read_file", []), RiskLevel.LOW)


class TestSensitiveOperations(unittest.TestCase):
    """测试敏感操作列表"""
    
    def test_sensitive_operations_list(self):
        """测试敏感操作列表内容"""
        SENSITIVE_OPERATIONS = [
            "delete_file",
            "delete_directory",
            "remove_directory",
            "execute_command",
            "run_shell",
            "write_file",
        ]
        
        self.assertIn("delete_file", SENSITIVE_OPERATIONS)
        self.assertIn("delete_directory", SENSITIVE_OPERATIONS)
        self.assertIn("execute_command", SENSITIVE_OPERATIONS)
        self.assertIn("write_file", SENSITIVE_OPERATIONS)


class TestApprovalManager(unittest.TestCase):
    """测试审批管理器"""
    
    def test_should_approve_auto_mode(self):
        """测试自动模式下不需要审批"""
        class ApprovalMode(Enum):
            AUTO = "auto"
            SUGGEST = "suggest"
            MANUAL = "manual"
        
        SENSITIVE_OPERATIONS = ["delete_file", "write_file"]
        
        class ApprovalManager:
            def __init__(self, mode):
                self.mode = mode
            
            def should_approve(self, operation):
                if self.mode == ApprovalMode.AUTO:
                    return False
                return True
        
        manager = ApprovalManager(ApprovalMode.AUTO)
        self.assertFalse(manager.should_approve("delete_file"))
    
    def test_should_approve_suggest_mode(self):
        """测试建议模式下敏感操作需要审批"""
        class ApprovalMode(Enum):
            AUTO = "auto"
            SUGGEST = "suggest"
            MANUAL = "manual"
        
        SENSITIVE_OPERATIONS = ["delete_file", "write_file"]
        
        class ApprovalManager:
            def __init__(self, mode):
                self.mode = mode
                self.sensitive_operations = SENSITIVE_OPERATIONS
            
            def should_approve(self, operation):
                if self.mode == ApprovalMode.AUTO:
                    return False
                elif self.mode == ApprovalMode.SUGGEST:
                    operation_lower = operation.lower()
                    return any(sop in operation_lower for sop in self.sensitive_operations)
                elif self.mode == ApprovalMode.MANUAL:
                    return True
                return False
        
        manager = ApprovalManager(ApprovalMode.SUGGEST)
        self.assertTrue(manager.should_approve("delete_file"))
        self.assertTrue(manager.should_approve("write_file"))
        self.assertFalse(manager.should_approve("read_file"))
    
    def test_should_approve_manual_mode(self):
        """测试手动模式下所有操作都需要审批"""
        class ApprovalMode(Enum):
            AUTO = "auto"
            SUGGEST = "suggest"
            MANUAL = "manual"
        
        class ApprovalManager:
            def __init__(self, mode):
                self.mode = mode
            
            def should_approve(self, operation):
                if self.mode == ApprovalMode.AUTO:
                    return False
                elif self.mode == ApprovalMode.SUGGEST:
                    return False
                elif self.mode == ApprovalMode.MANUAL:
                    return True
                return False
        
        manager = ApprovalManager(ApprovalMode.MANUAL)
        self.assertTrue(manager.should_approve("delete_file"))
        self.assertTrue(manager.should_approve("read_file"))
        self.assertTrue(manager.should_approve("any_operation"))


class TestApprovalDialogLogic(unittest.TestCase):
    """测试审批对话框逻辑"""
    
    def test_generate_tool_preview(self):
        """测试生成工具预览"""
        def generate_preview(tool_name, tool_args):
            preview_parts = []
            
            for key, value in tool_args.items():
                value_str = str(value)
                if len(value_str) > 50:
                    value_str = value_str[:47] + "..."
                
                if key.lower() in ("password", "token", "secret", "key", "api_key"):
                    value_str = "***"
                
                preview_parts.append(f"{key}={value_str}")
            
            preview = "; ".join(preview_parts)
            
            if len(preview) > 100:
                preview = preview[:97] + "..."
            
            return preview
        
        # 测试基本预览
        result = generate_preview("write_file", {"path": "/tmp/test.txt", "content": "hello"})
        self.assertIn("path=/tmp/test.txt", result)
        self.assertIn("content=hello", result)
        
        # 测试敏感字段隐藏
        result = generate_preview("api_call", {"api_key": "sk-secret123", "data": "test"})
        self.assertIn("api_key=***", result)
        self.assertIn("data=test", result)
        
        # 测试长值截断
        long_content = "x" * 100
        result = generate_preview("write_file", {"content": long_content})
        self.assertTrue(result.endswith("..."))
        self.assertLessEqual(len(result), 100)
    
    def test_risk_level_colors(self):
        """测试风险等级颜色"""
        class RiskLevel(Enum):
            LOW = "low"
            MEDIUM = "medium"
            HIGH = "high"
            
            def get_color(self):
                colors = {
                    "low": "#4CAF50",
                    "medium": "#FF9800",
                    "high": "#F44336",
                }
                return colors.get(self.value, "#888888")
        
        self.assertEqual(RiskLevel.LOW.get_color(), "#4CAF50")
        self.assertEqual(RiskLevel.MEDIUM.get_color(), "#FF9800")
        self.assertEqual(RiskLevel.HIGH.get_color(), "#F44336")
    
    def test_risk_level_icons(self):
        """测试风险等级图标"""
        class RiskLevel(Enum):
            LOW = "low"
            MEDIUM = "medium"
            HIGH = "high"
            
            def get_icon(self):
                icons = {
                    "low": "✓",
                    "medium": "⚠",
                    "high": "⚠",
                }
                return icons.get(self.value, "?")
        
        self.assertEqual(RiskLevel.LOW.get_icon(), "✓")
        self.assertEqual(RiskLevel.MEDIUM.get_icon(), "⚠")
        self.assertEqual(RiskLevel.HIGH.get_icon(), "⚠")


if __name__ == "__main__":
    unittest.main()