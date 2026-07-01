#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for agent/context_halver.py
"""

import pytest
from agent.context_halver import (
    ContextHalver,
    SkillContext,
    HalverConfig,
    MessageScore,
)


class TestContextHalver:
    """Test ContextHalver functionality"""

    def test_add_skill(self):
        """Test adding skills"""
        halver = ContextHalver()
        skill = SkillContext(
            skill_id="code-review",
            name="Code Review",
            description="Review code for bugs",
            keywords=["bug", "fix"],
        )
        halver.add_skill(skill)

        assert len(halver._skills) == 1
        assert halver._skills[0].skill_id == "code-review"

    def test_score_system_message_high(self):
        """System messages should get high scores"""
        halver = ContextHalver()
        message = {"role": "system", "content": "You are a helpful assistant"}

        score = halver.score_message(message, index=0)

        assert score.score == 1.0
        assert score.reason == "system_message"

    def test_score_empty_content_low(self):
        """Empty content should get low scores"""
        halver = ContextHalver()
        message = {"role": "user", "content": ""}

        score = halver.score_message(message, index=0)

        assert score.score < 0.5

    def test_score_skill_relevant_high(self):
        """Skill-relevant content should get high scores"""
        halver = ContextHalver()
        skill = SkillContext(
            skill_id="code-review",
            name="Code Review",
            description="Review code for bugs",
            keywords=["bug", "fix", "review"],
        )
        halver.add_skill(skill)

        message = {"role": "user", "content": "Please review this code for bugs"}

        score = halver.score_message(message, index=0)

        assert score.score > 0.3
        assert "code-review" in score.reason or "match" in score.reason

    def test_halve_preserves_system_messages(self):
        """Halve should preserve system messages"""
        halver = ContextHalver(HalverConfig(system_message_preserve=True))
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        result = halver.halve(messages, target_ratio=0.5)

        # System message should be preserved
        roles = [m.get("role") for m in result]
        assert "system" in roles

    def test_halve_preserves_recent_messages(self):
        """Halve should preserve recent messages"""
        halver = ContextHalver(HalverConfig(recent_messages_preserve=2))
        messages = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(10)
        ]

        result = halver.halve(messages, target_ratio=0.5)

        # Last 2 messages should be preserved
        assert len(result) >= 2

    def test_halve_respects_min_context_messages(self):
        """Halve should respect minimum message count"""
        halver = ContextHalver(HalverConfig(min_context_messages=5))
        messages = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(20)
        ]

        result = halver.halve(messages, target_ratio=0.1)

        # Should return at least min_context_messages
        assert len(result) >= 5

    def test_halve_no_change_when_small(self):
        """Halve should not change small message lists"""
        halver = ContextHalver()
        messages = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "Hello"},
        ]

        result = halver.halve(messages, target_ratio=0.9)

        assert len(result) == 2

    def test_tokenize_chinese(self):
        """Should tokenize Chinese text"""
        text = "这是一个测试文本"
        tokens = ContextHalver._tokenize(text)

        # Full text is tokenized as single token
        assert len(tokens) >= 1
        assert any("测试" in t or "一个" in t or "文本" in t for t in tokens)

    def test_tokenize_english(self):
        """Should tokenize English text"""
        text = "This is a test sentence"
        tokens = ContextHalver._tokenize(text)

        assert "test" in tokens
        assert "sentence" in tokens

    def test_get_skill_relevance_report(self):
        """Test relevance report generation"""
        halver = ContextHalver()
        skill = SkillContext(
            skill_id="code-review",
            name="Code Review",
            description="Review code",
        )
        halver.add_skill(skill)

        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Review this code"},
            {"role": "assistant", "content": "Code looks good"},
        ]

        report = halver.get_skill_relevance_report(messages)

        assert report["total_messages"] == 3
        assert report["skill_count"] == 1
        assert "relevance_distribution" in report


class TestSkillContext:
    """Test SkillContext dataclass"""

    def test_create_skill_context(self):
        """Test creating SkillContext"""
        skill = SkillContext(
            skill_id="test",
            name="Test Skill",
            description="A test skill",
            keywords=["test"],
            tags=["testing"],
        )

        assert skill.skill_id == "test"
        assert skill.name == "Test Skill"
        assert "test" in skill.keywords


class TestHalverConfig:
    """Test HalverConfig"""

    def test_default_config(self):
        """Test default configuration"""
        config = HalverConfig()

        assert config.max_context_ratio == 0.5
        assert config.min_context_messages == 10
        assert config.recent_messages_preserve == 5
        assert config.system_message_preserve is True

    def test_custom_config(self):
        """Test custom configuration"""
        config = HalverConfig(
            max_context_ratio=0.3,
            min_context_messages=5,
        )

        assert config.max_context_ratio == 0.3
        assert config.min_context_messages == 5
