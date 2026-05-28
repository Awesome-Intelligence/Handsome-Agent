"""多媒体工具定义 - 图像生成和文本转语音"""
from tools.schema_registry import UnifiedToolSchema, ToolSource


MULTIMEDIA_TOOLS = [
    UnifiedToolSchema(
        name="image_generate",
        description="使用 AI 生成图像，支持多种风格",
        source=ToolSource.HERMES,
        source_name="image_generate",
        parameters={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "图像描述提示词"
                },
                "model": {
                    "type": "string",
                    "description": "图像生成模型: dalle-3, flux, stable-diffusion",
                    "default": "dalle-3"
                },
                "size": {
                    "type": "string",
                    "enum": ["256x256", "512x512", "1024x1024", "1792x1024", "1024x1792"],
                    "description": "图像尺寸",
                    "default": "1024x1024"
                },
                "style": {
                    "type": "string",
                    "enum": ["vivid", "natural", "none"],
                    "description": "风格",
                    "default": "vivid"
                },
                "quality": {
                    "type": "string",
                    "enum": ["standard", "hd"],
                    "description": "质量",
                    "default": "standard"
                },
                "n": {
                    "type": "integer",
                    "description": "生成数量",
                    "default": 1
                }
            },
            "required": ["prompt"]
        },
        returns={
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "revised_prompt": {"type": "string"}
            }
        },
        safety_level="low",
        category="multimedia",
    ),
    UnifiedToolSchema(
        name="text_to_speech",
        description="文本转语音，支持多种声音和语言",
        source=ToolSource.HERMES,
        source_name="text_to_speech",
        parameters={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "要转换的文本"
                },
                "voice": {
                    "type": "string",
                    "description": "声音名称",
                    "default": "alloy"
                },
                "model": {
                    "type": "string",
                    "enum": ["tts-1", "tts-1-hd", "edge-tts"],
                    "description": "TTS 模型",
                    "default": "tts-1"
                },
                "speed": {
                    "type": "number",
                    "description": "语速 (0.25 - 4.0)",
                    "default": 1.0
                },
                "language": {
                    "type": "string",
                    "description": "语言代码",
                    "default": "auto"
                },
                "output_format": {
                    "type": "string",
                    "enum": ["mp3", "wav", "opus"],
                    "description": "输出格式",
                    "default": "mp3"
                }
            },
            "required": ["text"]
        },
        returns={
            "type": "object",
            "properties": {
                "audio_base64": {"type": "string"},
                "duration_seconds": {"type": "number"}
            }
        },
        safety_level="low",
        category="multimedia",
    ),
    UnifiedToolSchema(
        name="vision_analyze",
        description="分析图像内容，提取信息",
        source=ToolSource.HERMES,
        source_name="vision_analyze",
        parameters={
            "type": "object",
            "properties": {
                "image": {
                    "type": "string",
                    "description": "图像 URL 或 base64"
                },
                "prompt": {
                    "type": "string",
                    "description": "分析提示词"
                },
                "detail": {
                    "type": "string",
                    "enum": ["low", "high", "auto"],
                    "description": "分析详细程度",
                    "default": "auto"
                }
            },
            "required": ["image", "prompt"]
        },
        returns={
            "type": "object",
            "properties": {
                "analysis": {"type": "string"}
            }
        },
        safety_level="low",
        category="multimedia",
    ),
]
