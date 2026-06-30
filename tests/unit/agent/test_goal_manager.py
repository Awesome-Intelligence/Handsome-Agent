#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the Goal Manager module.

Tests cover:
- GoalState model serialization and deserialization
- GoalManager initialization and state management
- Goal lifecycle (set, pause, resume, clear, mark_done)
- Subgoal management (add, remove, clear, render)
- Judge response parsing
- evaluate() method - core entry point for exit decisions
- Continuation prompt generation
"""

import pytest
import json
import time
from unittest.mock import MagicMock, patch, AsyncMock

from agent.goal.manager import GoalManager
from agent.goal.models import GoalState, GoalStatus, JudgeVerdict
from agent.state.enums import ExitDecision, ExitReason


class TestGoalStatus:
    """Test GoalStatus enum."""

    def test_status_values(self):
        """Test all status values."""
        assert GoalStatus.ACTIVE.value == "active"
        assert GoalStatus.PAUSED.value == "paused"
        assert GoalStatus.DONE.value == "done"
        assert GoalStatus.CLEARED.value == "cleared"
        assert GoalStatus.EXPIRED.value == "expired"


class TestGoalState:
    """Test GoalState model."""

    def test_goal_state_creation(self):
        """Test creating a GoalState."""
        state = GoalState(
            goal="Write a blog post",
            max_turns=10,
            current_turn=3,
        )

        assert state.goal == "Write a blog post"
        assert state.max_turns == 10
        assert state.current_turn == 3
        assert state.status == GoalStatus.ACTIVE.value
        assert state.subgoals == []
        assert state.consecutive_parse_failures == 0

    def test_goal_state_set_status(self):
        """Test setting status with history recording."""
        state = GoalState(goal="Test")

        assert state.status == GoalStatus.ACTIVE.value
        assert len(state.status_history) == 0

        state.set_status(GoalStatus.PAUSED.value, "User paused")

        assert state.status == GoalStatus.PAUSED.value
        assert len(state.status_history) == 1
        assert state.status_history[0]["from_status"] == GoalStatus.ACTIVE.value
        assert state.status_history[0]["to_status"] == GoalStatus.PAUSED.value
        assert state.status_history[0]["reason"] == "User paused"

    def test_goal_state_set_same_status(self):
        """Test setting same status doesn't create new history."""
        state = GoalState(goal="Test")

        state.set_status(GoalStatus.ACTIVE.value, "test")

        assert len(state.status_history) == 0

    def test_goal_state_to_from_json(self):
        """Test JSON serialization and deserialization."""
        state = GoalState(
            goal="Write a blog post",
            max_turns=10,
            current_turn=5,
            status=GoalStatus.ACTIVE.value,
            subgoals=["requirement 1", "requirement 2"],
            last_verdict=True,
            last_reason="completed",
        )

        json_str = state.to_json()
        parsed = GoalState.from_json(json_str)

        assert parsed.goal == "Write a blog post"
        assert parsed.max_turns == 10
        assert parsed.current_turn == 5
        assert parsed.subgoals == ["requirement 1", "requirement 2"]
        assert parsed.last_verdict is True
        assert parsed.last_reason == "completed"

    def test_goal_state_completed_at(self):
        """Test completed_at is set when status changes to terminal state."""
        state = GoalState(goal="Test")

        assert state.completed_at is None

        state.set_status(GoalStatus.DONE.value, "completed")

        assert state.completed_at is not None


class TestGoalManagerInitialization:
    """Test GoalManager initialization."""

    def test_manager_default_init(self):
        """Test default initialization."""
        manager = GoalManager()

        assert manager._default_max_turns == 90  # 参考 Hermes 的默认值
        assert manager._judge_timeout == 30.0
        assert manager._judge_max_tokens == 4096
        assert manager._current_goal is None

    def test_manager_custom_init(self):
        """Test custom initialization parameters."""
        mock_llm = MagicMock()
        manager = GoalManager(
            session_id="test_session",
            judge_llm_provider=mock_llm,
            default_max_turns=15,
            judge_timeout=60.0,
            judge_max_tokens=2048,
        )

        assert manager._default_max_turns == 15
        assert manager._judge_timeout == 60.0
        assert manager._judge_max_tokens == 2048
        assert manager._judge_llm is mock_llm


class TestGoalManagerStateManagement:
    """Test Goal lifecycle management."""

    def test_set_goal(self):
        """Test setting a new goal."""
        manager = GoalManager()

        state = manager.set("Write a blog post about AI", max_turns=10)

        assert state is not None
        assert state.goal == "Write a blog post about AI"
        assert state.max_turns == 10
        assert state.status == GoalStatus.ACTIVE.value
        assert manager.is_active() is True

    def test_set_empty_goal_raises(self):
        """Test setting empty goal raises ValueError."""
        manager = GoalManager()

        with pytest.raises(ValueError, match="goal text is empty"):
            manager.set("")

    def test_create_goal_alias(self):
        """Test create_goal alias works."""
        manager = GoalManager()

        state = manager.create_goal("Test goal")

        assert state is not None
        assert state.goal == "Test goal"

    def test_pause_goal(self):
        """Test pausing a goal."""
        manager = GoalManager()
        manager.set("Test goal")

        manager.pause(reason="Taking a break")

        assert manager.state.status == GoalStatus.PAUSED.value
        assert manager.state.paused_reason == "Taking a break"
        assert manager.is_active() is False
        assert manager.has_goal() is True

    def test_resume_goal(self):
        """Test resuming a goal."""
        manager = GoalManager()
        manager.set("Test goal")
        manager.pause()

        manager.resume(reset_budget=True)

        assert manager.state.status == GoalStatus.ACTIVE.value
        assert manager.state.paused_reason is None
        assert manager.state.current_turn == 0
        assert manager.is_active() is True

    def test_resume_goal_no_reset(self):
        """Test resuming a goal without resetting budget."""
        manager = GoalManager()
        manager.set("Test goal")
        manager.pause()
        manager.state.current_turn = 5

        manager.resume(reset_budget=False)

        assert manager.state.current_turn == 5

    def test_clear_goal(self):
        """Test clearing a goal."""
        manager = GoalManager()
        manager.set("Test goal")

        manager.clear()

        assert manager.state is None
        assert manager.is_active() is False
        assert manager.has_goal() is False

    def test_mark_done(self):
        """Test marking a goal as done."""
        manager = GoalManager()
        manager.set("Test goal")

        manager.mark_done("Completed successfully")

        assert manager.state.status == GoalStatus.DONE.value
        assert manager.state.last_verdict is True
        assert manager.state.last_reason == "Completed successfully"

    def test_status_line(self):
        """Test status_line method."""
        manager = GoalManager()

        assert "No active goal" in manager.status_line()

        manager.set("Test goal")
        assert "active" in manager.status_line()

        manager.pause()
        assert "paused" in manager.status_line()

        manager.clear()
        assert "No active goal" in manager.status_line()


class TestGoalManagerSubgoals:
    """Test subgoal management."""

    def test_add_subgoal(self):
        """Test adding a subgoal."""
        manager = GoalManager()
        manager.set("Main goal")

        result = manager.add_subgoal("Subgoal 1")

        assert result == "Subgoal 1"
        assert len(manager.state.subgoals) == 1
        assert manager.state.subgoals[0] == "Subgoal 1"

    def test_add_subgoal_without_active_goal(self):
        """Test adding subgoal without active goal raises."""
        manager = GoalManager()

        with pytest.raises(RuntimeError, match="no active goal"):
            manager.add_subgoal("Subgoal")

    def test_add_empty_subgoal(self):
        """Test adding empty subgoal raises."""
        manager = GoalManager()
        manager.set("Main goal")

        with pytest.raises(ValueError, match="subgoal text is empty"):
            manager.add_subgoal("")

    def test_remove_subgoal(self):
        """Test removing a subgoal."""
        manager = GoalManager()
        manager.set("Main goal")
        manager.add_subgoal("Subgoal 1")
        manager.add_subgoal("Subgoal 2")

        removed = manager.remove_subgoal(1)

        assert removed == "Subgoal 1"
        assert len(manager.state.subgoals) == 1
        assert manager.state.subgoals[0] == "Subgoal 2"

    def test_remove_subgoal_invalid_index(self):
        """Test removing subgoal with invalid index."""
        manager = GoalManager()
        manager.set("Main goal")
        manager.add_subgoal("Subgoal 1")

        with pytest.raises(IndexError):
            manager.remove_subgoal(2)

    def test_clear_subgoals(self):
        """Test clearing all subgoals."""
        manager = GoalManager()
        manager.set("Main goal")
        manager.add_subgoal("Subgoal 1")
        manager.add_subgoal("Subgoal 2")

        prev_count = manager.clear_subgoals()

        assert prev_count == 2
        assert len(manager.state.subgoals) == 0

    def test_get_subgoals(self):
        """Test getting subgoals."""
        manager = GoalManager()
        manager.set("Main goal")
        manager.add_subgoal("Subgoal 1")

        subgoals = manager.get_subgoals()

        assert subgoals == ["Subgoal 1"]
        assert subgoals is not manager.state.subgoals

    def test_render_subgoals_block(self):
        """Test rendering subgoals as numbered block."""
        manager = GoalManager()
        manager.set("Main goal")
        manager.add_subgoal("Requirement 1")
        manager.add_subgoal("Requirement 2")

        block = manager.render_subgoals_block()

        assert "- 1. Requirement 1" in block
        assert "- 2. Requirement 2" in block


class TestGoalManagerJudgeParsing:
    """Test Judge response parsing."""

    def test_parse_judge_response_valid_json(self):
        """Test parsing valid JSON response."""
        manager = GoalManager()

        raw = '{"done": true, "reason": "Goal completed"}'
        done, reason, parse_failed = manager._parse_judge_response(raw)

        assert done is True
        assert reason == "Goal completed"
        assert parse_failed is False

    def test_parse_judge_response_false(self):
        """Test parsing JSON with done=false."""
        manager = GoalManager()

        raw = '{"done": false, "reason": "Need more steps"}'
        done, reason, parse_failed = manager._parse_judge_response(raw)

        assert done is False
        assert reason == "Need more steps"
        assert parse_failed is False

    def test_parse_judge_response_with_markdown(self):
        """Test parsing JSON with markdown code block."""
        manager = GoalManager()

        raw = '```json\n{"done": true, "reason": "Completed"}\n```'
        done, reason, parse_failed = manager._parse_judge_response(raw)

        assert done is True
        assert reason == "Completed"
        assert parse_failed is False

    def test_parse_judge_response_extract_json(self):
        """Test extracting JSON from text."""
        manager = GoalManager()

        raw = "Here is my verdict: {\"done\": true, \"reason\": \"OK\"}"
        done, reason, parse_failed = manager._parse_judge_response(raw)

        assert done is True
        assert reason == "OK"
        assert parse_failed is False

    def test_parse_judge_response_invalid_json(self):
        """Test parsing invalid JSON."""
        manager = GoalManager()

        raw = "not valid json"
        done, reason, parse_failed = manager._parse_judge_response(raw)

        assert done is False
        assert parse_failed is True

    def test_parse_judge_response_empty(self):
        """Test parsing empty response."""
        manager = GoalManager()

        raw = ""
        done, reason, parse_failed = manager._parse_judge_response(raw)

        assert done is False
        assert parse_failed is True

    def test_parse_judge_response_string_true(self):
        """Test parsing JSON with string "true"."""
        manager = GoalManager()

        raw = '{"done": "true", "reason": "Completed"}'
        done, reason, parse_failed = manager._parse_judge_response(raw)

        assert done is True


class TestGoalManagerContinuationPrompt:
    """Test continuation prompt generation."""

    def test_next_continuation_prompt(self):
        """Test generating continuation prompt."""
        manager = GoalManager()
        manager.set("Write a blog post")

        prompt = manager.next_continuation_prompt()

        assert prompt is not None
        assert "Write a blog post" in prompt
        assert "Continue working" in prompt

    def test_next_continuation_prompt_with_subgoals(self):
        """Test generating continuation prompt with subgoals."""
        manager = GoalManager()
        manager.set("Write a blog post")
        manager.add_subgoal("Include introduction")

        prompt = manager.next_continuation_prompt()

        assert prompt is not None
        assert "Include introduction" in prompt

    def test_next_continuation_prompt_no_active_goal(self):
        """Test continuation prompt when no active goal."""
        manager = GoalManager()

        prompt = manager.next_continuation_prompt()

        assert prompt is None

    def test_next_continuation_prompt_paused(self):
        """Test continuation prompt when goal is paused."""
        manager = GoalManager()
        manager.set("Test goal")
        manager.pause()

        prompt = manager.next_continuation_prompt()

        assert prompt is None


class TestGoalManagerEvaluate:
    """Test evaluate() method - core exit decision logic."""

    @pytest.mark.asyncio
    async def test_evaluate_no_active_goal(self):
        """Test evaluate when no active goal."""
        manager = GoalManager()

        result = await manager.evaluate("response", 1, 10)

        assert result.should_exit is True
        assert result.reason == ExitReason.UNKNOWN

    @pytest.mark.asyncio
    async def test_evaluate_judge_done(self):
        """Test evaluate when Judge says done."""
        manager = GoalManager()
        manager.set("Test goal")

        with patch.object(manager, '_call_judge_async', return_value=("done", "completed", False)):
            result = await manager.evaluate("I completed the task", 1, 10)

        assert result.should_exit is True
        assert result.reason == ExitReason.GOAL_COMPLETED
        assert "目标达成" in result.message
        assert manager.state.status == GoalStatus.DONE.value

    @pytest.mark.asyncio
    async def test_evaluate_judge_continue(self):
        """Test evaluate when Judge says continue."""
        manager = GoalManager()
        manager.set("Test goal")

        with patch.object(manager, '_call_judge_async', return_value=("continue", "need more steps", False)):
            result = await manager.evaluate("Working on it", 1, 10)

        assert result.should_exit is False
        assert result.reason == ExitReason.UNKNOWN
        assert result.continuation_prompt is not None
        assert manager.state.status == GoalStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_evaluate_budget_exhausted(self):
        """Test evaluate when budget is exhausted."""
        manager = GoalManager()
        manager.set("Test goal")

        with patch.object(manager, '_call_judge_async', return_value=("continue", "need more steps", False)):
            result = await manager.evaluate("Working on it", 10, 10)

        assert result.should_exit is True
        assert result.reason == ExitReason.GOAL_PAUSED
        assert "轮次已用完" in result.message
        assert manager.state.status == GoalStatus.PAUSED.value

    @pytest.mark.asyncio
    async def test_evaluate_parse_failures(self):
        """Test evaluate when Judge returns unparseable output."""
        manager = GoalManager()
        manager.set("Test goal")
        manager.state.consecutive_parse_failures = 2

        with patch.object(manager, '_call_judge_async', return_value=("continue", "error", True)):
            result = await manager.evaluate("response", 1, 10)

        assert result.should_exit is True
        assert result.reason == ExitReason.GOAL_PAUSED
        assert "Judge" in result.message


class TestGoalManagerHelpers:
    """Test helper methods."""

    def test_truncate(self):
        """Test _truncate method."""
        manager = GoalManager()

        text = "hello world"
        assert manager._truncate(text, 100) == text

        long_text = "a" * 100
        assert len(manager._truncate(long_text, 50)) == 50 + len("… [truncated]")

    def test_render_subgoals_block_static(self):
        """Test _render_subgoals_block_static method."""
        subgoals = ["Goal 1", "Goal 2"]

        block = GoalManager._render_subgoals_block_static(subgoals)

        assert "- 1. Goal 1" in block
        assert "- 2. Goal 2" in block


class TestGoalManagerPersistence:
    """Test persistence methods."""

    def test_has_saved_goal(self):
        """Test has_saved_goal method."""
        manager = GoalManager()

        assert manager.has_saved_goal("test_session") is False


class TestJudgeVerdict:
    """Test JudgeVerdict model."""

    def test_verdict_creation(self):
        """Test creating a JudgeVerdict."""
        verdict = JudgeVerdict(done=True, reason="completed", todo_list=[{"task": "done"}])

        assert verdict.done is True
        assert verdict.reason == "completed"
        assert verdict.todo_list == [{"task": "done"}]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])