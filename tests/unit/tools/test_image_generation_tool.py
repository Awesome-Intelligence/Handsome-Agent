#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the image_generation_tool module.

Tests cover image generation functionality including:
- Image generation
- Model listing
- Provider support
"""

import pytest
import json
from unittest.mock import patch, MagicMock


class TestGenerateImage:
    """Test suite for generate_image."""

    def test_generate_image_returns_json(self):
        """Test that generate_image returns valid JSON."""
        from tools.image_generation_tool import generate_image
        
        # Without API keys, should return error but valid JSON
        result = generate_image(prompt="A beautiful sunset")
        assert isinstance(result, str)
        
        data = json.loads(result)
        assert "success" in data
        assert isinstance(data["success"], bool)

    def test_generate_with_model(self):
        """Test image generation with custom model."""
        from tools.image_generation_tool import generate_image
        
        result = generate_image(prompt="A cat", model="dall-e-3")
        data = json.loads(result)
        
        assert "success" in data

    def test_generate_with_size(self):
        """Test image generation with custom size."""
        from tools.image_generation_tool import generate_image
        
        result = generate_image(prompt="A cat", size="512x512")
        data = json.loads(result)
        
        assert "success" in data

    def test_generate_multiple(self):
        """Test generating multiple images."""
        from tools.image_generation_tool import generate_image
        
        result = generate_image(prompt="A cat", n=2)
        data = json.loads(result)
        
        assert "success" in data


class TestListImageModels:
    """Test suite for list_image_models."""

    def test_list_openai_models(self):
        """Test listing OpenAI image models."""
        from tools.image_generation_tool import list_image_models
        
        result = list_image_models(provider="openai")
        assert isinstance(result, str)
        
        data = json.loads(result)
        assert data["success"] is True
        assert "models" in data
        assert len(data["models"]) >= 2

    def test_list_hf_models(self):
        """Test listing Hugging Face models."""
        from tools.image_generation_tool import list_image_models
        
        result = list_image_models(provider="huggingface")
        assert isinstance(result, str)
        
        data = json.loads(result)
        assert data["success"] is True

    def test_list_unknown_provider(self):
        """Test listing models for unknown provider."""
        from tools.image_generation_tool import list_image_models
        
        result = list_image_models(provider="unknown")
        data = json.loads(result)
        
        assert data["success"] is False


class TestImageGenerationConfig:
    """Test image generation configuration."""

    def test_get_config(self):
        """Test getting image generation config."""
        from tools.image_generation_tool import _get_config
        
        config = _get_config()
        assert isinstance(config, dict)
        assert "provider" in config


class TestImageGenerationRegistry:
    """Test tool registry integration."""

    def test_tools_registered(self):
        """Test that image generation tools are registered."""
        from tools.registry import registry
        
        tool = registry.get("image_generate")
        assert tool is not None, "Tool image_generate should be registered"

    def test_tool_has_handler(self):
        """Test that tool has handler."""
        from tools.registry import registry
        
        tool = registry.get("image_generate")
        assert tool.handler is not None


class TestCheckImageGenRequirements:
    """Test requirement checking."""

    def test_check_image_gen_requirements(self):
        """Test image generation requirements check."""
        from tools.image_generation_tool import check_image_gen_requirements
        
        result = check_image_gen_requirements()
        assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
