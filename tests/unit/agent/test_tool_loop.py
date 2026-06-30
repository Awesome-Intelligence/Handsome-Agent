#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tool Loop Guardrail 单元测试

测试 ToolLoopController 的以下功能：
1. 失败计数和清除逻辑
2. 警告和 halt 阈值
3. 幂等工具无进展检测
4. 配置化支持
"""

import pytest
from agent.rails.tool_loop import (
    ToolLoopController,
    ToolLoopConfig,
    ToolCallSignature,
    ToolLoopDecision,
    IDEMPOTENT_TOOL_NAMES,
    MUTATING_TOOL_NAMES,
    _classify_tool_failure,
    append_toolguard_guidance,
)


class TestToolLoopController:
    """ToolLoopController 测试"""

    def test_init_default_config(self):
        """测试默认配置"""
        controller = ToolLoopController()
        assert controller.config.warnings_enabled is True
        assert controller.config.hard_stop_enabled is False
        assert controller.config.same_tool_failure_halt_after == 8
        assert controller.config.same_tool_failure_warn_after == 3

    def test_reset(self):
        """测试重置"""
        controller = ToolLoopController()
        controller._exact_failure_counts[ToolCallSignature("test", "hash")] = 5
        controller._same_tool_failure_counts["test_tool"] = 5

        controller.reset()

        assert len(controller._exact_failure_counts) == 0
        assert len(controller._same_tool_failure_counts) == 0
        assert controller._halt_decision is None

    def test_success_clears_failure_count(self):
        """测试成功执行清除失败计数"""
        controller = ToolLoopController()

        # 失败 2 次
        controller.after_call("terminal", {"cmd": "ls"}, {"success": False, "error": "error"}, failed=True)
        controller.after_call("terminal", {"cmd": "ls"}, {"success": False, "error": "error"}, failed=True)

        assert controller._same_tool_failure_counts.get("terminal") == 2

        # 成功 1 次
        controller.after_call("terminal", {"cmd": "ls"}, {"success": True, "output": "result"})

        # 失败计数应该被清除
        assert controller._same_tool_failure_counts.get("terminal") is None

    def test_same_tool_failure_warning(self):
        """测试同一工具失败达到警告阈值"""
        config = ToolLoopConfig(
            warnings_enabled=True,
            hard_stop_enabled=False,
            same_tool_failure_warn_after=2,
        )
        controller = ToolLoopController(config)

        # 失败 2 次，应该触发警告
        decision = controller.after_call("terminal", {"cmd": "test"}, {"success": False}, failed=True)
        decision = controller.after_call("terminal", {"cmd": "test"}, {"success": False}, failed=True)

        assert decision.is_warning
        assert decision.action == "warn"
        assert decision.code == "tool_failure_warning"
        assert decision.count == 2

    def test_same_tool_failure_halt(self):
        """测试同一工具失败达到停止阈值"""
        config = ToolLoopConfig(
            warnings_enabled=True,
            hard_stop_enabled=True,
            same_tool_failure_halt_after=3,
        )
        controller = ToolLoopController(config)

        # 失败 3 次，应该触发 halt
        controller.after_call("terminal", {"cmd": "test"}, {"success": False}, failed=True)
        controller.after_call("terminal", {"cmd": "test"}, {"success": False}, failed=True)
        decision = controller.after_call("terminal", {"cmd": "test"}, {"success": False}, failed=True)

        assert decision.should_halt
        assert decision.action == "halt"
        assert decision.code == "same_tool_failure_halt"
        assert controller.halt_decision is not None

    def test_exact_failure_counting(self):
        """测试完全相同的调用计数"""
        controller = ToolLoopController()

        sig = ToolCallSignature.from_call("terminal", {"cmd": "ls"})
        sig2 = ToolCallSignature.from_call("terminal", {"cmd": "pwd"})  # 不同参数

        # 相同调用失败 2 次
        controller.after_call("terminal", {"cmd": "ls"}, {"success": False}, failed=True)
        controller.after_call("terminal", {"cmd": "ls"}, {"success": False}, failed=True)

        assert controller._exact_failure_counts[sig] == 2
        # 不同调用不共享计数
        assert sig2 not in controller._exact_failure_counts

    def test_idempotent_tool_no_progress_detection(self):
        """测试幂等工具无进展检测"""
        config = ToolLoopConfig(
            warnings_enabled=True,
            hard_stop_enabled=False,
            no_progress_warn_after=2,
        )
        controller = ToolLoopController(config)

        # 读取文件 2 次相同结果
        result = {"content": "same content"}
        decision = controller.after_call("read_file", {"path": "/test.txt"}, result, failed=False)
        decision = controller.after_call("read_file", {"path": "/test.txt"}, result, failed=False)

        assert decision.is_warning
        assert decision.code == "idempotent_no_progress_warning"

    def test_idempotent_tool_different_result_no_warning(self):
        """测试幂等工具不同结果不触发警告"""
        config = ToolLoopConfig(
            warnings_enabled=True,
            hard_stop_enabled=False,
            no_progress_warn_after=2,
        )
        controller = ToolLoopController(config)

        # 读取文件 2 次不同结果
        decision = controller.after_call("read_file", {"path": "/test.txt"}, {"content": "content1"}, failed=False)
        decision = controller.after_call("read_file", {"path": "/test.txt"}, {"content": "content2"}, failed=False)

        assert not decision.is_warning
        assert decision.count == 1  # 重置为 1

    def test_mutating_tool_not_idempotent(self):
        """测试变更工具不追踪无进展"""
        controller = ToolLoopController()

        # write_file 是变更工具，不应该追踪无进展
        sig = ToolCallSignature.from_call("write_file", {"path": "/test.txt"})
        controller.after_call("write_file", {"path": "/test.txt"}, {"content": "same"}, failed=False)
        controller.after_call("write_file", {"path": "/test.txt"}, {"content": "same"}, failed=False)

        # 变更工具不应该记录 no_progress
        assert sig not in controller._no_progress

    def test_before_call_blocks_when_enabled(self):
        """测试 before_call 在 hard_stop_enabled 时阻止"""
        config = ToolLoopConfig(
            hard_stop_enabled=True,
            exact_failure_block_after=2,
        )
        controller = ToolLoopController(config)

        # 失败 2 次后，before_call 应该阻止
        controller.after_call("terminal", {"cmd": "test"}, {"success": False}, failed=True)
        controller.after_call("terminal", {"cmd": "test"}, {"success": False}, failed=True)

        decision = controller.before_call("terminal", {"cmd": "test"})

        assert decision.action == "block"
        assert decision.should_halt

    def test_classify_tool_failure_dict(self):
        """测试字典结果的失败分类"""
        # success=False
        is_failed, _ = _classify_tool_failure("tool", {"success": False})
        assert is_failed is True

        # 有 error 字段
        is_failed, _ = _classify_tool_failure("tool", {"error": "some error"})
        assert is_failed is True

        # success=True
        is_failed, _ = _classify_tool_failure("tool", {"success": True})
        assert is_failed is False

    def test_classify_tool_failure_string(self):
        """测试字符串结果的失败分类"""
        # 包含 "error"
        is_failed, _ = _classify_tool_failure("tool", '{"error": "test"}')
        assert is_failed is True

        # 包含 "failed"
        is_failed, _ = _classify_tool_failure("tool", '{"failed": true}')
        assert is_failed is True

        # 以 Error 开头
        is_failed, _ = _classify_tool_failure("tool", "Error: something went wrong")
        assert is_failed is True

        # 正常结果
        is_failed, _ = _classify_tool_failure("tool", '{"success": true, "data": "..."}')
        assert is_failed is False

    def test_append_toolguard_guidance(self):
        """测试追加警告信息到结果"""
        decision = ToolLoopDecision(
            action="warn",
            code="test_warning",
            message="This is a test warning",
            count=3,
        )

        result = append_toolguard_guidance("original result", decision)

        assert "original result" in result
        assert "Tool loop warning" in result
        assert "test_warning" in result
        assert "count=3" in result

    def test_append_toolguard_guidance_no_warning(self):
        """测试无警告时不追加"""
        decision = ToolLoopDecision(action="allow")
        result = append_toolguard_guidance("original", decision)
        assert result == "original"


class TestToolLoopConfig:
    """ToolLoopConfig 测试"""

    def test_from_mapping_empty(self):
        """测试空配置"""
        config = ToolLoopConfig.from_mapping(None)
        assert config.warnings_enabled is True
        assert config.hard_stop_enabled is False

    def test_from_mapping_full(self):
        """测试完整配置"""
        data = {
            "warnings_enabled": False,
            "hard_stop_enabled": True,
            "warn_after": {
                "exact_failure": 5,
                "same_tool_failure": 10,
            },
            "hard_stop_after": {
                "exact_failure": 15,
                "same_tool_failure": 20,
            },
        }
        config = ToolLoopConfig.from_mapping(data)

        assert config.warnings_enabled is False
        assert config.hard_stop_enabled is True
        assert config.exact_failure_warn_after == 5
        assert config.same_tool_failure_warn_after == 10
        assert config.exact_failure_block_after == 15
        assert config.same_tool_failure_halt_after == 20


class TestToolCallSignature:
    """ToolCallSignature 测试"""

    def test_same_args_same_hash(self):
        """测试相同参数生成相同哈希"""
        sig1 = ToolCallSignature.from_call("test_tool", {"a": 1, "b": 2})
        sig2 = ToolCallSignature.from_call("test_tool", {"b": 2, "a": 1})  # 不同顺序
        assert sig1 == sig2

    def test_different_args_different_hash(self):
        """测试不同参数生成不同哈希"""
        sig1 = ToolCallSignature.from_call("test_tool", {"a": 1})
        sig2 = ToolCallSignature.from_call("test_tool", {"a": 2})
        assert sig1 != sig2

    def test_none_args(self):
        """测试 None 参数"""
        sig = ToolCallSignature.from_call("test_tool", None)
        assert sig.tool_name == "test_tool"
        assert sig.args_hash is not None


class TestIdempotentTools:
    """幂等工具列表测试"""

    def test_read_file_is_idempotent(self):
        """测试 read_file 是幂等工具"""
        controller = ToolLoopController()
        assert controller._is_idempotent("read_file") is True

    def test_write_file_not_idempotent(self):
        """测试 write_file 不是幂等工具"""
        controller = ToolLoopController()
        assert controller._is_idempotent("write_file") is False

    def test_terminal_not_idempotent(self):
        """测试 terminal 不是幂等工具"""
        controller = ToolLoopController()
        assert controller._is_idempotent("terminal") is False

    def test_browser_tools_not_idempotent(self):
        """测试浏览器工具不是幂等工具"""
        controller = ToolLoopController()
        assert controller._is_idempotent("browser_click") is False
        assert controller._is_idempotent("browser_navigate") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])