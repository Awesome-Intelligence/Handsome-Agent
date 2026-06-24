#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Prompt Templates - 提示模板测试

测试所有提示模板常量的正确定义和内容。

日志子层：💾 Context
"""

import pytest


class TestAgentIdentity:
    """Agent 身份定义测试"""
    
    def test_agent_identity_exists(self):
        """测试 AGENT_IDENTITY 常量存在"""
        from agent.context.prompt_templates import AGENT_IDENTITY
        assert AGENT_IDENTITY is not None
        assert len(AGENT_IDENTITY) > 0
    
    def test_agent_identity_has_name(self):
        """测试包含 Agent 名称"""
        from agent.context.prompt_templates import AGENT_IDENTITY
        assert "Handsome Agent" in AGENT_IDENTITY
    
    def test_agent_identity_has_principles(self):
        """测试包含核心原则"""
        from agent.context.prompt_templates import AGENT_IDENTITY
        assert "核心身份" in AGENT_IDENTITY
        assert "理解用户意图" in AGENT_IDENTITY
    
    def test_agent_identity_has_capabilities(self):
        """测试包含能力边界"""
        from agent.context.prompt_templates import AGENT_IDENTITY
        assert "你能做的" in AGENT_IDENTITY
        assert "你不能做的" in AGENT_IDENTITY


class TestCapabilities:
    """能力清单测试"""
    
    def test_capabilities_exists(self):
        """测试 CAPABILITIES 常量存在"""
        from agent.context.prompt_templates import CAPABILITIES
        assert CAPABILITIES is not None
        assert len(CAPABILITIES) > 0
    
    def test_capabilities_has_overview(self):
        """测试包含能力概览"""
        from agent.context.prompt_templates import CAPABILITIES
        assert "能力概览" in CAPABILITIES
        assert "Intent Recognition" in CAPABILITIES
    
    def test_capabilities_has_tools(self):
        """测试包含核心工具"""
        from agent.context.prompt_templates import CAPABILITIES
        assert "核心工具" in CAPABILITIES
        assert "open_browser" in CAPABILITIES
        assert "execute_terminal" in CAPABILITIES


class TestMemoryGuidance:
    """记忆使用指南测试"""
    
    def test_memory_guidance_exists(self):
        """测试 MEMORY_GUIDANCE 常量存在"""
        from agent.context.prompt_templates import MEMORY_GUIDANCE
        assert MEMORY_GUIDANCE is not None
        assert len(MEMORY_GUIDANCE) > 0
    
    def test_memory_guidance_has_title(self):
        """测试包含标题"""
        from agent.context.prompt_templates import MEMORY_GUIDANCE
        assert "Memory System" in MEMORY_GUIDANCE
        assert "记忆系统" in MEMORY_GUIDANCE
    
    def test_memory_guidance_has_usage(self):
        """测试包含使用说明"""
        from agent.context.prompt_templates import MEMORY_GUIDANCE
        assert "memory" in MEMORY_GUIDANCE.lower()
        assert "action=" in MEMORY_GUIDANCE
    
    def test_memory_guidance_has_when_to_use(self):
        """测试包含使用场景"""
        from agent.context.prompt_templates import MEMORY_GUIDANCE
        assert "何时使用" in MEMORY_GUIDANCE


class TestSessionSearchGuidance:
    """跨会话搜索指南测试"""
    
    def test_session_search_guidance_exists(self):
        """测试 SESSION_SEARCH_GUIDANCE 常量存在"""
        from agent.context.prompt_templates import SESSION_SEARCH_GUIDANCE
        assert SESSION_SEARCH_GUIDANCE is not None
        assert len(SESSION_SEARCH_GUIDANCE) > 0
    
    def test_session_search_has_title(self):
        """测试包含标题"""
        from agent.context.prompt_templates import SESSION_SEARCH_GUIDANCE
        assert "Session Search" in SESSION_SEARCH_GUIDANCE
        assert "跨会话搜索" in SESSION_SEARCH_GUIDANCE
    
    def test_session_search_has_usage(self):
        """测试包含使用说明"""
        from agent.context.prompt_templates import SESSION_SEARCH_GUIDANCE
        assert "session_search" in SESSION_SEARCH_GUIDANCE


class TestSkillsGuidance:
    """技能保存指南测试"""
    
    def test_skills_guidance_exists(self):
        """测试 SKILLS_GUIDANCE 常量存在"""
        from agent.context.prompt_templates import SKILLS_GUIDANCE
        assert SKILLS_GUIDANCE is not None
        assert len(SKILLS_GUIDANCE) > 0
    
    def test_skills_guidance_has_title(self):
        """测试包含标题"""
        from agent.context.prompt_templates import SKILLS_GUIDANCE
        assert "Skills System" in SKILLS_GUIDANCE
        assert "技能系统" in SKILLS_GUIDANCE
    
    def test_skills_guidance_has_usage(self):
        """测试包含使用说明"""
        from agent.context.prompt_templates import SKILLS_GUIDANCE
        assert "skill_manage" in SKILLS_GUIDANCE


class TestDefaultUserProfile:
    """默认用户画像测试"""
    
    def test_default_user_profile_exists(self):
        """测试 DEFAULT_USER_PROFILE 常量存在"""
        from agent.context.prompt_templates import DEFAULT_USER_PROFILE
        assert DEFAULT_USER_PROFILE is not None
        assert len(DEFAULT_USER_PROFILE) > 0
    
    def test_default_user_profile_has_title(self):
        """测试包含标题"""
        from agent.context.prompt_templates import DEFAULT_USER_PROFILE
        assert "User Profile" in DEFAULT_USER_PROFILE
        assert "用户画像" in DEFAULT_USER_PROFILE
    
    def test_default_user_profile_has_defaults(self):
        """测试包含默认值"""
        from agent.context.prompt_templates import DEFAULT_USER_PROFILE
        assert "未配置" in DEFAULT_USER_PROFILE
        assert "时区" in DEFAULT_USER_PROFILE


class TestGetGuidanceForTools:
    """get_guidance_for_tools 辅助函数测试"""
    
    def test_get_guidance_with_memory(self):
        """测试包含 memory 工具时的指导"""
        from agent.context.prompt_templates import get_guidance_for_tools
        result = get_guidance_for_tools(["memory"])
        
        assert result is not None
        assert "Memory System" in result
        assert "Session Search" not in result
        assert "Skills System" not in result
    
    def test_get_guidance_with_all_tools(self):
        """测试包含所有工具时的指导"""
        from agent.context.prompt_templates import get_guidance_for_tools
        result = get_guidance_for_tools(["memory", "session_search", "skill_manage"])
        
        assert result is not None
        assert "Memory System" in result
        assert "Session Search" in result
        assert "Skills System" in result
    
    def test_get_guidance_with_no_tools(self):
        """测试没有工具时的指导"""
        from agent.context.prompt_templates import get_guidance_for_tools
        result = get_guidance_for_tools([])
        
        assert result == ""


class TestAllExports:
    """所有导出测试"""
    
    def test_all_exports_exist(self):
        """测试所有导出都存在"""
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
            get_guidance_for_tools,
        )
        
        # 所有常量都应该存在且非空
        assert AGENT_IDENTITY
        assert CAPABILITIES
        assert MEMORY_GUIDANCE
        assert SESSION_SEARCH_GUIDANCE
        assert SKILLS_GUIDANCE
        assert TOOL_USE_ENFORCEMENT
        assert MANDATORY_TOOL_USE
        assert ACT_DONT_ASK
        assert OPENAI_MODEL_EXECUTION_GUIDANCE
        assert THINK_TAG_INSTRUCTION
        assert DEFAULT_USER_PROFILE
        assert callable(get_guidance_for_tools)


# ═══════════════════════════════════════════════════════════════════════════════
# Length and Size Tests - 长度和大小测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestTemplateLengths:
    """模板长度测试"""
    
    def test_agent_identity_reasonable_length(self):
        """测试身份定义长度合理"""
        from agent.context.prompt_templates import AGENT_IDENTITY
        # 身份定义应该在 1000-5000 chars 之间
        assert 1000 < len(AGENT_IDENTITY) < 5000
    
    def test_capabilities_reasonable_length(self):
        """测试能力清单长度合理"""
        from agent.context.prompt_templates import CAPABILITIES
        # 能力清单应该在 500-3000 chars 之间
        assert 500 < len(CAPABILITIES) < 3000
    
    def test_memory_guidance_reasonable_length(self):
        """测试记忆指南长度合理"""
        from agent.context.prompt_templates import MEMORY_GUIDANCE
        # 记忆指南应该在 200-2000 chars 之间
        assert 200 < len(MEMORY_GUIDANCE) < 2000
    
    def test_default_user_profile_reasonable_length(self):
        """测试用户画像长度合理"""
        from agent.context.prompt_templates import DEFAULT_USER_PROFILE
        # 默认用户画像应该在 100-1000 chars 之间
        assert 100 < len(DEFAULT_USER_PROFILE) < 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])