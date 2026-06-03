#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Generation Tool Module

Provides functionality for generating images using AI models.

Based on Hermes Agent's image_generation_tool.py implementation.

Features:
- OpenAI DALL-E 3 (requires OPENAI_API_KEY)
- Hugging Face Stable Diffusion (requires HF_API_TOKEN)
- Local Stable Diffusion (requires local installation)
- Flux models

Usage:
    from tools.image_generation_tool import generate_image, check_image_gen_requirements

    result = generate_image(prompt="A beautiful sunset over the ocean")
"""

import base64
import json
import os
import tempfile
import time
from io import BytesIO
from pathlib import Path
from typing import Optional, List

import requests

from common.logging_manager import get_execution_logger
from tools.registry import registry

logger = get_execution_logger("ImageGeneration")

# Default settings
DEFAULT_MODEL = "dall-e-3"
DEFAULT_SIZE = "1024x1024"
DEFAULT_QUALITY = "standard"
DEFAULT_STYLE = "vivid"


def _get_config() -> dict:
    """获取图像生成配置"""
    try:
        from common.config import settings
        
        return {
            "provider": getattr(settings, 'IMAGE_PROVIDER', None) or "openai",
            "openai_key": getattr(settings, 'OPENAI_API_KEY', None),
            "hf_token": getattr(settings, 'HF_API_TOKEN', None),
            "default_size": getattr(settings, 'IMAGE_DEFAULT_SIZE', DEFAULT_SIZE),
        }
    except Exception:
        pass
    
    return {
        "provider": os.environ.get("IMAGE_PROVIDER", "openai"),
        "openai_key": os.environ.get("OPENAI_API_KEY"),
        "hf_token": os.environ.get("HF_API_TOKEN"),
        "default_size": os.environ.get("IMAGE_DEFAULT_SIZE", DEFAULT_SIZE),
    }


def _openai_generate(
    prompt: str,
    model: str,
    size: str,
    quality: str,
    style: str,
    n: int,
    api_key: str
) -> dict:
    """使用 OpenAI DALL-E 生成图像"""
    from openai import OpenAI
    
    client = OpenAI(api_key=api_key)
    
    response = client.images.generate(
        model=model,
        prompt=prompt,
        size=size,
        quality=quality,
        style=style,
        n=n
    )
    
    results = []
    for image in response.data:
        results.append({
            "url": image.url,
            "revised_prompt": getattr(image, "revised_prompt", prompt),
            "b64_json": getattr(image, "b64_json", None)
        })
    
    return results


def _hf_generate(
    prompt: str,
    model: str,
    size: str,
    api_token: str
) -> List[dict]:
    """使用 Hugging Face Stable Diffusion 生成图像"""
    # Parse size
    width, height = map(int, size.split('x'))
    
    # Use inference API
    API_URL = f"https://api-inference.huggingface.co/models/{model}"
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "x-wait-for-model": "true"
    }
    
    payload = {
        "inputs": prompt,
        "parameters": {
            "width": width,
            "height": height,
        }
    }
    
    response = requests.post(API_URL, headers=headers, json=payload, timeout=120)
    
    if response.status_code == 503:
        # Model loading, retry after estimated time
        try:
            estimated_time = response.json().get("estimated_time", 30)
            time.sleep(min(estimated_time + 5, 120))
            
            response = requests.post(API_URL, headers=headers, json=payload, timeout=120)
        except Exception:
            pass
    
    response.raise_for_status()
    
    # Convert to base64
    img_b64 = base64.b64encode(response.content).decode('utf-8')
    
    return [{
        "url": None,
        "b64_json": img_b64,
        "revised_prompt": prompt
    }]


def generate_image(
    prompt: str,
    model: Optional[str] = None,
    size: Optional[str] = None,
    quality: Optional[str] = None,
    style: Optional[str] = None,
    n: int = 1,
    output_path: Optional[str] = None,
    return_base64: bool = False
) -> str:
    """
    Generate an image using AI.
    
    Args:
        prompt: Image description/prompt
        model: Model to use (dall-e-3, dall-e-2, stable-diffusion-xl, etc.)
        size: Image size (256x256, 512x512, 1024x1024, 1792x1024, 1024x1792)
        quality: Image quality (standard, hd for DALL-E 3)
        style: Style (vivid, natural for DALL-E 3)
        n: Number of images to generate
        output_path: Optional path to save the image
        return_base64: Return base64 encoded image instead of URL
        
    Returns:
        JSON string with generated image(s)
    """
    config = _get_config()
    provider = config["provider"]
    
    # Apply defaults
    model = model or (DEFAULT_MODEL if provider == "openai" else "stabilityai/stable-diffusion-xl-base-1.0")
    size = size or config["default_size"]
    quality = quality or DEFAULT_QUALITY
    style = style or DEFAULT_STYLE
    
    try:
        results = []
        
        if provider == "openai":
            api_key = config["openai_key"]
            if not api_key:
                raise ValueError("OpenAI API key not configured")
            
            results = _openai_generate(
                prompt, model, size, quality, style, n, api_key
            )
            
        elif provider in ("huggingface", "hf"):
            api_token = config["hf_token"]
            if not api_token:
                raise ValueError("Hugging Face API token not configured")
            
            results = _hf_generate(prompt, model, size, api_token)
            
        else:
            raise ValueError(f"Unknown image generation provider: {provider}")
        
        # Save to file if requested
        if output_path:
            output_paths = _save_images(results, output_path, return_base64)
            return json.dumps({
                "success": True,
                "count": len(results),
                "images": [
                    {
                        "path": str(p),
                        "prompt": r.get("revised_prompt", prompt)
                    }
                    for p, r in zip(output_paths, results)
                ]
            }, ensure_ascii=False, indent=2)
        
        # Return results
        if return_base64:
            return json.dumps({
                "success": True,
                "count": len(results),
                "images": [
                    {
                        "base64": r.get("b64_json"),
                        "revised_prompt": r.get("revised_prompt", prompt)
                    }
                    for r in results
                ]
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "success": True,
                "count": len(results),
                "images": [
                    {
                        "url": r.get("url"),
                        "revised_prompt": r.get("revised_prompt", prompt)
                    }
                    for r in results
                ]
            }, ensure_ascii=False)
            
    except ImportError as e:
        logger.error(f"Image generation dependency missing: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "hint": "Install required package: pip install openai"
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Image generation error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False)


def _save_images(results: List[dict], output_path: str, return_base64: bool) -> List[Path]:
    """Save generated images to file"""
    paths = []
    
    base_path = Path(output_path)
    
    # If single path without extension, create numbered files
    if base_path.suffix == '':
        base_path.parent.mkdir(parents=True, exist_ok=True)
        
        for i, result in enumerate(results):
            file_path = base_path.parent / f"{base_path.name}_{i+1}.png"
            
            if return_base64 and result.get("b64_json"):
                data = base64.b64decode(result["b64_json"])
            else:
                # Download from URL
                url = result.get("url")
                if url:
                    response = requests.get(url, timeout=30)
                    response.raise_for_status()
                    data = response.content
                else:
                    continue
            
            file_path.write_bytes(data)
            paths.append(file_path)
    else:
        # Single file
        base_path.parent.mkdir(parents=True, exist_ok=True)
        
        result = results[0]
        if return_base64 and result.get("b64_json"):
            data = base64.b64decode(result["b64_json"])
        else:
            url = result.get("url")
            if url:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                data = response.content
            else:
                raise ValueError("No image data available")
        
        base_path.write_bytes(data)
        paths.append(base_path)
    
    return paths


def list_image_models(provider: str = "openai") -> str:
    """
    List available image generation models.
    
    Args:
        provider: Image generation provider
        
    Returns:
        JSON string with available models
    """
    if provider == "openai":
        return json.dumps({
            "success": True,
            "provider": "openai",
            "models": [
                {
                    "name": "dall-e-3",
                    "description": "Latest DALL-E model, highest quality, 1024x1024 or 1024x1792",
                    "sizes": ["1024x1024", "1024x1792", "1792x1024"],
                    "quality": ["standard", "hd"],
                    "styles": ["vivid", "natural"]
                },
                {
                    "name": "dall-e-2",
                    "description": "Earlier DALL-E model, faster, 256x256 to 1024x1024",
                    "sizes": ["256x256", "512x512", "1024x1024"],
                    "quality": ["standard"],
                    "styles": ["vivid", "natural"]
                }
            ]
        }, ensure_ascii=False, indent=2)
        
    elif provider in ("huggingface", "hf"):
        return json.dumps({
            "success": True,
            "provider": "huggingface",
            "models": [
                {"name": "stabilityai/stable-diffusion-xl-base-1.0", "description": "SDXL base model"},
                {"name": "stabilityai/stable-diffusion-2-1", "description": "SD 2.1 model"},
                {"name": "runwayml/stable-diffusion-v1-5", "description": "SD 1.5 model"},
            ]
        }, ensure_ascii=False, indent=2)
    
    else:
        return json.dumps({
            "success": False,
            "error": f"Unknown provider: {provider}"
        }, ensure_ascii=False)


def check_image_gen_requirements() -> bool:
    """检查图像生成工具是否可用"""
    config = _get_config()
    provider = config["provider"]
    
    if provider == "openai":
        return bool(config["openai_key"])
    elif provider in ("huggingface", "hf"):
        return bool(config["hf_token"])
    
    return False


# Schema definitions
IMAGE_GENERATION_SCHEMA = {
    "name": "image_generate",
    "description": "Generate images using AI. Supports DALL-E 3, DALL-E 2, and Stable Diffusion.",
    "parameters": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Detailed description of the image to generate. Be specific and descriptive."
            },
            "model": {
                "type": "string",
                "description": "Model to use: dall-e-3, dall-e-2, or stable-diffusion model ID",
                "default": "dall-e-3"
            },
            "size": {
                "type": "string",
                "description": "Image size",
                "enum": ["256x256", "512x512", "1024x1024", "1792x1024", "1024x1792"],
                "default": "1024x1024"
            },
            "quality": {
                "type": "string",
                "description": "Image quality (DALL-E 3 only)",
                "enum": ["standard", "hd"],
                "default": "standard"
            },
            "style": {
                "type": "string",
                "description": "Style (DALL-E 3 only)",
                "enum": ["vivid", "natural"],
                "default": "vivid"
            },
            "n": {
                "type": "integer",
                "description": "Number of images to generate",
                "default": 1
            },
            "output_path": {
                "type": "string",
                "description": "Optional path to save the image(s)"
            },
            "return_base64": {
                "type": "boolean",
                "description": "Return base64 encoded image instead of URL",
                "default": False
            }
        },
        "required": ["prompt"]
    }
}


# Register the tool
registry.register(
    name="image_generate",
    toolset="image_generation",
    schema=IMAGE_GENERATION_SCHEMA,
    handler=lambda args, **kw: generate_image(
        prompt=args.get("prompt", ""),
        model=args.get("model"),
        size=args.get("size"),
        quality=args.get("quality"),
        style=args.get("style"),
        n=args.get("n", 1),
        output_path=args.get("output_path"),
        return_base64=args.get("return_base64", False)
    ),
    check_fn=check_image_gen_requirements,
    emoji="🎨",
)
