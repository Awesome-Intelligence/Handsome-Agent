#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proxy Adapters - Upstream adapters for proxy.

🚪 Access - 💬 CLI - 代理适配器
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class UpstreamAdapter(ABC):
    """Base class for upstream adapters."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize adapter.

        Args:
            api_key: API key for authentication
        """
        self.api_key = api_key

    @abstractmethod
    def get_headers(self) -> Dict[str, str]:
        """Get headers for upstream request.

        Returns:
            Headers dict
        """
        pass

    @abstractmethod
    def transform_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Transform request before sending to upstream.

        Args:
            request: Original request dict

        Returns:
            Transformed request dict
        """
        pass

    @abstractmethod
    def transform_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Transform response from upstream.

        Args:
            response: Upstream response dict

        Returns:
            Transformed response dict
        """
        pass


class OpenAIAdapter(UpstreamAdapter):
    """Adapter for OpenAI API."""

    def get_headers(self) -> Dict[str, str]:
        """Get headers for OpenAI request."""
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def transform_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Transform request for OpenAI."""
        return request

    def transform_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Transform response from OpenAI."""
        return response


class AnthropicAdapter(UpstreamAdapter):
    """Adapter for Anthropic API."""

    def get_headers(self) -> Dict[str, str]:
        """Get headers for Anthropic request."""
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        return headers

    def transform_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Transform request for Anthropic."""
        # Anthropic uses 'messages' instead of 'prompt'
        return request

    def transform_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Transform response from Anthropic."""
        return response


def get_adapter(provider: str, api_key: Optional[str] = None) -> UpstreamAdapter:
    """Get adapter for a provider.

    Args:
        provider: Provider name
        api_key: API key

    Returns:
        UpstreamAdapter instance
    """
    adapters = {
        "openai": OpenAIAdapter,
        "anthropic": AnthropicAdapter,
    }

    adapter_class = adapters.get(provider.lower())
    if adapter_class:
        return adapter_class(api_key=api_key)

    return OpenAIAdapter(api_key=api_key)


__all__ = ["UpstreamAdapter", "OpenAIAdapter", "AnthropicAdapter", "get_adapter"]