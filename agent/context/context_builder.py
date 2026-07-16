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
from common.config import load_config
from agent.progressive_disclosure import get_skills_system_prompt
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
    build_agent_self_intro,
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
    - 记忆预取由 ContextManager（协调层）完成，结果通过 memory_snapshot 参数传入
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
        memory_snapshot: str = "",
        context_files: str = "",
        context_sources: list = None,
        system_meta: dict = None,
        session_info: dict = None,
    ) -> List[Dict[str, Any]]:
        """
        构建消息列表格式的上下文（Hermes 风格）

        返回标准消息列表格式，用于需要消息列表的场景（如 OpenAI API）。

        使用三层架构构建系统消息：stable(Base) + context(Role) + volatile(Session)。

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
            memory_snapshot: 记忆快照（USER.md + MEMORY.md，由 ContextManager 提供）
            context_files: 上下文文件内容（AGENTS.md、项目规则等）
            context_sources: 上下文文件来源列表（用于日志显示）
            system_meta: Agent 启动元信息（version/provider/tools_count 等，Base 层）
            session_info: 当前会话元信息（rounds/used_tools 等，Session 层）

        Returns:
            标准消息列表
        """

        # 1. 使用 build_parts() 获取三层结构（传入记忆快照、上下文文件、元信息）
        parts = self.build_parts(
            user_message=user_message,
            model=model,
            memory_snapshot=memory_snapshot,
            context_files=context_files,
            context_sources=context_sources,
            system_meta=system_meta,
            session_info=session_info,
        )

        # 2. 合并为 system 消息（与 Hermes 一致）
        # 三层顺序：stable -> context -> volatile
        # 工具 Schema 通过 API 的 tools 参数传递
        system_content = "\n\n".join(
            [
                parts.get("stable", ""),
                parts.get("context", ""),
                parts.get("volatile", ""),
            ]
        )

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
            "volatile_sources": parts.get("volatile_sources", []),
            "context_sources": parts.get("context_sources", []),
        }
        messages.append(system_msg)

        # 5. 处理对话历史
        if conversation_history:
            history_messages = self._convert_history_to_messages(conversation_history)
            messages.extend(history_messages)

        # 6. 添加当前用户消息
        if user_message:
            messages.append({"role": "user", "content": user_message})

        # 🧠 Decision - 💾 Context - 消息列表构建完成（摘要日志）
        # 计算各层消息数
        layer1_count = 1  # system 消息
        layer2_count = len(conversation_history) if conversation_history else 0
        layer3_count = 1 if user_message else 0

        # Token 估算（简单方法：总字符数 / 3，中文约 / 2）
        total_chars = sum(len(m.get("content", "") or "") for m in messages)
        # 中英混合估算：假设平均每 token 约 3 字符
        estimated_tokens = int(total_chars / 3)
        # 格式化 token 数显示
        if estimated_tokens >= 1000:
            tokens_display = f"≈{estimated_tokens/1000:.1f}k tokens"
        else:
            tokens_display = f"≈{estimated_tokens} tokens"

        # 工具数
        tools_count = len(self.tools)

        # 输出摘要日志
        self.logger.info(
            f"📊 Context built: {len(messages)} msgs ({tokens_display}) | "
            f"tools={tools_count} | "
            f"layer1=system({layer1_count}) layer2=history({layer2_count}) layer3=current({layer3_count})"
        )

        return messages

    def _convert_history_to_messages(
        self, conversation_history: List[Dict]
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
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls")
            tool_call_id = msg.get("tool_call_id")
            name = msg.get("name")  # 工具名

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
            elif role == "tool" and tool_call_id:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": content,
                        "name": name,  # 保留工具名
                    }
                )
            # 处理普通消息
            elif role in ("user", "assistant", "system"):
                msg_dict = {"role": role}
                if content:
                    msg_dict["content"] = content
                messages.append(msg_dict)
            else:
                # 未知角色，作为 assistant 处理
                self.logger.warning(
                    f"Unknown message role: {role}, treating as assistant"
                )
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
                                "arguments": (
                                    json.dumps(tc.get("arguments", {}))
                                    if isinstance(tc.get("arguments"), dict)
                                    else str(tc.get("arguments", "{}"))
                                ),
                            },
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
        memory_snapshot: str = "",
        context_files: str = "",
        context_sources: list = None,
        system_meta: dict = None,
        session_info: dict = None,
    ) -> Dict[str, str]:
        """
        构建系统提示词的三层结构（Hermes 风格）

        三层架构（语义对齐：Base/Role/Session）：
        - stable   (Base    Layer)：Agent 身份 + 能力 + 自我认知 + 工具指导 + 模型特定指导
                                    整个会话不变，可缓存。
        - context  (Role    Layer)：项目级上下文文件（AGENTS.md、项目规则等）
                                    工作目录固定时可缓存（Role 级）。
        - volatile (Session Layer)：记忆快照（USER.md + MEMORY.md）+ 时间戳 + 会话元信息
                                    每次都可能变化，永不缓存。

        注意：
        - 记忆快照由 ContextManager（协调层）提供，构建层只负责组装
        - 用户画像（USER.md）属于 volatile 层，与 MEMORY.md 一起作为记忆快照传入
        - 上下文文件属于 context 层，由调用方通过 context_files 参数传入
        - system_meta 属于 Base(stable) 层（启动时固定，影响缓存 key）
        - session_info 属于 Session(volatile) 层（每次可能变化，不参与缓存）

        Args:
            user_message: 用户消息
            model: 模型名称（用于模型特定指导）
            memory_snapshot: 记忆快照（USER.md + MEMORY.md，由 ContextManager 提供）
            context_files: 上下文文件内容（AGENTS.md、项目规则等）
            context_sources: 上下文文件来源列表（用于日志显示）
            system_meta: Agent 启动元信息（version/provider/tools_count/skills_count 等），放在 Base 层
            session_info: 当前会话元信息（rounds/turns/used_tools/start_time 等），放在 Session 层

        Returns:
            Dict[str, str]: 包含 stable/context/volatile 三层内容的字典
        """

        # 🧠 Decision - 💾 Context - 开始构建三层架构
        self.logger.debug("Context Assembly: Building three-layer architecture")

        # 初始化缓存结构（G1a：统一初始化 + 统计计数器）
        if not hasattr(self, "_stable_cache"):
            self._stable_cache: dict[str, str] = {}
            self._context_cache: dict[str, str] = {}
            self._cache_hits: int = 0
            self._cache_misses: int = 0

        # ─────────────────────────────────────────────────────────
        # Stable Layer (Base Layer) - 会话级缓存
        # 变化条件：enable_guidance / model / coding_instructions /
        #          skills_index / system_meta(version/provider/tool_count)
        # ─────────────────────────────────────────────────────────
        model_tag = (model or "").lower()[:3]
        skills_digest = "1" if bool(getattr(self, "_skills_index_digest", None) or True) else "0"
        try:
            coding_digest = str(hash(load_config().get("agent", {}).get("coding_instructions", "") or ""))[:8]
        except Exception:
            coding_digest = "0"
        # system_meta 参与缓存键计算（G4：系统信息注入 Base 层）
        try:
            meta_digest = str(hash(tuple(sorted((system_meta or {}).items()))))[:10]
        except Exception:
            meta_digest = "0"
        cache_key = (
            f"stable_v2_g{self.enable_guidance}_m{model_tag}_"
            f"s{skills_digest}_c{coding_digest}_meta{meta_digest}"
        )

        stable_content: str | None = self._stable_cache.get(cache_key)
        stable_keys: list[str] = [
            "AGENT_IDENTITY", "CAPABILITIES", "SELF_INTRO",
            "TOOL_USE_ENFORCEMENT", "MANDATORY_TOOL_USE",
            "ACT_DONT_ASK", "MEMORY_GUIDANCE",
            "SESSION_SEARCH_GUIDANCE", "SKILLS_GUIDANCE",
        ]
        cache_hit = stable_content is not None

        if not cache_hit:
            self._cache_misses += 1
            # 构造自我认知段落（G4 + G5：Agent 知道自己是谁、什么版本、什么系统）
            meta = dict(system_meta or {})
            meta.setdefault("model", model or "Agent-Z")
            if not meta.get("cwd"):
                import os
                meta["cwd"] = os.getcwd()
            self_intro_block = build_agent_self_intro(**meta)

            stable_parts = [
                AGENT_IDENTITY,  # Agent 身份（Prompt 模板）
                CAPABILITIES,    # 能力摘要（Prompt 模板）
                self_intro_block,  # 🆕 自我认知（G4/G5：运行时真相信息块）
            ]

            # 渐进式披露技能索引（Tier 1）
            try:
                skills_index = get_skills_system_prompt()
                if skills_index:
                    stable_parts.append(skills_index)
                    stable_keys.append("SKILLS_INDEX")
            except Exception as e:
                self.logger.warning(f"Failed to load skills index: {e}")

            if self.enable_guidance:
                stable_parts.extend([
                    TOOL_USE_ENFORCEMENT,
                    MANDATORY_TOOL_USE,
                    ACT_DONT_ASK,
                    MEMORY_GUIDANCE,
                    SESSION_SEARCH_GUIDANCE,
                    SKILLS_GUIDANCE,
                ])
                if model:
                    model_lower = model.lower()
                    if any(p in model_lower for p in ["deepseek", "gpt", "grok", "glm", "qwen"]):
                        stable_parts.append(OPENAI_MODEL_EXECUTION_GUIDANCE)
                        stable_keys.append("OPENAI_MODEL_EXECUTION_GUIDANCE")
            else:
                # 未启用 guidance 时只保留最关键的 2 条强制规范
                stable_parts.extend([TOOL_USE_ENFORCEMENT, THINK_TAG_INSTRUCTION])
                stable_keys = ["AGENT_IDENTITY", "CAPABILITIES",
                               "TOOL_USE_ENFORCEMENT", "THINK_TAG_INSTRUCTION"]

            try:
                coding_instr = load_config().get("agent", {}).get("coding_instructions", "")
            except Exception:
                coding_instr = ""
            if coding_instr:
                stable_parts.append(coding_instr)
                stable_keys.append("CODING_INSTRUCTIONS")

            # 思考标签指令（强制，所有模型都要）
            if "THINK_TAG_INSTRUCTION" not in stable_keys:
                stable_parts.append(THINK_TAG_INSTRUCTION)
                stable_keys.append("THINK_TAG_INSTRUCTION")

            stable_content = "\n\n".join(p for p in stable_parts if p)
            self._stable_cache[cache_key] = stable_content
        else:
            self._cache_hits += 1

        # ─────────────────────────────────────────────────────────
        # Context Layer - 工作目录级缓存（按内容 hash）
        # 包含：AGENTS.md、项目规则、上下文文件等
        # ─────────────────────────────────────────────────────────
        if context_files and context_files.strip():
            ctx_key = "ctx_" + str(hash(context_files))[:12]
            context_content = self._context_cache.get(ctx_key)
            if context_content is None:
                context_content = context_files
                self._context_cache[ctx_key] = context_content
                self._cache_misses += 1
            else:
                self._cache_hits += 1
        else:
            context_content = ""

        # ─────────────────────────────────────────────────────────
        # Volatile Layer (Session Layer) - 每次变化，永不缓存
        # 包含：记忆快照（USER.md + MEMORY.md）+ 时间戳
        # 参照 Hermes：volatile 层放记忆和时间戳
        # ─────────────────────────────────────────────────────────
        volatile_parts = []

        # 记忆快照：USER.md + MEMORY.md（由 ContextManager 在协调层提供）
        if memory_snapshot and memory_snapshot.strip():
            volatile_parts.append(memory_snapshot)

        # 时间戳（使用日精度，与 Hermes 一致，避免 stable 层缓存失效）
        timestamp = time.strftime("%Y-%m-%d")
        volatile_parts.append(f"Conversation started: {timestamp}")

        # 🆕 G3: Session 层注入当前对话元信息（轮数/已调用工具/启动时间等）
        if session_info:
            si = session_info
            rounds = si.get("rounds", si.get("turns", 0))
            used_tools = si.get("used_tools") or si.get("tools_called") or []
            start_time = si.get("start_time") or si.get("session_start") or ""
            session_id = si.get("session_id", "")
            user_lang = si.get("user_lang") or si.get("language", "zh")

            session_lines = ["## Current Session - 当前对话状态"]
            if session_id:
                session_lines.append(f"- Session ID: `{session_id}`")
            if rounds:
                session_lines.append(f"- 对话轮次: `{rounds}`")
            if start_time:
                session_lines.append(f"- 会话启动时间: `{start_time}`")
            session_lines.append(f"- 用户偏好语言: `{user_lang}`")
            if used_tools:
                # 取不重复且最新的 20 个工具名
                seen, uniq = [], []
                for t in reversed(list(used_tools)):
                    if t and t not in seen:
                        seen.append(t)
                        uniq.append(t)
                uniq = uniq[:20]
                session_lines.append(f"- 本会话已使用工具({len(uniq)}): `{', '.join(uniq)}`")
            volatile_parts.append("\n".join(session_lines))

        volatile_content = "\n\n".join(p for p in volatile_parts if p and p.strip())

        # 🧠 Decision - 💾 Context - 三层架构构建完成
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total else 0.0
        self.logger.debug(
            f"Context Assembly: three-layer complete - "
            f"stable={len(stable_content)} chars, "
            f"context={len(context_content)} chars, "
            f"volatile={len(volatile_content)} chars | "
            f"cache h/m={self._cache_hits}/{self._cache_misses} ({hit_rate:.0f}%)"
        )

        return {
            "stable": stable_content,
            "context": context_content,
            "volatile": volatile_content,
            "stable_keys": stable_keys,
            "volatile_sources": ["USER.md", "MEMORY.md"] if memory_snapshot else [],
            "context_sources": context_sources or [],
        }


__all__ = ["ContextBuilder"]
