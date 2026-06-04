#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A Client Implementation.

Provides client for connecting to A2A agents.
"""

# 🧠 Decision - 💾 Memory - A2A Client

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from common.logging_manager import get_decision_logger
from agent.a2a.models import AgentCard, Message, Part, Task, TextPart, TaskStatus

logger = get_decision_logger(__name__)


class A2AClient:
    """
    A2A Client for connecting to A2A agents.

    Usage:
        client = A2AClient("http://remote-agent:8003")
        card = await client.get_agent_card()
        if card:
            print(f"Connected to {card.name}")
    """

    def __init__(self, url: str, api_key: Optional[str] = None):
        """
        Initialize A2A client.

        Args:
            url: Base URL of the A2A agent (e.g., "http://localhost:8003")
            api_key: Optional API key for authentication
        """
        self._url = url.rstrip("/")
        self._api_key = api_key
        self._agent_card: Optional[AgentCard] = None

    @property
    def url(self) -> str:
        """Get base URL."""
        return self._url

    async def get_agent_card(self) -> Optional[AgentCard]:
        """
        Fetch and cache the Agent Card from the remote agent.

        Returns:
            AgentCard if successful, None otherwise
        """
        if self._agent_card:
            return self._agent_card

        try:
            import aiohttp
        except ImportError:
            logger.error("aiohttp is required for A2A client")
            return None

        url = f"{self._url}/.well-known/agent.json"
        headers = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self._agent_card = AgentCard.from_dict(data)
                        return self._agent_card
                    else:
                        logger.warning(f"Failed to get agent card: {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching agent card: {e}")
            return None

    async def send_task(
        self,
        message: str,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Optional[Task]:
        """
        Send a task to the remote agent.

        Args:
            message: Text message to send
            session_id: Optional session ID for context
            task_id: Optional existing task ID (for continuing a task)

        Returns:
            Task if successful, None otherwise
        """
        try:
            import aiohttp
        except ImportError:
            logger.error("aiohttp is required for A2A client")
            return None

        url = f"{self._url}/tasks/send"
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload = {
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": message}],
            }
        }
        if session_id:
            payload["sessionId"] = session_id
        if task_id:
            payload["taskId"] = task_id

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, json=payload, headers=headers, timeout=60
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        task_data = data.get("task", {})
                        return Task.from_dict(task_data)
                    else:
                        logger.warning(f"Failed to send task: {resp.status}")
                        return None
        except asyncio.TimeoutError:
            logger.error("Request timed out")
            return None
        except Exception as e:
            logger.error(f"Error sending task: {e}")
            return None

    async def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get task status.

        Args:
            task_id: ID of the task

        Returns:
            Task if found, None otherwise
        """
        try:
            import aiohttp
        except ImportError:
            logger.error("aiohttp is required for A2A client")
            return None

        url = f"{self._url}/tasks/{task_id}"
        headers = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        task_data = data.get("task", {})
                        return Task.from_dict(task_data)
                    else:
                        logger.warning(f"Failed to get task: {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"Error getting task: {e}")
            return None

    async def cancel_task(self, task_id: str) -> Optional[Task]:
        """
        Cancel a task.

        Args:
            task_id: ID of the task

        Returns:
            Updated Task if successful, None otherwise
        """
        try:
            import aiohttp
        except ImportError:
            logger.error("aiohttp is required for A2A client")
            return None

        url = f"{self._url}/tasks/{task_id}/cancel"
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        task_data = data.get("task", {})
                        return Task.from_dict(task_data)
                    else:
                        logger.warning(f"Failed to cancel task: {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"Error canceling task: {e}")
            return None

    async def send_task_stream(
        self,
        message: str,
        session_id: Optional[str] = None,
    ):
        """
        Send a task and stream results via SSE.

        Yields:
            Task events as they arrive

        Args:
            message: Text message to send
            session_id: Optional session ID

        Yields:
            Dict event data
        """
        try:
            import aiohttp
        except ImportError:
            logger.error("aiohttp is required for A2A client")
            return

        # First send the task
        task = await self.send_task(message, session_id)
        if not task:
            return

        # Then stream events
        url = f"{self._url}/tasks/{task.task_id}/events"
        headers = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=60) as resp:
                    async for line in resp.content:
                        line = line.decode("utf-8").strip()
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                yield data
                            except json.JSONDecodeError:
                                pass
        except Exception as e:
            logger.error(f"Error streaming task events: {e}")


class A2ABroker:
    """
    A2A Broker for multi-agent coordination.

    Discovers agents and routes tasks to appropriate agents based on their
    capabilities.
    """

    def __init__(self):
        self._agents: Dict[str, AgentCard] = {}
        self._clients: Dict[str, A2AClient] = {}

    def register_agent(self, url: str, card: AgentCard) -> None:
        """Register an agent by URL and card."""
        self._agents[url] = card
        self._clients[url] = A2AClient(url)

    async def discover_agent(self, url: str) -> Optional[AgentCard]:
        """Discover an agent by fetching its Agent Card."""
        client = A2AClient(url)
        card = await client.get_agent_card()
        if card:
            self._agents[url] = card
            self._clients[url] = client
        return card

    def find_agent_by_skill(self, skill_name: str) -> Optional[str]:
        """Find an agent URL that has a specific skill."""
        for url, card in self._agents.items():
            for skill in card.skills:
                if skill.name == skill_name:
                    return url
        return None

    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents."""
        return [
            {
                "url": url,
                "name": card.name,
                "description": card.description,
                "skills": [s.name for s in card.skills],
            }
            for url, card in self._agents.items()
        ]

    async def send_task_to_agent(
        self, agent_url: str, message: str, session_id: Optional[str] = None
    ) -> Optional[Task]:
        """Send a task to a specific agent."""
        client = self._clients.get(agent_url)
        if not client:
            client = A2AClient(agent_url)
            self._clients[agent_url] = client

        return await client.send_task(message, session_id)

    async def broadcast_task(
        self, message: str, target_skills: Optional[List[str]] = None
    ) -> Dict[str, Task]:
        """
        Broadcast a task to all matching agents.

        Args:
            message: Task message
            target_skills: Filter agents by these skills

        Returns:
            Dict mapping agent URL to Task result
        """
        results = {}

        for url, card in self._agents.items():
            # Filter by skills if specified
            if target_skills:
                agent_skills = {s.name for s in card.skills}
                if not any(s in agent_skills for s in target_skills):
                    continue

            client = self._clients.get(url)
            if client:
                task = await client.send_task(message)
                if task:
                    results[url] = task

        return results
