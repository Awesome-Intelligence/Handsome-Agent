#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context Builder - 独立的上下文构建器

将上下文拼装逻辑从 LLMToolSelector 中分离出来，职责更清晰。

参考 Hermes 的 system_prompt.py 和 prompt_builder.py 实现。

架构：
- ContextBuilder: 专门负责构建完整的系统提示词（使用三层架构）
- LLMToolSelector: 只负责工具选择 + 执行

职责：
1. Agent 定义（身份、能力、用户信息）
2. 构建工具 Schema
3. 收集对话历史
4. 组装完整的系统提示词（三层架构）

注意：记忆预取由 ContextManager（协调层）完成，构建层只负责组装。

日志子层：💾 Context
"""

import json
import time
from typing import Any, Dict, List, Optional

from common.logging_manager import get_decision_logger
from agent.context.prompt_templates import (
    AGENT_IDENTITY,
    CAPABILITIES,
    MEMORY_GUIDANCE,
    SESSION_SEARCH_GUIDANCE,
    SKILLS_GUIDANCE,
    TOOL_USE_ENFORCEMENT,
    MANDATORY_TOOL_USE,
    ACT_DONT_ASK,
    OPENAI_MODEL_EXECUTION_GUIDANCE,
    THINK_TAG_INSTRUCTION,
    DEFAULT_USER_PROFILE,
)


class ContextBuilder:
    """
    上下文构建器 - 专门负责构建完整的系统提示词
    
    职责：
    1. 加载 Agent 定义（身份、能力、用户信息）
    2. 构建工具 Schema
    3. 收集对话历史
    4. 组装完整的系统提示词（三层架构）
    
    注意：
    - 记忆预取由 ContextManager（协调层）完成，结果通过 memory_context 参数传入
    - 用户画像由调用方通过 user_profile 参数传入
    - 构建层只负责组装，不持有任何存储层引用（职责分离原则）
    
    日志子层：💾 Context
    """
    
    def __init__(
        self,
        tools: Optional[Dict[str, Any]] = None,
        enable_guidance: bool = True,
    ):
        """
        Args:
            tools: 工具字典 {name: ToolDefinition}
            enable_guidance: 是否添加工具使用指导（memory, skills 等）
        """
        self.logger = get_decision_logger(self.__class__.__name__, sublayer="context")
        self.tools = tools or {}
        self.enable_guidance = enable_guidance
        
        # 🧠 Decision - 💾 Context - 上下文构建器初始化
        self.logger.debug(
            f"ContextBuilder initialized (enable_guidance={enable_guidance})"
        )
    
    def set_tools(self, tools: Dict[str, Any]) -> None:
        """设置工具字典"""
        self.tools = tools or {}
        self.logger.debug(f"Tools set: {len(self.tools)} tools available")

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """获取工具 Schema 列表（用于 LLM）

        使用统一的 schema_registry 生成 OpenAI 格式的工具 Schema。
        """
        from tools.schema_registry import generate_openai_tools_schema
        return generate_openai_tools_schema(self.tools)
    
    def build_messages(
        self,
        conversation_history: Optional[List[Dict]] = None,
        include_tools: bool = True,
        user_message: str = "",
        model: str = None,
        memory_context: str = "",
        user_profile: str = "",
    ) -> List[Dict[str, Any]]:
        """
        构建消息列表格式的上下文（Hermes 风格）

        返回标准消息列表格式，用于需要消息列表的场景（如 OpenAI API）。

        使用三层架构构建系统消息：stable + context + volatile。

        格式示例：
        [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."},
            {"role": "assistant", "tool_calls": [...]},
            {"role": "tool", "tool_call_id": "...", "content": "..."},
            ...
        ]

        Args:
            conversation_history: 对话历史
            include_tools: 是否包含工具列表
            user_message: 用户消息
            model: 模型名称（用于注入模型特定指导）
            memory_context: 预取的记忆上下文（由 ContextManager 提供）
            user_profile: 用户画像内容（由调用方提供）

        Returns:
            标准消息列表
        """
        # 🧠 Decision - 💾 Context - 开始构建消息列表
        self.logger.info("Context Assembly: Building message list format (three-layer)")

        # 1. 使用 build_parts() 获取三层结构（传入预取的记忆上下文和用户画像）
        parts = self.build_parts(
            user_message=user_message,
            model=model,
            memory_context=memory_context,
            user_profile=user_profile,
        )

        # 2. 合并为 system 消息（与 Hermes 一致）
        # 三层顺序：stable -> context -> volatile
        # 工具 Schema 通过 API 的 tools 参数传递
        system_content = "\n\n".join([
            parts.get("stable", ""),
            parts.get("context", ""),
            parts.get("volatile", "")
        ])

        # 3. 构建消息列表
        messages: List[Dict[str, Any]] = []
        # System 消息添加元数据：prompt_key 用于日志标识
        system_msg = {"role": "system", "content": system_content}
        # 记录各层长度和模板变量名（用于日志显示）
        system_msg["_prompt_meta"] = {
            "stable_chars": len(parts.get("stable", "")),
            "context_chars": len(parts.get("context", "")),
            "volatile_chars": len(parts.get("volatile", "")),
            "stable_keys": parts.get("stable_keys", []),
        }
        messages.append(system_msg)

        # 5. 处理对话历史
        if conversation_history:
            history_messages = self._convert_history_to_messages(conversation_history)
            messages.extend(history_messages)

        # 6. 添加当前用户消息
        if user_message:
            messages.append({"role": "user", "content": user_message})

        # 🧠 Decision - 💾 Context - 消息列表构建完成
        self.logger.debug(
            f"Context Assembly: Message list built with {len(messages)} messages, "
            f"stable={len(parts.get('stable', ''))} chars, "
            f"context={len(parts.get('context', ''))} chars, "
            f"volatile={len(parts.get('volatile', ''))} chars, "
            f"tools_count={len(self.tools)}"
        )

        return messages

    def _convert_history_to_messages(
        self,
        conversation_history: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        将对话历史转换为标准消息列表格式
        
        处理各种消息格式：
        - 普通文本消息：{"role": "user/assistant", "content": "..."}
        - 工具调用消息：{"role": "assistant", "tool_calls": [...]}
        - 工具结果消息：{"role": "tool", "tool_call_id": "...", "content": "..."}
        
        Args:
            conversation_history: 对话历史
            
        Returns:
            标准消息列表
        """
        messages = []
        
        for msg in conversation_history:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            tool_calls = msg.get('tool_calls')
            tool_call_id = msg.get('tool_call_id')
            name = msg.get('name')  # 工具名
            
            # 处理工具调用消息
            if tool_calls:
                # assistant 消息可以同时有 content 和 tool_calls
                assistant_msg = {"role": "assistant"}
                if content:
                    assistant_msg["content"] = content
                # 添加 tool_calls
                assistant_msg["tool_calls"] = self._normalize_tool_calls(tool_calls)
                messages.append(assistant_msg)
            # 处理工具结果消息
            elif role == 'tool' and tool_call_id:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": content,
                    "name": name  # 保留工具名
                })
            # 处理普通消息
            elif role in ('user', 'assistant', 'system'):
                msg_dict = {"role": role}
                if content:
                    msg_dict["content"] = content
                messages.append(msg_dict)
            else:
                # 未知角色，作为 assistant 处理
                self.logger.warning(f"Unknown message role: {role}, treating as assistant")
                msg_dict = {"role": "assistant"}
                if content:
                    msg_dict["content"] = content
                messages.append(msg_dict)
        
        return messages
    
    def _normalize_tool_calls(self, tool_calls: Any) -> List[Dict[str, Any]]:
        """
        标准化工具调用格式
        
        支持多种格式的 tool_calls：
        - OpenAI 格式：[{"id": "...", "type": "function", "function": {...}}]
        - 简化格式：[{"name": "...", "arguments": {...}}]
        
        Args:
            tool_calls: 原始工具调用数据
            
        Returns:
            标准化的工具调用列表
        """
        if not tool_calls:
            return []
        
        normalized = []
        # 处理列表格式
        if isinstance(tool_calls, list):
            for tc in tool_calls:
                if isinstance(tc, dict):
                    # OpenAI 格式已有 id 和 function
                    if "function" in tc:
                        normalized.append(tc)
                    # 简化格式需要转换为标准格式
                    else:
                        normalized_tc = {
                            "id": tc.get("id", f"call_{len(normalized)}"),
                            "type": "function",
                            "function": {
                                "name": tc.get("name", ""),
                                "arguments": json.dumps(tc.get("arguments", {})) if isinstance(tc.get("arguments"), dict) else str(tc.get("arguments", "{}"))
                            }
                        }
                        normalized.append(normalized_tc)
                else:
                    self.logger.warning(f"Skipping non-dict tool call: {type(tc)}")
        
        return normalized
    
    def _get_user_profile(self, user_profile: str = "") -> str:
        """
        获取用户画像
        
        Args:
            user_profile: 由调用方传入的用户画像内容
            
        Returns:
            用户画像内容，默认为 DEFAULT_USER_PROFILE
        """
        if user_profile and user_profile.strip():
            self.logger.debug(f"Using provided user profile: {len(user_profile)} chars")
            return user_profile
        
        # 降级到默认模板
        self.logger.debug("Using default user profile template")
        return DEFAULT_USER_PROFILE

    def build_parts(
        self,
        user_message: str = "",
        model: str = None,
        memory_context: str = "",
        user_profile: str = "",
    ) -> Dict[str, str]:
        """
        构建系统提示词的三层结构（Hermes 风格）
        
        三层架构：
        - stable: Agent 身份 + 能力 + 工具指导 + 技能索引 + 模型特定指导（会话级缓存）
        - context: 用户画像 + 项目上下文（配置相关）
        - volatile: 记忆预取 + 时间戳（每次变化）
        
        注意：
        - 记忆预取应在协调层（ContextManager）完成，这里只接收预取结果
        - 用户画像由调用方通过 user_profile 参数传入
        
        Args:
            user_message: 用户消息
            model: 模型名称（用于模型特定指导）
            memory_context: 预取的记忆上下文（由 ContextManager 提供）
            user_profile: 用户画像内容（由调用方提供）
            
        Returns:
            Dict[str, str]: 包含 stable/context/volatile 三层内容的字典
        """
        # 🧠 Decision - 💾 Context - 开始构建三层架构
        self.logger.debug("Context Assembly: Building three-layer architecture")

        # ─────────────────────────────────────────────────────────
        # Stable Layer - 会话级缓存
        # ─────────────────────────────────────────────────────────
        cache_key = f"stable_v1_guidance_{self.enable_guidance}"

        # 尝试从缓存获取 stable 层
        if hasattr(self, '_stable_cache') and cache_key in self._stable_cache:
            stable_parts = [self._stable_cache[cache_key]]
        else:
            stable_parts = []

        # 构建 stable 层内容
        # 工具 Schema 通过 API 的 tools 参数传递
        stable_parts = [
            AGENT_IDENTITY,                              # Agent 身份
            CAPABILITIES,                                # 能力摘要
        ]
        
        # 记录 stable 层使用的模板变量名（用于日志）
        stable_keys = ["AGENT_IDENTITY", "CAPABILITIES"]

        # 仅当启用指导时添加指导性文本
        if self.enable_guidance:
            stable_parts.extend([
                TOOL_USE_ENFORCEMENT,                       # 工具使用强制规范
                MANDATORY_TOOL_USE,                          # 必须使用工具的场景
                ACT_DONT_ASK,                                # 行动而非询问
                MEMORY_GUIDANCE,                             # 记忆使用指导
                SESSION_SEARCH_GUIDANCE,                     # 跨会话搜索指导
                SKILLS_GUIDANCE,                             # 技能保存指导
            ])
            stable_keys.extend([
                "TOOL_USE_ENFORCEMENT",
                "MANDATORY_TOOL_USE",
                "ACT_DONT_ASK",
                "MEMORY_GUIDANCE",
                "SESSION_SEARCH_GUIDANCE",
                "SKILLS_GUIDANCE",
            ])

            # 模型特定指导
            if model:
                model_lower = model.lower()
                if any(p in model_lower for p in ["deepseek", "gpt", "grok", "glm", "qwen"]):
                    stable_parts.append(OPENAI_MODEL_EXECUTION_GUIDANCE)
                    stable_keys.append("OPENAI_MODEL_EXECUTION_GUIDANCE")
        
        stable_content = "\n\n".join(stable_parts)
        
        # 缓存 stable 层
        if not hasattr(self, '_stable_cache'):
            self._stable_cache = {}
        self._stable_cache[cache_key] = stable_content
        
        # ─────────────────────────────────────────────────────────
        # Context Layer - 配置相关，永不缓存
        # ─────────────────────────────────────────────────────────
        context_content = self._get_user_profile(user_profile)
        
        # ─────────────────────────────────────────────────────────
        # Volatile Layer - 每次变化，永不缓存
        # ─────────────────────────────────────────────────────────
        volatile_parts = []
        
        # 记忆上下文由 ContextManager 在协调层预取后传入
        # 构建层只负责组装，不再进行预取（职责分离）
        if memory_context:
            volatile_parts.append(memory_context)
        
        # 时间戳（使用日精度，与 Hermes 一致，避免 stable 层缓存失效）
        timestamp = time.strftime("%Y-%m-%d")
        volatile_parts.append(f"Conversation started: {timestamp}")
        
        volatile_content = "\n\n".join(volatile_parts)
        
        # 🧠 Decision - 💾 Context - 三层架构构建完成
        self.logger.debug(
            f"Context Assembly: three-layer complete - "
            f"stable={len(stable_content)} chars, "
            f"context={len(context_content)} chars, "
            f"volatile={len(volatile_content)} chars"
        )
        
        return {
            "stable": stable_content,
            "context": context_content,
            "volatile": volatile_content,
            "stable_keys": stable_keys,
        }


__all__ = ["ContextBuilder"]