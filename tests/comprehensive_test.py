#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Handsome Agent - 综合测试套件
测试所有模块: Lightweight Agent, Gateway, Advanced Reasoning
参考: Pytest最佳实践
"""

import pytest
import asyncio
import time
from typing import Dict


# ============================================================================
# Lightweight Agent Tests (参考Zero Claw设计)
# ============================================================================

class TestLightweightAgent:
    """Lightweight Agent核心测试"""
    
    @pytest.mark.asyncio
    async def test_basic_response(self):
        """测试基本响应生成"""
        from lightweight.agent import LightweightAgent
        
        agent = LightweightAgent()
        response = await agent.respond("What is Python?")
        
        assert response.content is not None
        assert len(response.content) > 0
        assert response.confidence > 0
    
    @pytest.mark.asyncio
    async def test_caching(self):
        """测试缓存功能"""
        from lightweight.agent import LightweightAgent
        
        agent = LightweightAgent(AgentConfig(enable_caching=True))
        
        # 第一次调用
        result1 = await agent.respond("test query")
        
        # 第二次调用应该使用缓存
        result2 = await agent.respond("test query")
        
        assert result1.content == result2.content
        assert result2.execution_time < result1.execution_time
    
    @pytest.mark.asyncio
    async def test_multiple_domains(self):
        """测试多领域支持"""
        from lightweight.agent import LightweightAgent
        
        agent = LightweightAgent()
        
        queries = {
            "python": "What is Python?",
            "ml": "Explain machine learning",
            "api": "What is REST API?"
        }
        
        for domain, query in queries.items():
            response = await agent.respond(query)
            assert response.content is not None


# ============================================================================
# Enhanced Agent Tests (参考AutoGPT + Claude)
# ============================================================================

class TestEnhancedAgent:
    """增强版Agent测试 (Chain of Thought + Tool Use)"""
    
    @pytest.mark.asyncio
    async def test_chain_of_thought(self):
        """测试思维链推理"""
        from lightweight.agent_v2 import EnhancedAgent, ReasoningLevel
        
        agent = EnhancedAgent(reasoning_level=ReasoningLevel.CHAIN_OF_THOUGHT)
        result = await agent.respond("What is AI?", include_reasoning=True)
        
        assert result["reasoning"] is not None
        assert len(result["reasoning"]) > 0
        assert "decompose" in result["reasoning"].lower()
    
    @pytest.mark.asyncio
    async def test_tool_usage(self):
        """测试工具使用"""
        from lightweight.agent_v2 import EnhancedAgent
        
        agent = EnhancedAgent()
        result = await agent.respond(
            "calculate 2+2",
            include_reasoning=False,
            use_tools=True
        )
        
        assert "tools_used" in result
        assert result["confidence"] > 0
    
    @pytest.mark.asyncio
    async def test_memory_system(self):
        """测试记忆系统"""
        from lightweight.agent_v2 import EnhancedAgent
        
        agent = EnhancedAgent()
        
        # 添加记忆
        agent.reasoning_history.append(
            agent.reasoning_history.__class__.__name__(
                step_type="test",
                content="Test memory"
            )
        )
        
        assert len(agent.reasoning_history) > 0


# ============================================================================
# Gateway Tests (参考Hermes + Kong)
# ============================================================================

class TestGateway:
    """API Gateway测试"""
    
    def test_gateway_config(self):
        """测试网关配置"""
        from gateway import GatewayConfig
        
        config = GatewayConfig(
            api_keys=["test-key-123"],
            rate_limit=50,
            rate_window=30
        )
        
        assert len(config.api_keys) == 1
        assert config.rate_limit == 50
        assert config.rate_window == 30
    
    def test_auth_middleware(self):
        """测试认证中间件"""
        from gateway import GatewayConfig
        from gateway.middleware import AuthMiddleware
        
        config = GatewayConfig(api_keys=["valid-key"])
        auth = AuthMiddleware(config)
        
        # 测试有效密钥
        assert auth.check("valid-key") is True
        
        # 测试无效密钥
        assert auth.check("invalid-key") is False
    
    def test_rate_limiter(self):
        """测试限流器"""
        from gateway import GatewayConfig
        from gateway.middleware import RateLimitMiddleware
        
        config = GatewayConfig(rate_limit=3, rate_window=60)
        limiter = RateLimitMiddleware(config)
        
        # 前3个请求应该成功
        for i in range(3):
            assert limiter.check(f"client-{i}") is True
        
        # 第4个请求应该失败
        assert limiter.check("client-3") is False
    
    def test_cors_handling(self):
        """测试CORS处理"""
        from gateway import GatewayConfig
        
        config = GatewayConfig(enable_cors=True)
        
        assert config.enable_cors is True


# ============================================================================
# Advanced Reasoning Tests (参考LangChain + AutoGPT)
# ============================================================================

class TestAdvancedReasoning:
    """高级推理测试"""
    
    @pytest.mark.asyncio
    async def test_domain_classification(self):
        """测试领域分类"""
        from advanced_reasoning import AdvancedReasoningModule
        
        module = AdvancedReasoningModule()
        
        # 编程领域
        assert module._classify_input("Python code optimization") == "programming"
        
        # ML领域
        assert module._classify_input("neural network training") == "machine_learning"
        
        # 系统设计领域
        assert module._classify_input("REST API design patterns") == "system_design"
    
    @pytest.mark.asyncio
    async def test_complexity_assessment(self):
        """测试复杂度评估"""
        from advanced_reasoning import AdvancedReasoningModule
        
        module = AdvancedReasoningModule()
        
        # 简单查询
        simple = module._assess_complexity("Hi")
        assert 0 <= simple <= 3
        
        # 复杂查询
        complex_query = "Explain " + " AND ".join(["concept"] * 20)
        complex = module._assess_complexity(complex_query)
        assert 0 <= complex <= 3
    
    @pytest.mark.asyncio
    async def test_knowledge_base(self):
        """测试知识库加载"""
        from advanced_reasoning import AdvancedReasoningModule
        
        module = AdvancedReasoningModule()
        kb = module._load_knowledge_base()
        
        assert "programming" in kb
        assert "machine_learning" in kb
        assert "system_design" in kb


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """性能测试"""
    
    @pytest.mark.asyncio
    async def test_lightweight_speed(self):
        """测试轻量版响应速度"""
        from lightweight.agent import LightweightAgent
        
        agent = LightweightAgent()
        
        start = time.time()
        await agent.respond("test performance")
        elapsed = time.time() - start
        
        assert elapsed < 0.1  # 应该< 100ms
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """测试并发请求"""
        from lightweight.agent import LightweightAgent
        
        agent = LightweightAgent()
        
        # 并发10个请求
        tasks = [agent.respond(f"query {i}") for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 10
        assert all(r.content for r in results)


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """测试完整流程"""
        from lightweight.agent import LightweightAgent
        from gateway import GatewayConfig
        from gateway import GatewayConfig, run_gateway
        
        # Agent部分
        agent = LightweightAgent()
        response = await agent.respond("integration test")
        
        assert response.content is not None
        
        # Gateway部分
        config = GatewayConfig()
        assert config is not None


# ============================================================================
# 运行所有测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
