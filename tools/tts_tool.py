#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Text-to-Speech Tool Module

Provides functionality for converting text to speech with multiple providers.

Based on Hermes Agent's tts_tool.py implementation.

Features:
- Edge TTS (default, free, no API key): Microsoft Edge neural voices
- OpenAI TTS: Good quality, needs OPENAI_API_KEY
- ElevenLabs (premium): High-quality voices, needs ELEVENLABS_API_KEY

Usage:
    from tools.tts_tool import text_to_speech, check_tts_requirements

    result = text_to_speech(text="Hello world")
"""

import base64
import io
import json
import os
import tempfile
from pathlib import Path
from typing import Optional

from common.logging_manager import get_execution_logger
from tools.registry import registry

logger = get_execution_logger("TTS")

# Default TTS settings
DEFAULT_PROVIDER = "edge"
DEFAULT_VOICE = "en-US-AriaNeural"
DEFAULT_MODEL = "tts-1"
DEFAULT_SPEED = 1.0


def _get_config() -> dict:
    """获取 TTS 配置"""
    try:
        from common.config import settings
        
        return {
            "provider": getattr(settings, 'TTS_PROVIDER', None) or DEFAULT_PROVIDER,
            "api_key": getattr(settings, 'OPENAI_API_KEY', None),
            "elevenlabs_key": getattr(settings, 'ELEVENLABS_API_KEY', None),
        }
    except Exception:
        pass
    
    return {
        "provider": os.environ.get("TTS_PROVIDER", DEFAULT_PROVIDER),
        "api_key": os.environ.get("OPENAI_API_KEY"),
        "elevenlabs_key": os.environ.get("ELEVENLABS_API_KEY"),
    }


def _edge_tts(text: str, voice: str, speed: float, output_format: str = "mp3") -> bytes:
    """使用 Edge TTS 生成语音"""
    try:
        import edge_tts
    except ImportError:
        raise ImportError("edge-tts not installed. Run: pip install edge-tts")
    
    output = io.BytesIO()
    
    async def generate():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output)
    
    import asyncio
    asyncio.run(generate())
    
    return output.getvalue()


def _openai_tts(text: str, voice: str, model: str, speed: float, api_key: str) -> bytes:
    """使用 OpenAI TTS 生成语音"""
    from openai import OpenAI
    
    client = OpenAI(api_key=api_key)
    
    response = client.audio.speech.create(
        model=model,
        voice=voice,
        input=text,
        speed=speed
    )
    
    return response.content


def _elevenlabs_tts(text: str, voice: str, api_key: str) -> bytes:
    """使用 ElevenLabs TTS 生成语音"""
    from elevenlabs.client import ElevenLabs
    
    client = ElevenLabs(api_key=api_key)
    
    response = client.text_to_speech.convert(
        voice_id=voice,
        text=text,
        model_id="eleven_monolingual_v1"
    )
    
    return b"".join(response)


def text_to_speech(
    text: str,
    voice: str = DEFAULT_VOICE,
    provider: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    speed: float = DEFAULT_SPEED,
    language: str = "en-US",
    output_format: str = "mp3"
) -> str:
    """
    Convert text to speech.
    
    Args:
        text: Text to convert to speech
        voice: Voice name (e.g., 'en-US-AriaNeural', 'alloy', 'elevenlabs_voice_id')
        provider: TTS provider (edge, openai, elevenlabs). Auto-detected if not specified.
        model: TTS model (tts-1, tts-1-hd, or custom)
        speed: Speech speed (0.25 - 4.0)
        language: Language code
        output_format: Output format (mp3, wav, opus)
        
    Returns:
        JSON string with audio data
    """
    config = _get_config()
    provider = provider or config["provider"] or DEFAULT_PROVIDER
    
    try:
        audio_data: bytes
        
        if provider == "edge":
            # Map language to Edge TTS voice if not specified
            if voice == DEFAULT_VOICE and language != "en-US":
                voice = _get_edge_voice_for_language(language)
            audio_data = _edge_tts(text, voice, speed, output_format)
            
        elif provider == "openai":
            api_key = config["api_key"]
            if not api_key:
                raise ValueError("OpenAI API key not configured")
            audio_data = _openai_tts(text, voice, model, speed, api_key)
            
        elif provider == "elevenlabs":
            api_key = config["elevenlabs_key"]
            if not api_key:
                raise ValueError("ElevenLabs API key not configured")
            audio_data = _elevenlabs_tts(text, voice, api_key)
            
        else:
            raise ValueError(f"Unknown TTS provider: {provider}")
        
        # Encode to base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # Estimate duration (rough estimate: ~150 words per minute)
        word_count = len(text.split())
        duration = (word_count / 150) * 60 / speed
        
        return json.dumps({
            "success": True,
            "provider": provider,
            "voice": voice,
            "audio_base64": audio_base64,
            "duration_seconds": round(duration, 1),
            "format": output_format,
            "size_bytes": len(audio_data)
        }, ensure_ascii=False)
        
    except ImportError as e:
        logger.error(f"TTS dependency missing: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "hint": "Install required package: pip install edge-tts"
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False)


def _get_edge_voice_for_language(language: str) -> str:
    """获取语言对应的 Edge TTS 声音"""
    voice_map = {
        "zh-CN": "zh-CN-XiaoxiaoNeural",
        "zh-TW": "zh-TW-HsiaoYuNeural",
        "ja-JP": "ja-JP-NanamiNeural",
        "ko-KR": "ko-KR-SunHiNeural",
        "fr-FR": "fr-FR-DeniseNeural",
        "de-DE": "de-DE-KatjaNeural",
        "es-ES": "es-ES-ElviraNeural",
        "it-IT": "it-IT-ElsaNeural",
        "pt-BR": "pt-BR-FranciscaNeural",
        "ru-RU": "ru-RU-DariyaNeural",
    }
    return voice_map.get(language, DEFAULT_VOICE)


def list_tts_voices(provider: str = "edge") -> str:
    """
    List available TTS voices.
    
    Args:
        provider: TTS provider
        
    Returns:
        JSON string with available voices
    """
    if provider == "edge":
        try:
            import edge_tts
            import asyncio
            
            voices = asyncio.run(edge_tts.list_voices())
            
            # Group by language
            grouped = {}
            for voice in voices:
                lang = voice["Locale"]
                if lang not in grouped:
                    grouped[lang] = []
                grouped[lang].append({
                    "name": voice["Name"],
                    "gender": voice["Gender"],
                    "short_name": voice["ShortName"]
                })
            
            return json.dumps({
                "success": True,
                "provider": "edge",
                "voices": grouped,
                "default": DEFAULT_VOICE
            }, ensure_ascii=False, indent=2)
            
        except ImportError:
            return json.dumps({
                "success": False,
                "error": "edge-tts not installed",
                "hint": "pip install edge-tts"
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False)
    
    elif provider == "openai":
        return json.dumps({
            "success": True,
            "provider": "openai",
            "voices": [
                {"name": "alloy", "description": "Neutral, balanced voice"},
                {"name": "echo", "description": "Male voice with lower pitch"},
                {"name": "fable", "description": "British accent voice"},
                {"name": "onyx", "description": "Deep male voice"},
                {"name": "nova", "description": "Female voice with higher pitch"},
                {"name": "shimmer", "description": "Female voice with medium pitch"}
            ],
            "default": "alloy"
        }, ensure_ascii=False, indent=2)
    
    else:
        return json.dumps({
            "success": False,
            "error": f"Unknown provider: {provider}"
        }, ensure_ascii=False)


def check_tts_requirements() -> bool:
    """检查 TTS 工具是否可用"""
    config = _get_config()
    provider = config["provider"] or DEFAULT_PROVIDER
    
    if provider == "edge":
        try:
            import edge_tts
            return True
        except ImportError:
            return False
    
    elif provider == "openai":
        return bool(config["api_key"])
    
    elif provider == "elevenlabs":
        return bool(config["elevenlabs_key"])
    
    return False


# Schema definitions
TTS_SCHEMA = {
    "name": "text_to_speech",
    "description": "Convert text to speech using AI. Supports multiple providers (Edge TTS, OpenAI, ElevenLabs).",
    "parameters": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to convert to speech"
            },
            "voice": {
                "type": "string",
                "description": "Voice name (Edge: 'en-US-AriaNeural', OpenAI: 'alloy', ElevenLabs: voice ID)",
                "default": "en-US-AriaNeural"
            },
            "provider": {
                "type": "string",
                "description": "TTS provider: edge (default, free), openai, elevenlabs",
                "enum": ["edge", "openai", "elevenlabs"]
            },
            "model": {
                "type": "string",
                "description": "TTS model (OpenAI: tts-1, tts-1-hd)",
                "default": "tts-1"
            },
            "speed": {
                "type": "number",
                "description": "Speech speed (0.25 - 4.0)",
                "default": 1.0
            },
            "language": {
                "type": "string",
                "description": "Language code for voice selection",
                "default": "en-US"
            },
            "output_format": {
                "type": "string",
                "description": "Output audio format",
                "enum": ["mp3", "wav", "opus"],
                "default": "mp3"
            }
        },
        "required": ["text"]
    }
}

LIST_VOICES_SCHEMA = {
    "name": "list_tts_voices",
    "description": "List available TTS voices for the specified provider.",
    "parameters": {
        "type": "object",
        "properties": {
            "provider": {
                "type": "string",
                "description": "TTS provider",
                "enum": ["edge", "openai", "elevenlabs"],
                "default": "edge"
            }
        },
        "required": []
    }
}


# Register tools
registry.register(
    name="text_to_speech",
    toolset="tts",
    schema=TTS_SCHEMA,
    handler=lambda args, **kw: text_to_speech(
        text=args.get("text", ""),
        voice=args.get("voice", DEFAULT_VOICE),
        provider=args.get("provider"),
        model=args.get("model", DEFAULT_MODEL),
        speed=args.get("speed", DEFAULT_SPEED),
        language=args.get("language", "en-US"),
        output_format=args.get("output_format", "mp3")
    ),
    check_fn=check_tts_requirements,
    emoji="🔊",
)

registry.register(
    name="list_tts_voices",
    toolset="tts",
    schema=LIST_VOICES_SCHEMA,
    handler=lambda args, **kw: list_tts_voices(
        provider=args.get("provider", "edge")
    ),
    check_fn=check_tts_requirements,
    emoji="🔊",
)
