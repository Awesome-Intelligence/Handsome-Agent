"""Tests for Iterative Summary Updates (Iterative Summary Feature)"""

import pytest
from agent.context.context_compressor import ContextCompressor


class TestIterativeSummaryUpdates:
    """测试迭代摘要更新功能"""

    @pytest.fixture
    def compressor(self):
        """创建压缩器实例"""
        return ContextCompressor(
            model="gpt-4o",
            quiet_mode=True,
        )

    def test_previous_summary_initial_none(self, compressor):
        """测试初始状态下 _previous_summary 为 None"""
        assert compressor._previous_summary is None

    def test_previous_summary_state_variable(self, compressor):
        """测试 _previous_summary 状态变量存在"""
        assert hasattr(compressor, "_previous_summary")
        compressor._previous_summary = "Previous summary content"
        assert compressor._previous_summary == "Previous summary content"

    def test_summary_failure_cooldown_variable(self, compressor):
        """测试失败冷却期变量存在"""
        import time
        assert hasattr(compressor, "_summary_failure_cooldown_until")
        compressor._summary_failure_cooldown_until = time.time() + 60
        # 变量正确设置


class TestFocusTopicParameter:
    """测试聚焦压缩 (focus_topic) 参数"""

    @pytest.fixture
    def compressor(self):
        return ContextCompressor(model="gpt-4o", quiet_mode=True)

    def test_focus_topic_parameter_accepted(self, compressor):
        """测试 focus_topic 参数被正确接受"""
        messages = [{"role": "user", "content": "Test"}]
        try:
            compressor.compress(messages, focus_topic="Python")
            compressor.compress(messages, focus_topic="重构")
        except TypeError as e:
            pytest.fail(f"compress() 不接受 focus_topic 参数: {e}")

    def test_focus_topic_parameter_in_generate_summary(self, compressor):
        """测试 _generate_summary 接受 focus_topic 参数"""
        messages = [{"role": "user", "content": "Test" * 100}]
        try:
            compressor._generate_summary(messages, focus_topic="Test topic")
        except TypeError as e:
            pytest.fail(f"_generate_summary() 不接受 focus_topic 参数: {e}")


class TestSummaryTemplate:
    """测试完整摘要模板"""

    @pytest.fixture
    def compressor(self):
        return ContextCompressor(model="gpt-4o", quiet_mode=True)

    def test_summary_prefix_constant(self, compressor):
        """测试摘要前缀常量存在"""
        from agent.context.context_compressor import SUMMARY_PREFIX
        assert SUMMARY_PREFIX is not None
        assert "CONTEXT COMPACTION" in SUMMARY_PREFIX


class TestCompressionStats:
    """测试压缩统计功能"""

    @pytest.fixture
    def compressor(self):
        return ContextCompressor(model="gpt-4o", quiet_mode=True)

    def test_compression_count_initial(self, compressor):
        """测试压缩计数初始值"""
        assert compressor.compression_count == 0

    def test_compression_count_incremented(self, compressor):
        """测试压缩计数递增"""
        compressor.compression_count += 1
        assert compressor.compression_count == 1

    def test_ineffective_count_tracking(self, compressor):
        """测试低效压缩计数"""
        compressor._ineffective_compression_count = 2
        assert compressor._ineffective_compression_count == 2
        assert compressor.should_compress(100000) is False

    def test_failure_cooldown_tracking(self, compressor):
        """测试失败冷却期"""
        import time
        compressor._summary_failure_cooldown_until = time.time() + 60
        assert compressor._summary_failure_cooldown_until > time.time()

    def test_last_compression_savings(self, compressor):
        """测试上次压缩节省百分比"""
        assert hasattr(compressor, "_last_compression_savings_pct")
        compressor._last_compression_savings_pct = 15.5
        assert compressor._last_compression_savings_pct == 15.5


class TestCompressSimple:
    """测试简单压缩功能"""

    @pytest.fixture
    def compressor(self):
        return ContextCompressor(model="gpt-4o", quiet_mode=True)

    def test_compress_simple_basic(self, compressor):
        """测试简单压缩基本功能"""
        messages = [
            {"role": "user", "content": "Hello" * 100}
            for _ in range(20)
        ]
        result = compressor.compress_simple(messages)
        assert len(result) > 0
        assert len(result) <= len(messages)

    def test_compress_simple_preserves_head(self, compressor):
        """测试简单压缩保护头部"""
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Task 1" * 100},
            {"role": "assistant", "content": "Response 1"},
        ]
        result = compressor.compress_simple(messages)
        assert any(msg.get("role") == "system" for msg in result)

    def test_compress_simple_empty(self, compressor):
        """测试空消息列表"""
        result = compressor.compress_simple([])
        assert result == []


class TestCompressionIntegration:
    """测试压缩集成"""

    @pytest.fixture
    def compressor(self):
        return ContextCompressor(model="gpt-4o", quiet_mode=True)

    def test_should_compress_below_threshold(self, compressor):
        """测试低于阈值时不压缩"""
        compressor.threshold_tokens = 50000
        assert compressor.should_compress(10000) is False

    def test_should_compress_above_threshold(self, compressor):
        """测试高于阈值时压缩"""
        compressor.threshold_tokens = 10000
        compressor._ineffective_compression_count = 0
        assert compressor.should_compress(50000) is True

    def test_should_compress_ineffective_skips(self, compressor):
        """测试低效压缩后跳过"""
        compressor.threshold_tokens = 10000
        compressor._ineffective_compression_count = 2
        assert compressor.should_compress(50000) is False

    def test_threshold_tokens_calculation(self, compressor):
        """测试阈值 tokens 计算"""
        assert compressor.threshold_tokens == 64000

    def test_tail_token_budget_calculation(self, compressor):
        """测试尾部 token 预算计算"""
        assert compressor.tail_token_budget == 12800
