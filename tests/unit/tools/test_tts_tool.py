#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the tts_tool module.

Tests cover text-to-speech functionality including:
- Text to speech conversion
- Voice listing
- Provider support
"""

import pytest
import json
from unittest.mock import patch, MagicMock


class TestTextToSpeech:
    """Test suite for text_to_speech."""

    def test_tts_returns_json(self):
        """Test that tts returns valid JSON structure."""
        from tools.tts_tool import text_to_speech
        
        # Without API keys, should return error but valid JSON
        result = text_to_speech(text="Hello world")
        assert isinstance(result, str)
        
        data = json.loads(result)
        assert "success" in data
        assert isinstance(data["success"], bool)

    def test_tts_with_voice(self):
        """Test tts with custom voice."""
        from tools.tts_tool import text_to_speech
        
        result = text_to_speech(text="Hello", voice="en-US-AriaNeural")
        data = json.loads(result)
        
        assert "success" in data

    def test_tts_with_language(self):
        """Test tts with language parameter."""
        from tools.tts_tool import text_to_speech
        
        result = text_to_speech(text="你好", language="zh-CN")
        data = json.loads(result)
        
        assert "success" in data


class TestListTTSVoices:
    """Test suite for list_tts_voices."""

    def test_list_voices_edge(self):
        """Test listing Edge TTS voices."""
        from tools.tts_tool import list_tts_voices
        
        result = list_tts_voices(provider="edge")
        assert isinstance(result, str)
        
        data = json.loads(result)
        assert "success" in data

    def test_list_voices_openai(self):
        """Test listing OpenAI voices."""
        from tools.tts_tool import list_tts_voices
        
        result = list_tts_voices(provider="openai")
        assert isinstance(result, str)
        
        data = json.loads(result)
        assert data["success"] is True
        assert "voices" in data

    def test_list_voices_unknown_provider(self):
        """Test listing voices with unknown provider."""
        from tools.tts_tool import list_tts_voices
        
        result = list_tts_voices(provider="unknown")
        data = json.loads(result)
        
        assert data["success"] is False


class TestGetEdgeVoiceForLanguage:
    """Test edge voice language mapping."""

    def test_chinese_voice(self):
        """Test Chinese voice mapping."""
        from tools.tts_tool import _get_edge_voice_for_language
        
        voice = _get_edge_voice_for_language("zh-CN")
        assert voice == "zh-CN-XiaoxiaoNeural"

    def test_japanese_voice(self):
        """Test Japanese voice mapping."""
        from tools.tts_tool import _get_edge_voice_for_language
        
        voice = _get_edge_voice_for_language("ja-JP")
        assert voice == "ja-JP-NanamiNeural"

    def test_default_voice(self):
        """Test default voice fallback."""
        from tools.tts_tool import _get_edge_voice_for_language, DEFAULT_VOICE
        
        voice = _get_edge_voice_for_language("unknown-lang")
        assert voice == DEFAULT_VOICE


class TestTTSConfig:
    """Test TTS configuration."""

    def test_get_config(self):
        """Test getting TTS config."""
        from tools.tts_tool import _get_config
        
        config = _get_config()
        assert isinstance(config, dict)
        assert "provider" in config


class TestTTSRegistry:
    """Test tool registry integration."""

    def test_tools_registered(self):
        """Test that all TTS tools are registered."""
        from tools.registry import registry
        
        expected_tools = ["text_to_speech", "list_tts_voices"]
        
        for tool_name in expected_tools:
            tool = registry.get(tool_name)
            assert tool is not None, f"Tool {tool_name} should be registered"

    def test_tools_have_handlers(self):
        """Test that all tools have handlers."""
        from tools.registry import registry
        
        tools = registry.get_by_toolset("tts")
        assert len(tools) >= 1
        
        for tool in tools:
            assert tool.handler is not None


class TestCheckTTSRequirements:
    """Test requirement checking."""

    def test_check_tts_requirements(self):
        """Test TTS requirements check."""
        from tools.tts_tool import check_tts_requirements
        
        result = check_tts_requirements()
        assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
