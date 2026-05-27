#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced AI reasoning module for the Custom Agent
Provides actual intelligent response generation capabilities
Supports LLM integration for AI-powered responses
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any
from core import BaseAgentModule, AgentResponse, AgentConfig
from core.exceptions import ResponseGenerationError
from core.cache import LRUCache, create_cache_key, hash_config
from core.layer_logger import get_layer_logger
import time


class AdvancedReasoningModule(BaseAgentModule):
    """
    Advanced reasoning module that provides AI-like responses.
    Supports both internal knowledge base and external LLM integration.
    """
    __slots__ = ('knowledge_base', '_cache', '_config_hash', '_llm_provider', '_reasoning_logger', '_llm_logger')
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.knowledge_base = self._load_knowledge_base()
        
        if config.enable_caching:
            self._cache = LRUCache(maxsize=50)
            self._config_hash = hash_config(config)
        else:
            self._cache = None
            self._config_hash = None
        
        self._llm_provider = None
        self._reasoning_logger = get_layer_logger("reasoning", "AdvancedReasoningModule")
        self._llm_logger = None
    
    def set_llm_provider(self, llm_provider):
        """Set LLM provider for AI-powered responses."""
        self._llm_provider = llm_provider
    
    async def process(self, input_data: str, session=None) -> AgentResponse:
        """Generate intelligent, context-aware responses.
        
        Args:
            input_data: The user's query as a string.
            
        Returns:
            AgentResponse: Structured response with intelligent content.
            
        Raises:
            ResponseGenerationError: If response generation fails unexpectedly.
        """
        reasoning = self._reasoning_logger
        
        reasoning.info(f"generate_response() 收到请求: {input_data[:30]}...")
        reasoning.info(f"   → 下一步: LRUCache 检查缓存")
        
        if hasattr(self, '_cache') and self._cache is not None:
            cache_key = create_cache_key(input_data, self._config_hash)
            cached_response = self._cache.get(cache_key)
            if cached_response is not None:
                reasoning.info(f"LRUCache 缓存命中，直接返回")
                reasoning.info(f"   → 返回结果到 [控制层]")
                return cached_response
            reasoning.info(f"LRUCache 缓存未命中，继续处理")
        
        start_time = time.time()
        
        try:
            reasoning.info(f"_classify_input() 分析输入类型...")
            reasoning.info(f"   → 下一步: _assess_complexity()")
            input_type = self._classify_input(input_data)
            complexity = self._assess_complexity(input_data)
            reasoning.info(f"InputClassifier 分类结果: {input_type}, 复杂度: {complexity}")
            reasoning.info(f"   → 下一步: 判断是否配置了 LLM provider")
            
            if self._llm_provider is not None:
                provider_name = self._llm_provider.__class__.__name__
                reasoning.info(f"{provider_name} 准备调用大模型...")
                reasoning.info(f"   → 下一步: _generate_llm_response()")
                response_content = await self._generate_llm_response(input_data, input_type, complexity)
                reasoning.info(f"{provider_name} 大模型返回成功 (长度: {len(response_content)} 字符)")
                reasoning.info(f"   → 返回结果到 [推理层]")
            else:
                reasoning.info(f"_generate_intelligent_response() 使用知识库...")
                reasoning.info(f"   → 调用: _generate_intelligent_response()")
                response_content = self._generate_intelligent_response(input_data, input_type, complexity)
                reasoning.info(f"KnowledgeBase 返回成功 (长度: {len(response_content)} 字符)")
                reasoning.info(f"   → 返回结果到 [控制层]")
            
            reasoning_steps = self._extract_reasoning_steps(response_content)
            
            execution_time = time.time() - start_time
            
            response = AgentResponse(
                content=response_content,
                reasoning_steps=reasoning_steps,
                confidence_score=self._calculate_confidence(input_data, response_content),
                metadata={
                    "input_type": input_type,
                    "complexity_level": complexity,
                    "reasoning_approach": "llm" if self._llm_provider else "knowledge_base"
                },
                execution_time=execution_time
            )
            
            # Store in cache if enabled
            if hasattr(self, '_cache') and self._cache is not None:
                cache_key = create_cache_key(input_data, self._config_hash)
                self._cache.put(cache_key, response)
            
            return response
            
        except Exception as e:
            error_msg = f"Failed to generate intelligent response for input: {input_data[:100]}..."
            self.logger.error(error_msg, exc_info=True)
            raise ResponseGenerationError(error_msg, original_exception=e)
    
    async def _generate_llm_response(self, input_data: str, input_type: str, complexity: int) -> str:
        """Generate response using LLM provider."""
        llm = self._llm_logger
        reasoning = self._reasoning_logger
        
        if not self._llm_provider:
            llm.warning("⚠️ [LLM层] 没有配置 LLM provider，回退到知识库")
            llm.info(f"   → 下一步将调用: [推理层] _generate_intelligent_response()")
            return self._generate_intelligent_response(input_data, input_type, complexity)
        
        depth_prompt = {
            0: "提供简洁的回答",
            1: "提供中等详细程度的解释",
            2: "提供详细的解释，包括示例",
            3: "提供非常详细的解释，包括背景、示例和最佳实践"
        }
        
        prompt = f"""
你是一个智能助手。请根据用户的问题提供高质量的回答。

用户问题：{input_data}

要求：{depth_prompt.get(complexity, '提供详细的解释')}

请用自然、友好的语言回答，确保回答清晰易懂。
"""
        
        provider_name = self._llm_provider.__class__.__name__
        try:
            reasoning.info(f"{provider_name} 正在调用大模型... (prompt长度: {len(prompt)} 字符)")
            reasoning.info(f"   → 下一步: _generate_llm_response()")
            response = await self._llm_provider.generate(prompt)
            reasoning.info(f"{provider_name} 大模型调用成功 (响应长度: {len(response)} 字符)")
            reasoning.info(f"   → 返回结果到 [推理层]")
            return response.strip()
        except Exception as e:
            reasoning.error(f"{provider_name} 大模型调用失败: {str(e)}，回退到知识库")
            reasoning.info(f"   → 下一步: _generate_intelligent_response()")
            return self._generate_intelligent_response(input_data, input_type, complexity)
    
    def _load_knowledge_base(self) -> Dict[str, Any]:
        """Load domain knowledge for intelligent responses."""
        return {
            "programming": {
                "python_optimization": [
                    "Use built-in functions and libraries (they're implemented in C)",
                    "Avoid unnecessary loops - use list comprehensions or generator expressions",
                    "Use appropriate data structures (sets for membership testing, deque for queue operations)",
                    "Profile your code with cProfile to identify bottlenecks",
                    "Consider using NumPy for numerical computations",
                    "Use __slots__ to reduce memory overhead for classes with many instances"
                ],
                "common_patterns": {
                    "fibonacci": "def fibonacci(n):\n    if n <= 1:\n        return n\n    a, b = 0, 1\n    for _ in range(2, n + 1):\n        a, b = b, a + b\n    return b",
                    "binary_search": "def binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1"
                }
            },
            "machine_learning": {
                "supervised_vs_unsupervised": {
                    "supervised": "Uses labeled training data with input-output pairs. Examples include classification and regression.",
                    "unsupervised": "Finds patterns in unlabeled data. Examples include clustering and dimensionality reduction."
                },
                "neural_networks": [
                    "Inspired by biological neural networks",
                    "Consist of layers of interconnected nodes (neurons)",
                    "Learn through backpropagation and gradient descent",
                    "Can model complex non-linear relationships",
                    "Require large amounts of data and computational resources"
                ]
            },
            "system_design": {
                "rest_vs_graphql": {
                    "rest": "Resource-oriented, multiple endpoints, fixed data structure per endpoint",
                    "graphql": "Query-oriented, single endpoint, client specifies exactly what data is needed"
                }
            }
        }
    
    def _classify_input(self, input_data: str) -> str:
        """Enhanced input classification."""
        input_lower = input_data.lower()
        
        # Programming/Code related
        if any(keyword in input_lower for keyword in ['python', 'code', 'function', 'algorithm', 'optimize', 'debug', 'error']):
            return 'programming'
        
        # Machine Learning/AI related
        elif any(keyword in input_lower for keyword in ['machine learning', 'neural network', 'artificial intelligence', 'deep learning']) or \
             any(keyword == word for keyword in ['ai', 'model'] for word in input_lower.split()):
            return 'machine_learning'
        
        # System Design/API related
        elif any(keyword in input_lower for keyword in ['api', 'rest', 'graphql', 'architecture', 'design', 'system']):
            return 'system_design'
        
        # General conceptual questions
        elif any(keyword in input_lower for keyword in ['what is', 'explain', 'how does', 'why', 'difference between']):
            return 'conceptual'
            
        else:
            return 'general'
    
    def _assess_complexity(self, input_data: str) -> int:
        """Assess complexity level of the input (0-3 scale)."""
        word_count = len(input_data.split())
        question_marks = input_data.count('?')
        technical_terms = len([word for word in input_data.split() 
                              if any(term in word.lower() for term in 
                                    ['algorithm', 'framework', 'architecture', 'system'])])
        
        complexity = 0
        if word_count > 50:
            complexity += 1
        if question_marks > 1:
            complexity += 1
        if technical_terms > 2:
            complexity += 1
            
        return min(complexity, 3)
    
    def _generate_intelligent_response(self, input_data: str, input_type: str, complexity: int) -> str:
        """Generate response based on knowledge base."""
        input_lower = input_data.lower()
        
        # Friendly greeting response
        if any(greeting in input_lower for greeting in ['hello', 'hi', '你好', '嗨']):
            return "你好！我是一个智能问答助手。有什么我可以帮你的吗？我可以解答编程问题、解释技术概念、提供代码示例等等。"
        
        # Response templates based on type
        responses = {
            'programming': f"""关于编程问题，我可以帮助你：

**核心概念**
- Python是一种高级、通用、解释型编程语言
- 它以简洁的语法和强大的标准库著称

**常用技巧**
- 使用列表推导式代替显式循环
- 利用内置函数提高性能
- 使用适当的数据结构

**示例代码**
```python
# 简单示例
def greet():
    return "Hello!"
```

如果你有具体的问题，请告诉我。""",
            
            'machine_learning': """机器学习是人工智能的一个分支，它使计算机能够从数据中学习而无需明确编程。

**主要类型**
- 监督学习：使用标注数据进行训练
- 无监督学习：从无标注数据中发现模式
- 强化学习：通过试错学习最优策略

**关键概念**
- 神经网络：受生物大脑启发的计算模型
- 训练/验证/测试：机器学习的标准工作流程
- 特征工程：准备和转换数据

如果你有具体的问题，请告诉我。""",
            
            'system_design': """系统设计涉及创建可扩展、可靠、可维护的软件系统。

**设计原则**
- 模块化：将系统分解为独立组件
- 可扩展性：设计能够处理增长的系统
- 容错性：处理故障和错误

**常见模式**
- REST API：资源导向的API设计
- 微服务：将应用分解为小型服务
- 消息队列：异步通信和解耦

如果你有具体的问题，请告诉我。""",
            
            'conceptual': f"""关于"{input_data}"这个问题，我可以提供以下信息：

**背景知识**
理解这个概念需要探索其基本原理和实际应用。

**核心要点**
1. 这是一个需要深入理解的概念
2. 它在多个领域都有应用
3. 有一些关键的原则需要掌握

**进一步探索**
如果你有更具体的问题，或者想要了解某个方面的详细信息，请告诉我。""",
            
            'general': f"""我理解你在问关于："{input_data}"

这是一个有趣的话题！以下是我的分析：

**关键信息**
- 这个问题涉及多个方面
- 需要综合考虑各种因素

**建议**
如果你能提供更多上下文或具体问题，我可以给出更详细的回答。

你还有其他问题吗？"""
        }
        
        return responses.get(input_type, responses['general'])
    
    def _extract_reasoning_steps(self, content: str) -> List[str]:
        """Extract key reasoning steps from response."""
        lines = content.split('\n')
        steps = []
        for i, line in enumerate(lines):
            if line.strip().startswith(('1.', '2.', '3.', '-', '*', '**')):
                steps.append(line.strip())
        return steps[:5]
    
    def _calculate_confidence(self, input_data: str, response_content: str) -> float:
        """Calculate confidence score."""
        # Higher confidence when LLM is used
        if self._llm_provider:
            return 0.95
        
        # Simple heuristic based on input clarity
        clarity_indicators = [
            '?' in input_data,
            len(input_data.split()) > 10,
            any(word in input_data.lower() for word in ['please', 'help', 'explain'])
        ]
        return min(0.7 + sum(clarity_indicators) * 0.1, 1.0)