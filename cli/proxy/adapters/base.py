#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base Adapter - Base class for upstream adapters.

🚪 Access - 💬 CLI - 适配器基类
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseAdapter(ABC):
    """Abstract base class for upstream adapters."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """Initialize adapter.

        Args:
            api_key: API key for authentication
            base_url: Base URL for API
        """
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    def get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for the request.

        Returns:
            Dict of headers
        """
        pass

    @abstractmethod
    def transform_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Transform request body.

        Args:
            request: Original request dict

        Returns:
            Transformed request dict
        """
        pass

    @abstractmethod
    def transform_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Transform response body.

        Args:
            response: Original response dict

        Returns:
            Transformed response dict
        """
        pass

    def prepare_request(self, request: Dict[str, Any]) -> tuple[Dict[str, str], Dict[str, Any]]:
        """Prepare request headers and body.

        Args:
            request: Original request dict

        Returns:
            Tuple of (headers, body)
        """
        headers = self.get_headers()
        body = self.transform_request(request)
        return headers, body


if __name__ == "__main__":
    print("Base adapter class for proxy")