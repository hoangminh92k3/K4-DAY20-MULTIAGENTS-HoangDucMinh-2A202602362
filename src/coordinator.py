"""Coordinator for routing a user request to one or more worker agents.

Workers receive tasks through a message queue and post their correlated result
back to the coordinator inbox.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
import inspect
import json
import logging
from time import monotonic
from typing import Any

from message_queue import MessageQueue


class CoordinatorError(RuntimeError):
    """Base error raised when the coordinator cannot complete a request."""


class WorkerError(CoordinatorError):
    """A worker failed while handling a task."""


class ResourceExhaustedError(CoordinatorError):
    """The coordinator received more work than it is configured to accept."""


class Coordinator:
    """Analyse requests, dispatch them to workers, and combine their output."""

    def __init__(
        self,
        model: Any,
        worker_agents: Iterable[Any],
        message_queue: Any = None,
        max_concurrent_tasks: int | None = None,
    ):
        if max_concurrent_tasks is not None and max_concurrent_tasks < 1:
            raise ValueError("max_concurrent_tasks must be at least one")
        self.model = model
        self.workers = {agent.name: agent for agent in worker_agents}
        self.task_queue = message_queue if message_queue is not None else MessageQueue()
        self.max_concurrent_tasks = max_concurrent_tasks
        self.active_tasks: dict[str, dict[str, Any]] = {}
        self.logger = logging.getLogger("coordinator")

    def parse_request(self, user_input: str | Mapping[str, Any]) -> dict[str, Any]:
        """Ask the model for a JSON task description and validate its shape."""
        if isinstance(user_input, Mapping):
            parsed: Mapping[str, Any] = user_input
        else:
            if not isinstance(user_input, str) or not user_input.strip():
                raise ValueError("user_input must be a non-empty string or a mapping")

            prompt = f"""
Analyse the user request and return JSON only, with exactly these fields:
- task_type: one of data_analysis, code_generation, evaluation, complex
- parameters: an object containing the extracted parameters
- priority: low, normal, or high

User request: {user_input}
"""
            response = self.model.invoke(prompt)
            parsed = self._parse_model_response(response)

        task_type = parsed.get("task_type", parsed.get("type", "complex"))
        parameters = parsed.get("parameters", parsed.get("params", {}))
        priority = parsed.get("priority", "normal")

        if not isinstance(task_type, str) or not task_type.strip():
            raise ValueError("task_type must be a non-empty string")
        if not isinstance(parameters, Mapping):
            raise ValueError("parameters must be an object")
        if not isinstance(priority, str) or not priority.strip():
            raise ValueError("priority must be a non-empty string")

        return {
            "task_type": task_type.strip().lower(),
            "parameters": dict(parameters),
            "priority": priority.strip().lower(),
        }

    @staticmethod
    def _parse_model_response(response: Any) -> Mapping[str, Any]:
        """Extract a JSON object from common chat-model response formats."""
        if isinstance(response, Mapping):
            return response

        content = getattr(response, "content", response)
        if isinstance(content, list):
            content = "".join(
                block.get("text", "") if isinstance(block, Mapping) else str(block)
                for block in content
            )
        if not isinstance(content, str):
            raise ValueError("model response must contain a JSON object")

        text = content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else ""
            if text.rstrip().endswith("```"):
                text = text.rstrip()[:-3].rstrip()

        decoder = json.JSONDecoder()
        for index, character in enumerate(text):
            if character != "{":
                continue
            try:
                value, _ = decoder.raw_decode(text[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(value, Mapping):
                return value
        raise ValueError("model response did not contain a JSON object")

    def route_task(self, task_type: str, content: Any = None) -> list[str]:
        """Return the worker names responsible for a recognised task type."""
        del content  # The argument is retained for the public API and future rules.
        if not isinstance(task_type, str):
            raise ValueError("task_type must be a string")
        routing_map = {
            "data_analysis": ["data_agent"],
            "code_generation": ["code_agent"],
            "evaluation": ["evaluator_agent"],
            "complex": ["data_agent", "code_agent"],
        }
        return list(routing_map.get(task_type.strip().lower(), ["data_agent"]))

    async def execute_tasks(
        self,
        tasks: Iterable[Mapping[str, Any]],
        message_queue: Any = None,
        timeout: float = 60,
    ) -> list[Any]:
        """Send work to the queue and collect correlated worker replies.

        Workers must reply to the ``coordinator`` inbox with a message that
        includes the original ``task_id``. Results are returned in input order,
        even if workers finish out of order.
        """
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")

        task_list = list(tasks)
        if not task_list:
            return []
        queue = message_queue if message_queue is not None else self.task_queue
        if not callable(getattr(queue, "send_message", None)) or not callable(getattr(queue, "receive_message", None)):
            raise TypeError("message_queue must provide async send_message and receive_message methods")
        if self.max_concurrent_tasks is not None and len(task_list) > self.max_concurrent_tasks:
            raise ResourceExhaustedError(
                f"received {len(task_list)} tasks; limit is {self.max_concurrent_tasks}"
            )
        task_ids: set[str] = set()
        for task in task_list:
            task_id = task.get("id")
            worker_name = task.get("worker")
            if not task_id or not worker_name:
                raise ValueError("each task needs non-empty 'id' and 'worker' fields")
            if worker_name not in self.workers:
                raise KeyError(f"unknown worker: {worker_name}")
            if str(task_id) in task_ids:
                raise ValueError(f"duplicate task id: {task_id}")
            task_ids.add(str(task_id))
            self.active_tasks[str(task_id)] = {"status": "running", "worker": worker_name}

        for task in task_list:
            task_id = str(task["id"])
            try:
                await queue.send_message(
                    from_agent="coordinator",
                    to_agent=task["worker"],
                    message={
                        "type": "task",
                        "task_id": task_id,
                        "content": task.get("content"),
                        "parameters": dict(task.get("parameters", {})),
                    },
                )
            except Exception as exc:
                self.logger.exception("Could not queue task %s", task_id)
                self.active_tasks[task_id]["status"] = "error"
                return [
                    {"id": str(item["id"]), "status": "error", "type": "error", "content": str(exc)}
                    if str(item["id"]) == task_id
                    else {"id": str(item["id"]), "status": "cancelled", "type": "error", "content": None}
                    for item in task_list
                ]

        results_by_id: dict[str, Any] = {}
        deadline = monotonic() + timeout
        while len(results_by_id) < len(task_list):
            remaining = deadline - monotonic()
            if remaining <= 0:
                break
            try:
                received = await queue.receive_message("coordinator", timeout=remaining)
            except TimeoutError:
                break

            payload = received.get("message", received) if isinstance(received, Mapping) else received
            if not isinstance(payload, Mapping):
                self.logger.warning("Ignoring non-object worker response: %r", payload)
                continue
            task_id = str(payload.get("task_id", ""))
            if task_id not in task_ids or task_id in results_by_id:
                self.logger.warning("Ignoring unexpected result for task %s", task_id or "<missing>")
                continue
            result = payload.get("result", payload)
            if isinstance(result, Mapping):
                result = dict(result)
            results_by_id[task_id] = result
            status = str(result.get("status", "success")).lower() if isinstance(result, Mapping) else "success"
            self.active_tasks[task_id]["status"] = "completed" if status == "success" else status

        results: list[Any] = []
        for task in task_list:
            task_id = str(task["id"])
            if task_id not in results_by_id:
                self.active_tasks[task_id]["status"] = "timeout"
                results.append({"id": task_id, "status": "timeout", "type": "error", "content": None})
            else:
                results.append(results_by_id[task_id])
        return results

    async def execute_tasks_with_retry(
        self,
        tasks: Iterable[Mapping[str, Any]],
        max_retries: int = 2,
        timeout: float = 60,
        fallback: Any = None,
        message_queue: Any = None,
    ) -> list[Any]:
        """Execute tasks and retry timeouts; optionally use a fallback at the end.

        ``max_retries=2`` means at most three attempts in total.  A fallback,
        when supplied, receives ``(tasks, error)`` and should return results in
        the same shape as :meth:`execute_tasks`.
        """
        if not isinstance(max_retries, int) or max_retries < 0:
            raise ValueError("max_retries must be a non-negative integer")

        task_list = list(tasks)
        for attempt in range(max_retries + 1):
            try:
                results = await self.execute_tasks(task_list, message_queue=message_queue, timeout=timeout)
                failure = next(
                    (
                        result
                        for result in results
                        if isinstance(result, Mapping)
                        and str(result.get("status", "")).lower() in {"timeout", "error", "failed"}
                    ),
                    None,
                )
                if failure is None:
                    return results
                if str(failure.get("status", "")).lower() == "timeout":
                    raise TimeoutError(f"worker task timed out: {failure.get('id', 'unknown')}")
                raise WorkerError(str(failure.get("content", "worker failed")))
            except TimeoutError as exc:
                if attempt < max_retries:
                    self.logger.warning("Retry %s/%s after timeout", attempt + 1, max_retries)
                    continue
                self.logger.error("All retries exhausted after timeout")
                if fallback is not None:
                    value = fallback(task_list, exc)
                    return await value if inspect.isawaitable(value) else value
                raise CoordinatorError("All retries exhausted") from exc
            except WorkerError:
                self.logger.exception("Worker error")
                raise
            except ResourceExhaustedError:
                self.logger.error("Task capacity exhausted")
                raise

    def aggregate_results(self, results: Iterable[Any]) -> dict[str, Any]:
        """Combine worker results without discarding worker failures."""
        aggregated: dict[str, Any] = {
            "status": "success",
            "data": {},
            "code": None,
            "evaluation": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "errors": [],
        }

        for result in results:
            if not isinstance(result, Mapping):
                aggregated["errors"].append("worker returned a non-mapping result")
                continue

            result_status = str(result.get("status", "success")).lower()
            if result_status in {"error", "timeout", "failed"}:
                aggregated["errors"].append({
                    "id": result.get("id"),
                    "status": result_status,
                    "message": result.get("content", result.get("error", "worker failed")),
                })
                continue

            result_type = str(result.get("type", result.get("task_type", ""))).lower()
            content = result.get("content", result.get("result"))
            if result_type == "data":
                aggregated["data"] = content
            elif result_type == "code":
                aggregated["code"] = content
            elif result_type in {"evaluation", "eval"}:
                aggregated["evaluation"] = content
            else:
                aggregated["errors"].append(f"unknown result type: {result_type or 'missing'}")

        if aggregated["errors"]:
            aggregated["status"] = "partial_failure"
        return aggregated
