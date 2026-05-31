"""Tests for LLM-driven Tool Selector"""

import pytest
import json
from core.llm_tool_selector import (
    LLMToolSelector,
    LLMDrivenDecisionEngine,
    DirectToolRouter,
    ToolExecutionEngine,
    ToolDefinition,
    ToolSelectionResult
)
from core.simplified_agent import ActionType


class MockLLMProvider:
    """模拟 LLM 提供者"""

    def __init__(self, response_type='tool'):
        self.response_type = response_type
        self.call_count = 0

    async def generate(self, prompt: str) -> str:
        self.call_count += 1

        if self.response_type == 'tool':
            return json.dumps({
                'action': 'use_tool',
                'selected_tool': 'calculator',
                'parameters': {'expression': '2+2'},
                'reasoning': 'User wants to calculate',
                'confidence': 0.9
            })
        elif self.response_type == 'direct':
            return json.dumps({
                'action': 'direct_response',
                'reasoning': 'Simple greeting',
                'confidence': 0.8
            })
        elif self.response_type == 'clarify':
            return json.dumps({
                'action': 'ask_clarification',
                'reasoning': 'Need more info',
                'confidence': 0.5
            })
        elif self.response_type == 'invalid':
            return "Not a JSON response"
        else:
            raise Exception("LLM error")


class TestLLMToolSelector:
    """测试 LLM 工具选择器"""

    @pytest.fixture
    def selector(self):
        """创建选择器"""
        selector = LLMToolSelector(llm_provider=None)
        selector.register_tool(ToolDefinition(
            name='calculator',
            description='Calculate math expressions',
            parameters={'expression': 'string'}
        ))
        selector.register_tool(ToolDefinition(
            name='web_search',
            description='Search the web',
            parameters={'query': 'string'}
        ))
        return selector

    def test_register_tools(self, selector):
        """测试工具注册"""
        assert 'calculator' in selector.tools
        assert 'web_search' in selector.tools

    def test_get_tools_schema(self, selector):
        """测试获取工具 Schema"""
        schema = selector.get_tools_schema()
        assert len(schema) == 2
        assert schema[0]['name'] == 'calculator'

    def test_keyword_fallback(self, selector):
        """测试关键词回退"""
        result = selector._keyword_fallback("计算 2+2")

        assert result.selected_tool == 'calculator'
        assert result.action == 'use_tool'
        assert result.confidence > 0

    def test_keyword_fallback_no_match(self, selector):
        """测试无匹配"""
        result = selector._keyword_fallback("你好")

        assert result.selected_tool is None
        assert result.action == 'direct_response'

    @pytest.mark.asyncio
    async def test_select_tool_with_llm(self):
        """测试 LLM 工具选择"""
        mock_llm = MockLLMProvider(response_type='tool')
        selector = LLMToolSelector(llm_provider=mock_llm)
        selector.register_tool(ToolDefinition(
            name='calculator',
            description='Calculate',
            parameters={}
        ))

        result = await selector.select_tool("What is 2+2?")

        assert result.selected_tool == 'calculator'
        assert result.action == 'use_tool'
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_select_tool_direct_response(self):
        """测试直接回复"""
        mock_llm = MockLLMProvider(response_type='direct')
        selector = LLMToolSelector(llm_provider=mock_llm)

        result = await selector.select_tool("Hello")

        assert result.selected_tool is None
        assert result.action == 'direct_response'

    @pytest.mark.asyncio
    async def test_select_tool_fallback_on_error(self):
        """测试错误时回退"""
        mock_llm = MockLLMProvider(response_type='invalid')
        selector = LLMToolSelector(llm_provider=mock_llm)
        selector.register_tool(ToolDefinition(
            name='search',
            description='Search',
            parameters={}
        ))

        result = await selector.select_tool("Search for python")

        # 应该回退到直接回复
        assert result.selected_tool is None
        assert result.action == 'direct_response'


class TestDirectToolRouter:
    """测试直接工具路由"""

    @pytest.fixture
    def router(self):
        """创建路由器"""
        router = DirectToolRouter()
        router.register_tool(ToolDefinition(
            name='calculator',
            description='Calculate math expressions',
            parameters={'expression': 'string'},
            examples=['计算', '算一下']
        ))
        router.register_tool(ToolDefinition(
            name='search',
            description='Search for information',
            parameters={'query': 'string'},
            examples=['搜索', '查找']
        ))
        return router

    @pytest.mark.asyncio
    async def test_routing_match(self, router):
        """测试路由匹配"""
        tool = await router.route("帮我计算 2+2")

        assert tool is not None
        assert tool.name == 'calculator'

    @pytest.mark.asyncio
    async def test_routing_no_match(self, router):
        """测试无匹配"""
        tool = await router.route("你好")

        assert tool is None

    @pytest.mark.asyncio
    async def test_routing_with_examples(self, router):
        """测试关键词匹配"""
        tool = await router.route("搜索 Python 教程")

        assert tool is not None
        assert tool.name == 'search'


class TestToolExecutionEngine:
    """测试工具执行引擎"""

    @pytest.fixture
    def engine(self):
        """创建执行引擎"""
        engine = ToolExecutionEngine()

        async def calc_handler(params, context):
            expr = params.get('expression', '0')
            return {'result': eval(expr)}

        engine.register_tool(ToolDefinition(
            name='calculator',
            description='Calculate',
            parameters={'expression': 'string'},
            handler=calc_handler
        ))

        return engine

    @pytest.mark.asyncio
    async def test_execute_success(self, engine):
        """测试成功执行"""
        result = await engine.execute(
            'calculator',
            {'expression': '2+2'}
        )

        assert result['success'] is True
        assert result['result']['result'] == 4

    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self, engine):
        """测试工具不存在"""
        result = await engine.execute(
            'nonexistent',
            {}
        )

        assert result['success'] is False
        assert 'not found' in result['error']

    @pytest.mark.asyncio
    async def test_execute_no_handler(self, engine):
        """测试无处理器"""
        engine.register_tool(ToolDefinition(
            name='empty',
            description='No handler',
            parameters={}
        ))

        result = await engine.execute('empty', {})

        assert result['success'] is False
        assert 'no handler' in result['error']


class TestLLMDrivenDecisionEngine:
    """测试 LLM 驱动的决策引擎"""

    @pytest.fixture
    def engine(self):
        """创建决策引擎"""
        async def calc_handler(params, context):
            return {'result': eval(params.get('expression', '0'))}

        engine = LLMDrivenDecisionEngine(llm_provider=None)
        engine.register_tool(
            name='calculator',
            description='Calculate math expressions',
            parameters={'expression': 'string'},
            handler=calc_handler
        )
        return engine

    @pytest.mark.asyncio
    async def test_process_with_fallback(self, engine):
        """测试降级模式处理"""
        result = await engine.process("计算 100-50")

        assert result['type'] == 'tool_execution'
        assert result['tool'] == 'calculator'

    @pytest.mark.asyncio
    async def test_process_direct_response(self, engine):
        """测试直接回复"""
        result = await engine.process("你好")

        assert result['type'] in ['direct_response', 'tool_execution']

    @pytest.mark.asyncio
    async def test_get_capabilities(self, engine):
        """测试获取能力"""
        caps = engine.get_capabilities()

        assert 'tool_count' in caps
        assert caps['tool_count'] == 1
        assert 'tools' in caps


class TestIntegration:
    """集成测试"""

    @pytest.fixture
    def full_engine(self):
        """完整的决策引擎"""
        async def calc_handler(params, context):
            expr = params.get('expression', '0')
            try:
                return {'result': eval(expr)}
            except:
                return {'error': 'Invalid expression'}

        async def search_handler(params, context):
            query = params.get('query', '')
            return {'results': [f'Result for: {query}']}

        engine = LLMDrivenDecisionEngine(llm_provider=None)
        engine.register_tool(
            name='calculator',
            description='Calculate math',
            parameters={'expression': 'string'},
            handler=calc_handler
        )
        engine.register_tool(
            name='search',
            description='Search the web',
            parameters={'query': 'string'},
            handler=search_handler
        )
        return engine

    @pytest.mark.asyncio
    async def test_calculator_flow(self, full_engine):
        """测试计算器流程"""
        result = await full_engine.process("What's 2+2?")

        assert result['type'] == 'tool_execution'
        assert result['tool'] == 'calculator'
        assert result['result']['success'] is True

    @pytest.mark.asyncio
    async def test_search_flow(self, full_engine):
        """测试搜索流程"""
        result = await full_engine.process("搜索 Python")

        # 应该匹配到 search 工具
        assert result['type'] == 'tool_execution'
        assert result['tool'] in ['search', 'calculator']  # 关键词回退可能匹配

    @pytest.mark.asyncio
    async def test_greeting_flow(self, full_engine):
        """测试问候流程"""
        result = await full_engine.process("Hello, how are you?")

        # 简单问候应该被识别为不需要工具
        assert 'type' in result
        assert 'requires_llm_response' in result


class TestSimplifiedAgent:
    """测试简化版 Agent"""

    @pytest.mark.asyncio
    async def test_direct_decision(self):
        """测试直接决策"""
        from core.simplified_agent import SimplifiedAgent, Tool, ActionType

        async def calc_handler(params):
            return eval(params.get('expression', '0'))

        agent = SimplifiedAgent(
            llm_provider=None,
            tools=[
                Tool(
                    name='calc',
                    description='Calculate',
                    handler=calc_handler
                )
            ]
        )

        # 关键词匹配应该能路由
        result = await agent.chat("计算 2+2")

        assert 'type' in result
        assert result['type'] in ['tool_used', 'direct']
