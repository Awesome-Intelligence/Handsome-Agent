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
from core.logging_manager import get_decision_logger, get_llm_logger
import time


class AdvancedReasoningModule(BaseAgentModule):
    """
    Advanced reasoning module that provides AI-like responses.
    Supports both internal knowledge base and external LLM integration.
    """
    __slots__ = ('knowledge_base', '_cache', '_config_hash', '_llm_provider', '_decision_logger', '_llm_logger')
    
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
        self._decision_logger = get_decision_logger("AdvancedReasoningModule")
        self._llm_logger = get_llm_logger("AdvancedReasoningModule")
    
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
        decision = self._decision_logger
        
        decision.info(f"generate_response() 收到请求: {input_data[:30]}...")
        decision.info(f"   → 下一步: LRUCache 检查缓存")
        
        if hasattr(self, '_cache') and self._cache is not None:
            cache_key = create_cache_key(input_data, self._config_hash)
            cached_response = self._cache.get(cache_key)
            if cached_response is not None:
                decision.info(f"LRUCache 缓存命中，直接返回")
                decision.info(f"   → 返回结果到 [决策层]")
                return cached_response
            decision.info(f"LRUCache 缓存未命中，继续处理")
        
        start_time = time.time()
        
        try:
            decision.info(f"_classify_input() 分析输入类型...")
            decision.info(f"   → 下一步: _assess_complexity()")
            input_type = self._classify_input(input_data)
            complexity = self._assess_complexity(input_data)
            decision.info(f"InputClassifier 分类结果: {input_type}, 复杂度: {complexity}")
            decision.info(f"   → 下一步: 判断是否配置了 LLM provider")
            
            if self._llm_provider is not None:
                provider_name = self._llm_provider.__class__.__name__
                decision.info(f"{provider_name} 准备调用大模型...")
                decision.info(f"   → 下一步: _generate_llm_response()")
                response_content = await self._generate_llm_response(input_data, input_type, complexity)
                decision.info(f"{provider_name} 大模型返回成功 (长度: {len(response_content)} 字符)")
                decision.info(f"   → 返回结果到 [决策层]")
            else:
                decision.info(f"_generate_intelligent_response() 使用知识库...")
                decision.info(f"   → 调用: _generate_intelligent_response()")
                response_content = self._generate_intelligent_response(input_data, input_type, complexity)
                decision.info(f"KnowledgeBase 返回成功 (长度: {len(response_content)} 字符)")
                decision.info(f"   → 返回结果到 [决策层]")
            
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
        decision = self._decision_logger
        
        if not self._llm_provider:
            decision.warning("⚠️ [决策层] 没有配置 LLM provider，回退到知识库")
            decision.info(f"   → 下一步将调用: [决策层] _generate_intelligent_response()")
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
            self._llm_logger.debug(f"🤖 [LLM层] ┌─ LLM 调用请求:")
            self._llm_logger.debug(f"🤖 [LLM层] │  Prompt ({len(prompt)} 字符):")
            for i, line in enumerate(prompt.split('\n')):
                if line.strip():
                    self._llm_logger.debug(f"🤖 [LLM层] │    {line}")
            self._llm_logger.debug(f"🤖 [LLM层] └─ 正在等待响应...")
            
            response = await self._llm_provider.generate(prompt)
            
            self._llm_logger.summary(f"🤖 [LLM层] {provider_name} 返回成功")
            self._llm_logger.debug(f"🤖 [LLM层] ├─ 响应长度: {len(response)} 字符")
            self._llm_logger.debug(f"🤖 [LLM层] └─ 响应内容:\n{response[:500]}{'...' if len(response) > 500 else ''}")
            
            decision.info(f"{provider_name} 大模型调用成功 (响应长度: {len(response)} 字符)")
            return response.strip()
        except Exception as e:
            decision.error(f"{provider_name} 大模型调用失败: {str(e)}，回退到知识库")
            decision.info(f"   → 下一步: _generate_intelligent_response()")
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
        
        if any(keyword in input_lower for keyword in ['python', 'code', 'function', 'algorithm', 'optimize', 'debug', 'error', 'implement', 'fibonacci', 'binary search', 'sort', 'recursion']):
            return 'programming'
        
        elif any(keyword in input_lower for keyword in ['machine learning', 'neural network', 'artificial intelligence', 'deep learning']) or \
             any(keyword == word for keyword in ['ai', 'model'] for word in input_lower.split()):
            return 'machine_learning'
        
        elif any(keyword in input_lower for keyword in ['api', 'rest', 'graphql', 'architecture', 'design', 'system']):
            return 'system_design'
        
        elif any(keyword in input_lower for keyword in ['what is', 'explain', 'how does', 'why', 'difference between']):
            return 'conceptual'
            
        else:
            return 'general'
    
    def _assess_complexity(self, input_data: str) -> int:
        """Assess complexity level of the input (0-3 scale)."""
        input_lower = input_data.lower()
        word_count = len(input_data.split())
        question_marks = input_data.count('?')
        technical_terms = len([word for word in input_data.split() 
                              if any(term in word.lower() for term in 
                                    ['algorithm', 'framework', 'architecture', 'system', 'optimize', 'performance'])])
        
        complexity = 0
        if word_count > 50:
            complexity += 1
        if question_marks > 1:
            complexity += 1
        if technical_terms > 2:
            complexity += 1
        if any(keyword in input_lower for keyword in ['optimize', 'performance', 'implement', 'detailed']):
            complexity += 1
            
        return min(complexity, 3)
    
    def _generate_intelligent_response(self, input_data: str, input_type: str, complexity: int) -> str:
        """Generate response based on knowledge base."""
        input_lower = input_data.lower()
        
        if any(greeting in input_lower for greeting in ['hello', 'hi', '你好', '嗨']):
            return "你好！我是一个智能问答助手。有什么我可以帮你的吗？我可以解答编程问题、解释技术概念、提供代码示例等等。"
        
        if input_type == 'programming' and self.knowledge_base:
            patterns = self.knowledge_base.get('programming', {}).get('common_patterns', {})
            for pattern_name, pattern_code in patterns.items():
                if pattern_name.lower() in input_lower:
                    return self._generate_pattern_response(pattern_name, pattern_code, complexity)
            
            if any(keyword in input_lower for keyword in ['optimize', 'optimization', 'performance', 'faster']):
                return self._generate_optimization_response(complexity)
        
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
            
            'machine_learning': """机器学习 (Machine Learning) 是人工智能的一个分支，它使计算机能够从数据中学习而无需明确编程。

**主要类型 (Main Types)**
- 监督学习 (Supervised Learning)：使用标注数据进行训练
- 无监督学习 (Unsupervised Learning)：从无标注数据中发现模式
- 强化学习 (Reinforcement Learning)：通过试错学习最优策略

**关键概念 (Key Concepts)**
- 神经网络 (Neural Networks)：受生物大脑启发的计算模型
- 训练/验证/测试 (Train/Val/Test)：机器学习的标准工作流程
- 特征工程 (Feature Engineering)：准备和转换数据

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
    
    def _generate_optimization_response(self, complexity: int) -> str:
        """Generate response for Python optimization queries."""
        if complexity >= 2:
            return """关于Python代码性能优化 (Python Performance Optimization)，我有以下建议：

**性能优化的核心原则 (Core Optimization Principles)**
1. 避免不必要的重复计算 (Avoid redundant computations)
2. 使用高效的数据结构 (Use efficient data structures)
3. 利用Python内置函数和库 (Use Python built-in functions)
4. 减少内存分配和复制 (Reduce memory allocation)

**常用优化技巧 (Common Optimization Techniques)**
- 使用列表推导式代替显式循环 (Use list comprehensions)
- 使用生成器处理大数据集 (Use generators for large datasets)
- 利用内置函数（map, filter, reduce）
- 使用适当的数据结构（set用于成员测试，deque用于队列操作）

**性能分析工具 (Profiling Tools)**
- cProfile：Python内置的性能分析器
- timeit：测量小代码片段的执行时间
- memory_profiler：分析内存使用

**实际案例 (Practical Examples)**
- 避免在循环中使用字符串拼接（使用join）
- 使用局部变量缓存属性访问
- 使用__slots__减少类实例内存开销

如果你想了解更具体的优化技巧，请告诉我。"""
        else:
            return """关于Python代码优化 (Python Code Optimization)：

**核心建议 (Core Recommendations)**
- 使用列表推导式代替循环 (Use list comprehensions)
- 利用内置函数提高性能 (Use built-in functions)
- 使用适当的数据结构 (Use appropriate data structures)
- 避免不必要的计算 (Avoid unnecessary calculations)

**性能提示 (Performance Tips)**
- 使用生成器代替列表 (Use generators instead of lists)
- 利用缓存提高性能 (Use caching for better performance)
- 选择正确的数据结构 (Choose the right data structure)

如果你有具体问题，请告诉我。"""
    
    def _generate_pattern_response(self, pattern_name: str, pattern_code: str, complexity: int) -> str:
        """Generate response for specific programming patterns."""
        descriptions = {
            'fibonacci': 'Fibonacci 斐波那契数列',
            'binary_search': 'Binary Search 二分查找算法'
        }
        description = descriptions.get(pattern_name, pattern_name)
        
        if complexity >= 2:
            return f"""关于 {description} 的问题，我来帮你解答：

**什么是 {description}？**
{description}是计算机科学中常用的基础算法，在很多场景中都有应用。

**实现代码**
```python
{pattern_code}
```

**代码解释**
1. 函数接收必要的参数
2. 通过迭代或递归的方式计算结果
3. 返回计算结果

如果你想了解更优化的版本或有其他问题，请告诉我。"""
        else:
            return f"""关于 {description}，这是实现代码：

```python
{pattern_code}
```

如果你有更具体的问题，请告诉我。"""
    
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
        if self._llm_provider:
            return 0.95
        
        clarity_indicators = [
            '?' in input_data,
            len(input_data.split()) > 10,
            any(word in input_data.lower() for word in ['please', 'help', 'explain'])
        ]
        return min(0.7 + sum(clarity_indicators) * 0.1, 1.0)