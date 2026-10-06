"""In-memory asynchronous message queue for agent communication."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class MessageQueue:
    """Route copied messages to named agent inboxes and retain an audit log."""

    def __init__(self):
        self.queues: dict[str, asyncio.Queue[dict[str, Any]]] = {}
        self.message_log: list[dict[str, Any]] = []

    def register_agent(self, agent_name: str) -> bool:
        """Create an inbox once; return whether a new inbox was created."""
        if not isinstance(agent_name, str) or not agent_name.strip():
            raise ValueError("agent_name must be a non-empty string")
        if agent_name in self.queues:
            return False
        self.queues[agent_name] = asyncio.Queue()
        return True

    async def send_message(
        self,
        from_agent: str,
        to_agent: str,
        message: Mapping[str, Any],
    ) -> str:
        """Queue a copied message with immutable routing metadata for callers."""
        if not isinstance(from_agent, str) or not from_agent.strip():
            raise ValueError("from_agent must be a non-empty string")
        if not isinstance(to_agent, str) or not to_agent.strip():
            raise ValueError("to_agent must be a non-empty string")
        if not isinstance(message, Mapping):
            raise ValueError("message must be an object")
        if to_agent not in self.queues:
            raise ValueError(f"Agent {to_agent} is not registered")

        queued = dict(message)
        queued.update({
            "from": from_agent,
            "to": to_agent,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "id": str(uuid4()),
        })
        self.message_log.append(queued.copy())
        await self.queues[to_agent].put(queued)
        return queued["id"]

    async def receive_message(self, agent_name: str, timeout: float | None = 30) -> dict[str, Any]:
        """Receive the next message, raising ``TimeoutError`` on expiry."""
        if not isinstance(agent_name, str) or not agent_name.strip():
            raise ValueError("agent_name must be a non-empty string")
        if agent_name not in self.queues:
            raise ValueError(f"Agent {agent_name} is not registered")
        if timeout is not None and timeout <= 0:
            raise ValueError("timeout must be greater than zero or None")
        try:
            if timeout is None:
                return await self.queues[agent_name].get()
            return await asyncio.wait_for(self.queues[agent_name].get(), timeout=timeout)
        except asyncio.TimeoutError as exc:
            raise TimeoutError(f"No message for {agent_name} within {timeout}s") from exc

    def get_message_log(self, agent_name: str | None = None) -> list[dict[str, Any]]:
        """Return copied message-log entries, optionally filtered by agent."""
        if agent_name is not None and (not isinstance(agent_name, str) or not agent_name.strip()):
            raise ValueError("agent_name must be a non-empty string when provided")
        messages = self.message_log if agent_name is None else [
            message for message in self.message_log
            if message["from"] == agent_name or message["to"] == agent_name
        ]
        return [message.copy() for message in messages]
