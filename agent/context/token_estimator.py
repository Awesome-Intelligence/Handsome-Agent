#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token Estimator Module

Provides token estimation for LLM context management:
- Message token counting
- Request token counting (messages + system prompt + tools)
- Model context length lookup
- Token-based budget calculations

Inspired by Hermes Agent's model_metadata.py implementation.

Import chain:
    agent/context/token_estimator.py  (this file)
           ^
    agent/context/context_compressor.py
           ^
    agent/rails/context_compression_rail.py
"""

import os
import re
from typing import Any, Dict, List, Optional, Tuple

from common.logging_manager import get_decision_logger
from common.config import DEFAULT_COMPRESSION_THRESHOLD, DEFAULT_SUMMARY_RATIO

logger = get_decision_logger(__name__, sublayer="context")

_CHARS_PER_TOKEN = 4
_IMAGE_TOKEN_ESTIMATE = 1600
_IMAGE_CHAR_EQUIVALENT = _IMAGE_TOKEN_ESTIMATE * _CHARS_PER_TOKEN
_MINIMUM_CONTEXT_LENGTH = 8000


MODEL_CONTEXT_LENGTHS = {
    "gpt-4": 8192,
    "gpt-4-0314": 8192,
    "gpt-4-0613": 8192,
    "gpt-4-32k": 32768,
    "gpt-4-32k-0314": 32768,
    "gpt-4-32k-0613": 32768,
    "gpt-4-turbo": 128000,
    "gpt-4-turbo-2024-04-09": 128000,
    "gpt-4o": 128000,
    "gpt-4o-2024-05-13": 128000,
    "gpt-4o-mini": 128000,
    "gpt-4o-mini-2024-07-18": 128000,
    "gpt-3.5-turbo": 16385,
    "gpt-3.5-turbo-0301": 16385,
    "gpt-3.5-turbo-0613": 16385,
    "gpt-3.5-turbo-16k": 16385,
    "claude-3-opus": 200000,
    "claude-3-opus-20240229": 200000,
    "claude-3-sonnet": 200000,
    "claude-3-sonnet-20240229": 200000,
    "claude-3-haiku": 200000,
    "claude-3-haiku-20240307": 200000,
    "claude-3.5-sonnet": 200000,
    "claude-3.5-sonnet-20240620": 200000,
    "claude-3.5-sonnet-20241022": 200000,
    "claude-3.5-haiku": 200000,
    "claude-3.5-haiku-20241022": 200000,
    "claude-2": 100000,
    "claude-2-20230607": 100000,
    "claude-2.1": 100000,
    "claude-2.2": 100000,
    "gemini-1.5-pro": 128000,
    "gemini-1.5-flash": 128000,
    "gemini-1.5-pro-latest": 128000,
    "gemini-1.5-flash-latest": 128000,
    "gemini-1.0-pro": 32768,
    "gemini-1.0-pro-latest": 32768,
    "gemini-1.0-pro-001": 32768,
    "gemini-pro": 32768,
    "mistral-large": 32000,
    "mistral-medium": 32000,
    "mistral-small": 32000,
    "mistral-nemo": 128000,
    "mistral-7b": 32000,
    "mixtral-8x7b": 32000,
    "mixtral-8x22b": 64000,
    "llama-3-8b": 8192,
    "llama-3-70b": 8192,
    "llama-3.1-8b": 128000,
    "llama-3.1-70b": 128000,
    "llama-3.1-405b": 128000,
    "llama-2-70b": 4096,
    "llama-2-13b": 4096,
    "llama-2-7b": 4096,
    "command-r": 128000,
    "command-r-plus": 128000,
    "command": 4096,
    "command-light": 4096,
    "cohere": 4096,
}


def get_model_context_length(
    model: str,
    base_url: str = "",
    api_key: str = "",
    config_context_length: Optional[int] = None,
    provider: str = "",
) -> int:
    """Get the context length for a model.
    
    Args:
        model: Model name (e.g., 'gpt-4', 'claude-3-opus')
        base_url: Base URL for the API (for custom providers)
        api_key: API key (may be used for live lookup)
        config_context_length: Override from config file
        provider: Provider name (e.g., 'openai', 'anthropic')
    
    Returns:
        Context length in tokens
    """
    if config_context_length is not None and config_context_length > 0:
        return config_context_length

    model_lower = model.lower().strip()

    if model_lower in MODEL_CONTEXT_LENGTHS:
        return MODEL_CONTEXT_LENGTHS[model_lower]

    for known_model, context_length in MODEL_CONTEXT_LENGTHS.items():
        if known_model in model_lower or model_lower in known_model:
            return context_length

    if "claude" in model_lower:
        return 200000
    if "gpt-4" in model_lower:
        return 128000 if "128k" in model_lower else 8192
    if "gpt-3.5" in model_lower:
        return 16385
    if "gemini" in model_lower:
        return 128000
    if "llama" in model_lower or "llm" in model_lower:
        return 4096
    if "mistral" in model_lower:
        return 32000
    if "mixtral" in model_lower:
        return 32000
    if "command" in model_lower:
        return 128000

    logger.debug("Unknown model, using default context length")
    return _MINIMUM_CONTEXT_LENGTH


def get_model_family(model: str) -> str:
    """Get the model family for token estimation heuristics."""
    model_lower = model.lower()
    
    if "claude" in model_lower:
        return "anthropic"
    if "gpt-4" in model_lower:
        return "openai"
    if "gpt-3.5" in model_lower:
        return "openai"
    if "gemini" in model_lower:
        return "google"
    if "mistral" in model_lower or "mixtral" in model_lower:
        return "mistral"
    if "llama" in model_lower:
        return "meta"
    if "command" in model_lower:
        return "cohere"
    
    return "unknown"


def estimate_tokens(text: str) -> int:
    """Estimate token count for a text string.
    
    Uses char/4 heuristic for rough estimation.
    
    Args:
        text: Input text
    
    Returns:
        Estimated token count
    """
    if not text:
        return 0
    return max(1, len(text) // _CHARS_PER_TOKEN)


def _content_length_for_budget(raw_content: Any) -> int:
    """Return effective char-length of message content for token budgeting."""
    if isinstance(raw_content, str):
        return len(raw_content)
    if not isinstance(raw_content, list):
        return len(str(raw_content or ""))

    total = 0
    for p in raw_content:
        if isinstance(p, str):
            total += len(p)
            continue
        if not isinstance(p, dict):
            total += len(str(p))
            continue
        ptype = p.get("type")
        if ptype in {"image_url", "input_image", "image"}:
            total += _IMAGE_CHAR_EQUIVALENT
        else:
            total += len(p.get("text", "") or "")
    return total


def estimate_message_tokens(message: Dict[str, Any]) -> int:
    """Estimate token count for a single message.
    
    Includes:
    - Role overhead (~4 tokens)
    - Content tokens
    - Tool call arguments if present
    
    Args:
        message: Message dict with 'role', 'content', optionally 'tool_calls'
    
    Returns:
        Estimated token count
    """
    tokens = 4

    content = message.get("content") or ""
    tokens += _content_length_for_budget(content) // _CHARS_PER_TOKEN

    tool_calls = message.get("tool_calls")
    if tool_calls:
        for tc in (tool_calls if isinstance(tool_calls, list) else [tool_calls]):
            if isinstance(tc, dict):
                fn = tc.get("function", {})
                args = fn.get("arguments", "")
                if isinstance(args, str):
                    tokens += len(args) // _CHARS_PER_TOKEN
                else:
                    tokens += len(str(args)) // _CHARS_PER_TOKEN

    tool_call_id = message.get("tool_call_id")
    if tool_call_id:
        tokens += 3

    name = message.get("name")
    if name:
        tokens += len(name) // _CHARS_PER_TOKEN + 1

    return tokens


def estimate_messages_tokens_rough(messages: List[Dict[str, Any]]) -> int:
    """Rough token estimation for a list of messages.
    
    Used for quick threshold checks without precise counting.
    
    Args:
        messages: List of message dicts
    
    Returns:
        Estimated total token count
    """
    if not messages:
        return 0
    
    total = 0
    for msg in messages:
        total += estimate_message_tokens(msg)
    
    return total


def estimate_tool_schemas_tokens(tool_schemas: Optional[List[Dict[str, Any]]]) -> int:
    """Estimate tokens for tool schemas.
    
    Tool schemas are sent with every request, so we need to
    account for their size in threshold calculations.
    
    Args:
        tool_schemas: List of tool schema dicts
    
    Returns:
        Estimated token count for all tool schemas
    """
    if not tool_schemas:
        return 0
    
    total = 0
    for schema in tool_schemas:
        schema_str = str(schema)
        total += len(schema_str) // _CHARS_PER_TOKEN + 10

    overhead = 50
    return total + overhead


def estimate_system_prompt_tokens(system_prompt: str) -> int:
    """Estimate tokens for system prompt.
    
    Args:
        system_prompt: System prompt text
    
    Returns:
        Estimated token count
    """
    if not system_prompt:
        return 0
    
    tokens = len(system_prompt) // _CHARS_PER_TOKEN

    overhead = 10
    return tokens + overhead


def estimate_request_tokens_rough(
    messages: List[Dict[str, Any]],
    system_prompt: str = "",
    tool_schemas: Optional[List[Dict[str, Any]]] = None,
) -> int:
    """Estimate total tokens for a complete API request.
    
    Includes messages, system prompt, and tool schemas.
    This is what should be compared against context limits.
    
    Args:
        messages: List of message dicts
        system_prompt: System prompt text
        tool_schemas: List of tool schema dicts
    
    Returns:
        Estimated total token count
    """
    tokens = estimate_messages_tokens_rough(messages)
    
    tokens += estimate_system_prompt_tokens(system_prompt)
    
    tokens += estimate_tool_schemas_tokens(tool_schemas)
    
    return tokens


def calculate_compression_threshold(
    model: str,
    threshold_percent: float = DEFAULT_COMPRESSION_THRESHOLD,
    config_context_length: Optional[int] = None,
) -> int:
    """Calculate the token threshold for triggering compression.
    
    Args:
        model: Model name
        threshold_percent: Percentage of context length (0.0 to 1.0)
        config_context_length: Override from config file
    
    Returns:
        Token count threshold
    """
    context_length = get_model_context_length(model, config_context_length=config_context_length)
    
    threshold = int(context_length * threshold_percent)
    
    threshold = max(threshold, _MINIMUM_CONTEXT_LENGTH)
    
    return threshold


def calculate_tail_token_budget(
    model: str,
    summary_target_ratio: float = DEFAULT_SUMMARY_RATIO,
    threshold_tokens: Optional[int] = None,
) -> int:
    """Calculate the token budget for the protected tail region.
    
    Args:
        model: Model name
        summary_target_ratio: Percentage of threshold for tail budget
        threshold_tokens: Optional override threshold
    
    Returns:
        Token budget for tail protection
    """
    if threshold_tokens is not None:
        return int(threshold_tokens * summary_target_ratio)
    
    context_length = get_model_context_length(model)
    return int(context_length * summary_target_ratio * 0.5)


def calculate_summary_budget(
    content_tokens: int,
    context_length: int,
    max_summary_tokens: int = 4000,
    summary_ratio: float = 0.20,
) -> int:
    """Calculate the token budget for summarization.
    
    Args:
        content_tokens: Estimated tokens in content to summarize
        context_length: Model context length
        max_summary_tokens: Absolute ceiling for summary
        summary_ratio: Ratio of content to allocate for summary
    
    Returns:
        Token budget for summary generation
    """
    budget = int(content_tokens * summary_ratio)
    
    context_ceiling = int(context_length * 0.05)
    
    budget = min(budget, context_ceiling)
    
    budget = min(budget, max_summary_tokens)
    
    budget = max(budget, 200)
    
    return budget


def estimate_image_tokens(image_count: int, detail: str = "auto") -> int:
    """Estimate tokens for image inputs.
    
    Args:
        image_count: Number of images in the request
        detail: Vision detail level ('low', 'high', 'auto')
    
    Returns:
        Estimated token count for all images
    """
    if detail == "low":
        return image_count * 85
    elif detail == "high":
        return image_count * 1700
    else:
        return image_count * 850


def _messages_to_text_for_counting(messages: List[Dict[str, Any]]) -> str:
    """Convert messages to text for token counting utilities."""
    parts = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        
        if isinstance(content, list):
            text_parts = []
            for p in content:
                if isinstance(p, dict):
                    text = p.get("text", "")
                    if text:
                        text_parts.append(text)
                elif isinstance(p, str):
                    text_parts.append(p)
            content = " ".join(text_parts)
        
        parts.append(f"{role}: {content}")
    
    return "\n".join(parts)


class TokenBudget:
    """Token budget tracker for context management."""
    
    def __init__(
        self,
        model: str,
        threshold_percent: float = 0.50,
        summary_target_ratio: float = 0.20,
    ):
        self.model = model
        self.threshold_percent = threshold_percent
        self.summary_target_ratio = summary_target_ratio
        
        self.context_length = get_model_context_length(model)
        self.threshold_tokens = calculate_compression_threshold(
            model, threshold_percent
        )
        self.tail_token_budget = calculate_tail_token_budget(
            model, summary_target_ratio, self.threshold_tokens
        )
        self.max_summary_tokens = min(
            int(self.context_length * 0.05), 4000
        )
    
    def should_compress(self, prompt_tokens: int) -> bool:
        """Check if compression should be triggered."""
        return prompt_tokens >= self.threshold_tokens
    
    def estimate_request(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str = "",
        tool_schemas: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        """Estimate tokens for a complete request."""
        return estimate_request_tokens_rough(
            messages, system_prompt, tool_schemas
        )
    
    def remaining_budget(self, prompt_tokens: int) -> int:
        """Get remaining token budget before compression."""
        return max(0, self.threshold_tokens - prompt_tokens)
    
    def compression_ratio(self, prompt_tokens: int) -> float:
        """Get the ratio of used context (0.0 to 1.0+)."""
        if self.context_length == 0:
            return 0.0
        return prompt_tokens / self.context_length


def get_model_info(model: str) -> Dict[str, Any]:
    """Get comprehensive model information.
    
    Args:
        model: Model name
    
    Returns:
        Dict with context_length, family, and other info
    """
    return {
        "model": model,
        "context_length": get_model_context_length(model),
        "family": get_model_family(model),
        "supports_vision": "vision" in model.lower() or "gpt-4" in model.lower(),
        "supports_function_calling": True,
        "supports_streaming": True,
    }