"""Run coordinator-only end-to-end checks without a model provider or API key."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coordinator import Coordinator


# The coordinator still emits logs in an application.  This demo prints only
# its human-readable test report, matching the workshop's expected output.
logging.getLogger("coordinator").addHandler(logging.NullHandler())


class MockModel:
    def invoke(self, prompt):
        request = prompt.lower()
        task_type = "complex" if "report" in request else "data_analysis"
        return SimpleNamespace(
            content=json.dumps({"task_type": task_type, "parameters": {}, "priority": "normal"})
        )


class MockWorker:
    def __init__(self, name, result_type, delay=0):
        self.name = name
        self.result_type = result_type
        self.delay = delay

    async def process_async(self, content):
        await asyncio.sleep(self.delay)
        return {"type": self.result_type, "content": f"mock {self.result_type} result: {content}"}


class MockMessageQueue:
    """Queue mock that simulates workers replying through the coordinator inbox."""

    def __init__(self, delay=0, reply=True):
        self.delay = delay
        self.reply = reply
        self.replies = []

    async def send_message(self, from_agent, to_agent, message):
        del from_agent
        if self.reply:
            result_type = {"data_agent": "data", "code_agent": "code"}[to_agent]
            self.replies.append({
                "task_id": message["task_id"],
                "result": {"type": result_type, "content": f"mock {result_type} result"},
            })
        return message["task_id"]

    async def receive_message(self, _agent_name, timeout):
        if self.delay >= timeout or not self.replies:
            await asyncio.sleep(timeout)
            raise TimeoutError("mock queue timed out")
        await asyncio.sleep(self.delay)
        return self.replies.pop()


def coordinator(delay=0):
    return Coordinator(
        MockModel(),
        [MockWorker("data_agent", "data", delay), MockWorker("code_agent", "code", delay)],
    )


def main():
    passed = 0
    print("Testing Coordinator with mock workers...\n")

    print("Test 1: Simple task")
    request = coordinator().parse_request("Analyze sales data")
    routes = coordinator().route_task(request["task_type"])
    results = asyncio.run(coordinator().execute_tasks([
        {"id": "sales", "worker": routes[0], "content": "Analyze sales data"}
    ], MockMessageQueue()))
    assert request["task_type"] == "data_analysis" and routes == ["data_agent"]
    assert results[0]["type"] == "data"
    print('Input: "Analyze sales data"')
    print("Parsed: type=data_analysis")
    print("Routed to: data_agent")
    print("Result: [mock data returned]")
    print("✓ Pass\n")
    passed += 1

    print("Test 2: Multiple tasks")
    routes = coordinator().route_task("complex")
    started = perf_counter()
    results = asyncio.run(coordinator().execute_tasks([
        {"id": "data", "worker": routes[0], "content": "Analyze data"},
        {"id": "code", "worker": routes[1], "content": "Create report"},
    ], MockMessageQueue()))
    elapsed = perf_counter() - started
    assert routes == ["data_agent", "code_agent"] and len(results) == 2
    print('Input: "Analyze AND create report"')
    print("Routed to: data_agent, code_agent")
    print(f"Results: both returned in {elapsed:.2f}s")
    print("✓ Pass\n")
    passed += 1

    print("Test 3: Timeout handling")
    used_fallback = False

    def fallback(_tasks, _error):
        nonlocal used_fallback
        used_fallback = True
        return [{"type": "data", "content": "fallback result"}]

    results = asyncio.run(coordinator(delay=0.05).execute_tasks_with_retry(
        [{"id": "slow", "worker": "data_agent", "content": "Long task"}],
        max_retries=0,
        timeout=0.001,
        fallback=fallback,
        message_queue=MockMessageQueue(reply=False),
    ))
    assert used_fallback and results[0]["content"] == "fallback result"
    print('Input: "Long task"')
    print("Timeout after 0.001s")
    print("Fallback triggered")
    print("✓ Pass\n")
    passed += 1

    print(f"All coordinator tests passed! ({passed}/3)")


if __name__ == "__main__":
    main()
