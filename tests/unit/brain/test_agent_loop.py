"""Agent Loop 单元测试"""
import pytest
from brain.agent.agent_loop import AgentLoop, AgentConfig, AgentState


class TestAgentLoop:
    """AgentLoop 测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.config = AgentConfig(
            max_iterations=5,
            timeout_seconds=30.0,
        )
        self.agent = AgentLoop(self.config)
    
    def test_agent_initialization(self):
        """测试 Agent 初始化"""
        assert self.agent.config == self.config
        assert self.agent.state == AgentState.IDLE
        assert self.agent.llm_provider is None
        assert self.agent._iteration == 0
    
    def test_set_llm_provider(self):
        """测试设置 LLM Provider"""
        mock_provider = object()
        self.agent.set_llm_provider(mock_provider)
        assert self.agent.llm_provider == mock_provider
    
    def test_get_state(self):
        """测试获取状态"""
        state = self.agent.get_state()
        assert state == AgentState.IDLE
    
    def test_reset(self):
        """测试重置"""
        self.agent.state = AgentState.THINKING
        self.agent._iteration = 3
        self.agent._conversation_history.append({"role": "user", "content": "test"})
        
        self.agent.reset()
        
        assert self.agent.state == AgentState.IDLE
        assert self.agent._iteration == 0
        assert len(self.agent._conversation_history) == 0
    
    @pytest.mark.asyncio
    async def test_run_simple_question(self):
        """测试简单问答"""
        result = await self.agent.run("你好")
        
        assert "response" in result
        assert "reasoning_steps" in result
        assert "iterations" in result
        assert result["iterations"] >= 1
        assert result["metadata"]["state"] == AgentState.DONE.value
    
    @pytest.mark.asyncio
    async def test_run_with_max_iterations(self):
        """测试达到最大迭代次数"""
        config = AgentConfig(max_iterations=2)
        agent = AgentLoop(config)
        
        # 模拟需要多次迭代的场景
        result = await agent.run("执行一个复杂的任务")
        
        assert result["iterations"] <= config.max_iterations
    
    @pytest.mark.asyncio
    async def test_run_with_context(self):
        """测试带上下文运行"""
        context = {"user_id": "test_user", "session_id": "test_session"}
        result = await self.agent.run("你好", context=context)
        
        assert "response" in result
    
    @pytest.mark.asyncio
    async def test_rule_based_think(self):
        """测试基于规则的思考"""
        thought = await self.agent._rule_based_think("你好", "")
        
        assert thought.reasoning is not None
        assert thought.is_final is True
        assert thought.action is None
    
    @pytest.mark.asyncio
    async def test_rule_based_think_with_command(self):
        """测试命令执行场景"""
        thought = await self.agent._rule_based_think("帮我执行 git status", "")
        
        assert thought.action is not None
        assert thought.action.tool_name == "shell_execute"
        assert thought.is_final is False
    
    @pytest.mark.asyncio
    async def test_rule_based_think_with_file(self):
        """测试文件操作场景"""
        thought = await self.agent._rule_based_think("帮我写一个 Python 函数", "")
        
        assert thought.action is not None
        assert thought.action.tool_name == "file_edit"
        assert thought.is_final is False
    
    def test_get_available_tools(self):
        """测试获取可用工具"""
        tools = self.agent._get_available_tools()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool
    
    @pytest.mark.asyncio
    async def test_act_shell_execute(self):
        """测试 Shell 执行动作"""
        from brain.agent.schemas import Action
        
        action = Action(tool_name="shell_execute", parameters={"command": "ls"})
        result = await self.agent._act(action, {})
        
        assert "ls" in result
    
    @pytest.mark.asyncio
    async def test_act_file_edit(self):
        """测试文件编辑动作"""
        from brain.agent.schemas import Action
        
        action = Action(tool_name="file_edit", parameters={"content": "test content"})
        result = await self.agent._act(action, {})
        
        assert "File modified" in result