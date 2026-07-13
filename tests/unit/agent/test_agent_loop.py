#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for AgentLoop single-loop architecture.

Tests cover:
- AgentLoop.run() single-loop execution
- AgentState integration (unified state management)
- Interrupt handling
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch


class TestAgentLoopSingleLoop:
    """Test suite for AgentLoop single-loop architecture."""

    @pytest.mark.asyncio
    async def test_agent_loop_run_simple_exit(self):
        """Test AgentLoop.run() exits on direct_response."""
        from agent.execution.loop import AgentLoop, LoopState, LoopStepResult
        from agent.state import AgentState

        # Mock LLM provider
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "This is a direct response"
        mock_response.function_call = None
        mock_llm.generate = AsyncMock(return_value=mock_response)

        # Create unified state manager
        agent_state = AgentState(max_iterations=5)

        loop = AgentLoop(
            llm_provider=mock_llm,
            session_id="test_session",
            agent_state=agent_state,
        )

        # Create mock context
        mock_context = MagicMock()
        mock_context.task_description = "Test task"
        mock_context.tool_handlers = {}
        mock_context._messages = []
        mock_context.to_messages_dict.return_value = []
        mock_context.add_message = MagicMock()
        mock_context.add_tool_call.return_value = "call_123"
        mock_context.add_tool_result = MagicMock()
        mock_context.get.return_value = None

        # Mock tools
        loop.tools = {}

        # Mock context manager
        loop._context_manager = MagicMock()
        mock_result = MagicMock()
        mock_result.messages = [{"role": "user", "content": "Test"}]
        mock_result.compressed = False
        loop._context_manager.build_messages = AsyncMock(return_value=mock_result)

        # Run loop
        result = await loop.run(mock_context)

        # Should complete successfully
        assert result["success"] is True
        assert result["state"] == LoopState.COMPLETED.value
        # Should exit after 1 iteration (direct response)
        assert result["iterations"] == 1

    @pytest.mark.asyncio
    async def test_agent_loop_run_single_success(self):
        """Test AgentLoop.run() continues until LLM returns direct_response (no hardcoded exit).
        
        关键变化：移除了"非幂等工具成功即退出"的硬编码规则。
        现在由 LLM 自主决定何时完成任务。
        如果 LLM 持续调用工具，循环会继续直到：
        1. 预算耗尽
        2. LLM 返回 direct_response
        3. Tool Loop 检测到重复失败
        """
        from agent.execution.loop import AgentLoop, LoopState
        from agent.state import AgentState

        # Mock LLM provider that returns direct_response after one tool call
        mock_llm = MagicMock()
        
        # First call: tool call
        mock_response1 = MagicMock()
        mock_response1.content = ""
        mock_response1.function_call = {
            "name": "test_tool",
            "arguments": "{}"
        }
        
        # Second call: direct response (task complete)
        mock_response2 = MagicMock()
        mock_response2.content = "任务已完成"
        mock_response2.function_call = None
        
        mock_llm.generate = AsyncMock(side_effect=[mock_response1, mock_response2])

        # Create loop with sufficient budget
        agent_state = AgentState(max_iterations=5)

        loop = AgentLoop(
            llm_provider=mock_llm,
            session_id="test_session",
            agent_state=agent_state,
        )

        # Mock context
        mock_context = MagicMock()
        mock_context.task_description = "Test task"
        mock_context.tool_handlers = {"test_tool": AsyncMock(return_value={"success": True})}
        mock_context._messages = []
        mock_context.to_messages_dict.return_value = []
        mock_context.add_message = MagicMock()
        mock_context.add_tool_call.return_value = "call_123"
        mock_context.add_tool_result = MagicMock()
        mock_context.get.return_value = None
        mock_context.get_tools_schema.return_value = []

        loop.tools = {}

        # Mock context manager
        loop._context_manager = MagicMock()
        mock_result = MagicMock()
        mock_result.messages = [{"role": "user", "content": "Test"}]
        mock_result.compressed = False
        loop._context_manager.build_messages = AsyncMock(return_value=mock_result)

        # Mock tool executor
        loop._tool_executor = MagicMock()
        mock_tool_result = MagicMock()
        mock_tool_result.get_output.return_value = {"success": True}
        loop._tool_executor.execute = AsyncMock(return_value=mock_tool_result)

        # Run loop
        result = await loop.run(mock_context)

        # Should exit after 2 iterations:
        # - Iteration 1: tool call (LLM decides to continue)
        # - Iteration 2: direct_response (LLM decides task is complete)
        assert result["iterations"] == 2
        # State should be COMPLETED (clean exit on LLM decision)
        assert result["state"] == LoopState.COMPLETED.value

    @pytest.mark.asyncio
    async def test_agent_loop_run_interrupt(self):
        """Test AgentLoop.run() handles interrupt."""
        from agent.execution.loop import AgentLoop, LoopState
        from agent.state import AgentState

        # Mock LLM provider
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Response"
        mock_response.function_call = None
        mock_llm.generate = AsyncMock(return_value=mock_response)

        # Create unified state manager with interrupt
        agent_state = AgentState(max_iterations=10)
        agent_state.request_interrupt("test")

        loop = AgentLoop(
            llm_provider=mock_llm,
            session_id="test_session",
            agent_state=agent_state,
        )

        # Mock context
        mock_context = MagicMock()
        mock_context.task_description = "Test task"
        mock_context._messages = []
        mock_context.to_messages_dict.return_value = []
        mock_context.add_message = MagicMock()
        mock_context.add_tool_call.return_value = "call_123"
        mock_context.add_tool_result = MagicMock()
        mock_context.get.return_value = None

        loop.tools = {}

        # Mock context manager
        loop._context_manager = MagicMock()
        mock_result = MagicMock()
        mock_result.messages = [{"role": "user", "content": "Test"}]
        mock_result.compressed = False
        loop._context_manager.build_messages = AsyncMock(return_value=mock_result)

        # Run loop
        result = await loop.run(mock_context)

        # Should abort due to interrupt
        assert result["state"] == LoopState.ABORTED.value


class TestCheckpointManager:
    """Test suite for CheckpointManager."""

    def test_checkpoint_manager_init(self):
        """Test CheckpointManager initialization."""
        from agent.checkpoint import CheckpointManager, reset_checkpoint_manager

        reset_checkpoint_manager()

        mgr = CheckpointManager(enabled=False)
        assert mgr.enabled is False
        assert mgr.is_enabled() is False

    def test_should_snapshot_tool(self):
        """Test tool snapshot detection."""
        from agent.checkpoint import CheckpointManager, SNAPSHOT_TOOLS, reset_checkpoint_manager

        reset_checkpoint_manager()

        mgr = CheckpointManager(enabled=True)

        assert mgr.should_snapshot_tool("write_file") is True
        assert mgr.should_snapshot_tool("patch") is True
        assert mgr.should_snapshot_tool("terminal") is True
        assert mgr.should_snapshot_tool("str_replace_editor") is True
        assert mgr.should_snapshot_tool("todo") is False
        assert mgr.should_snapshot_tool("search") is False

    def test_is_destructive_command(self):
        """Test destructive command detection."""
        from agent.checkpoint import CheckpointManager, reset_checkpoint_manager

        reset_checkpoint_manager()

        mgr = CheckpointManager(enabled=True)

        # Destructive commands
        assert mgr.is_destructive_command("rm -rf /") is True
        assert mgr.is_destructive_command("rm -r /home") is True
        assert mgr.is_destructive_command("del /s /q *.*") is True
        assert mgr.is_destructive_command("format C:") is True

        # Safe commands
        assert mgr.is_destructive_command("ls -la") is False
        assert mgr.is_destructive_command("git status") is False
        assert mgr.is_destructive_command("echo hello") is False

    def test_project_hash_deterministic(self):
        """Test project hash is deterministic."""
        from tools.checkpoint_manager import _project_hash

        hash1 = _project_hash("/path/to/project")
        hash2 = _project_hash("/path/to/project")
        hash3 = _project_hash("/different/path")

        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 16  # SHA256[:16]


class TestCheckpointRail:
    """Test suite for CheckpointRail."""

    def test_checkpoint_rail_init(self):
        """Test CheckpointRail initialization."""
        from agent.rails.checkpoint_rail import CheckpointRail

        rail = CheckpointRail("test_session", enabled=True)
        assert rail.name == "checkpoint"
        assert rail.enabled is True

    def test_checkpoint_rail_disabled(self):
        """Test CheckpointRail when disabled."""
        from agent.rails.checkpoint_rail import CheckpointRail

        rail = CheckpointRail("test_session", enabled=False)
        assert rail.enabled is False

    def test_should_snapshot_write_file(self):
        """Test snapshot decision for write_file."""
        from agent.rails.checkpoint_rail import CheckpointRail

        rail = CheckpointRail("test_session", enabled=True)

        # With path - should snapshot
        assert rail._should_snapshot("write_file", {"path": "/tmp/test.txt"}) is True

        # Without path - should not snapshot
        assert rail._should_snapshot("write_file", {}) is False

    def test_should_snapshot_terminal_destructive(self):
        """Test snapshot decision for destructive terminal commands."""
        from agent.rails.checkpoint_rail import CheckpointRail

        rail = CheckpointRail("test_session", enabled=True)

        # Destructive - should snapshot
        assert rail._should_snapshot("terminal", {"command": "rm -rf /"}) is True

        # Safe - should not snapshot
        assert rail._should_snapshot("terminal", {"command": "ls -la"}) is False

    def test_build_snapshot_message(self):
        """Test snapshot message building."""
        from agent.rails.checkpoint_rail import CheckpointRail

        rail = CheckpointRail("test_session", enabled=True)

        msg = rail._build_snapshot_message("write_file", {"path": "/tmp/test.txt"})
        assert "write_file" in msg
        assert "/tmp/test.txt" in msg

        msg = rail._build_snapshot_message("terminal", {"command": "rm -rf /"})
        assert "terminal" in msg


class TestAgentState:
    """Test suite for AgentState (unified state management)."""

    def test_iteration_mode(self):
        """Test iteration mode budget."""
        from agent.state import AgentState

        state = AgentState(max_iterations=5)

        assert state.can_iterate() is True
        assert state.budget_remaining == 5

        state.consume()
        assert state.budget_remaining == 4
        assert state.can_iterate() is True

        # Exhaust budget
        for _ in range(4):
            state.consume()

        assert state.can_iterate() is False
        assert state.budget_remaining == 0

    def test_budget_thread_safety(self):
        """Test budget is thread-safe."""
        import threading
        from agent.state import AgentState

        state = AgentState(max_iterations=1000)

        def consume():
            for _ in range(100):
                state.consume()

        threads = [threading.Thread(target=consume) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All 1000 iterations should be consumed
        assert state.budget_used == 1000

    def test_interrupt_handling(self):
        """Test interrupt handling."""
        from agent.state import AgentState, AgentStatus

        state = AgentState()

        assert state.is_interrupt_requested is False
        assert state.status == AgentStatus.IDLE

        state.request_interrupt("user_cancelled")

        assert state.is_interrupt_requested is True
        assert state.interrupt_reason == "user_cancelled"

        state.clear_interrupt()

        assert state.is_interrupt_requested is False
        assert state.interrupt_reason is None

    def test_state_transitions(self):
        """Test state transitions."""
        from agent.state import AgentState, AgentStatus

        state = AgentState()

        # Initial state
        assert state.status == AgentStatus.IDLE

        # Start
        state.start()
        assert state.status == AgentStatus.RUNNING

        # Pause
        state.pause("user_requested")
        assert state.status == AgentStatus.PAUSED

        # Resume
        state.resume()
        assert state.status == AgentStatus.RUNNING

        # Complete
        state.complete()
        assert state.status == AgentStatus.COMPLETED

        # Reset
        state.reset()
        assert state.status == AgentStatus.IDLE

    def test_goal_mode(self):
        """Test goal mode through GoalManager (参考 Hermes)."""
        from agent.state import AgentState, BudgetMode
        from agent.goal import GoalManager

        state = AgentState(max_iterations=20, max_turns=10)
        manager = GoalManager(on_state_change=state.sync_from_goal_state)
        state.set_goal_manager(manager)

        # Set goal through GoalManager
        manager.set("Complete task X", max_turns=10)
        state.sync_from_goal_state(manager.state)

        assert state.is_goal_mode is True
        assert state.budget_mode == BudgetMode.TURN
        assert state.budget_max == 10

        # Clear goal through GoalManager
        manager.clear()

        assert state.is_goal_mode is False
        assert state.budget_mode == BudgetMode.ITERATION
        assert state.budget_max == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])