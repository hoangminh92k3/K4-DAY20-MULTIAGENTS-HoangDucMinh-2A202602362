"""High-level orchestration for a coordinator and its specialised workers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from coordinator import Coordinator
from message_queue import MessageQueue


class MultiAgentSystem:
    """Run a request through data/code workers and, when available, evaluation."""

    def __init__(self, coordinator: Coordinator, workers: Iterable[Any] | None = None):
        self.coordinator = coordinator
        self.workers = list(workers) if workers is not None else list(coordinator.workers.values())

    async def process(self, user_input: str | Mapping[str, Any], timeout: float = 60) -> dict[str, Any]:
        """Process one request with an isolated queue so concurrent requests do not mix replies."""
        primary = Coordinator(
            self.coordinator.model,
            self.workers,
            message_queue=MessageQueue(),
            max_concurrent_tasks=self.coordinator.max_concurrent_tasks,
        )
        result = await primary.handle_request(user_input, timeout=timeout)
        if result["status"] != "success" or "evaluator_agent" not in primary.workers:
            return result

        evaluator = Coordinator(self.coordinator.model, [primary.workers["evaluator_agent"]], message_queue=MessageQueue())
        evaluation = await evaluator.handle_request(
            {"task_type": "evaluation", "parameters": {"data": result["data"], "code": result["code"]}},
            timeout=timeout,
        )
        if evaluation["status"] == "success":
            result["evaluation"] = evaluation["evaluation"]
        else:
            result["status"] = "partial_failure"
            result["errors"].extend(evaluation["errors"])
        return result
