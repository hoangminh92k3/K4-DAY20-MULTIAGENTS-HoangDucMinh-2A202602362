"""Offline checks for the coordinator exercise."""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coordinator import Coordinator


class FakeModel:
    def invoke(self, _prompt):
        return SimpleNamespace(
            content='{"task_type": "complex", "parameters": {"period": "Q3"}, "priority": "high"}'
        )


class FakeWorker:
    def __init__(self, name, result_type, delay=0):
        self.name = name
        self.result_type = result_type
        self.delay = delay

    async def process_async(self, content):
        await asyncio.sleep(self.delay)
        return {"type": self.result_type, "content": content}


class FakeMessageQueue:
    def __init__(self, reply=True):
        self.reply = reply
        self.sent = []
        self.replies = []

    async def send_message(self, from_agent, to_agent, message):
        self.sent.append({"from_agent": from_agent, "to_agent": to_agent, "message": message})
        if self.reply:
            result_type = {"data_agent": "data", "code_agent": "code"}[to_agent]
            self.replies.append({
                "task_id": message["task_id"],
                "result": {"type": result_type, "content": message["content"]},
            })
        return f"message-{len(self.sent)}"

    async def receive_message(self, _agent_name, timeout):
        if not self.replies:
            await asyncio.sleep(timeout)
            raise TimeoutError("no result")
        return self.replies.pop()  # Return reverse order to test task-id correlation.


def make_coordinator(delay=0):
    return Coordinator(
        FakeModel(),
        [FakeWorker("data_agent", "data", delay), FakeWorker("code_agent", "code", delay)],
    )


def test_coordinator_init():
    coordinator = make_coordinator()

    assert set(coordinator.workers) == {"data_agent", "code_agent"}
    assert coordinator.active_tasks == {}
    assert coordinator.task_queue is not None


def test_parse_request():
    request = make_coordinator().parse_request("Tính doanh thu Q3 và tạo biểu đồ")

    assert request == {
        "task_type": "complex",
        "parameters": {"period": "Q3"},
        "priority": "high",
    }


def test_route_task():
    coordinator = make_coordinator()

    assert coordinator.route_task("data_analysis") == ["data_agent"]
    assert coordinator.route_task("code_generation") == ["code_agent"]
    assert coordinator.route_task("complex") == ["data_agent", "code_agent"]


def test_execute_tasks():
    coordinator = make_coordinator()
    queue = FakeMessageQueue()
    results = asyncio.run(coordinator.execute_tasks([
        {"id": "data-q3", "worker": "data_agent", "content": {"revenue": 50}, "parameters": {"quarter": "Q3"}},
        {"id": "chart-q3", "worker": "code_agent", "content": "create chart"},
    ], queue))

    assert results == [
        {"type": "data", "content": {"revenue": 50}},
        {"type": "code", "content": "create chart"},
    ]
    assert queue.sent[0]["message"]["parameters"] == {"quarter": "Q3"}
    assert {task["status"] for task in coordinator.active_tasks.values()} == {"completed"}

    fallback_called = False

    def fallback(_tasks, _error):
        nonlocal fallback_called
        fallback_called = True
        return [{"type": "data", "content": "fallback"}]

    timed_out = asyncio.run(make_coordinator(delay=0.01).execute_tasks_with_retry(
        [{"id": "slow", "worker": "data_agent", "content": "long task"}],
        max_retries=0,
        timeout=0.001,
        fallback=fallback,
        message_queue=FakeMessageQueue(reply=False),
    ))
    assert fallback_called and timed_out == [{"type": "data", "content": "fallback"}]


def test_aggregate_results():
    combined = make_coordinator().aggregate_results([
        {"type": "data", "content": {"revenue": 50}},
        {"type": "code", "content": "chart.py"},
        {"type": "evaluation", "content": {"valid": True}},
    ])

    assert combined["status"] == "success"
    assert combined["data"] == {"revenue": 50}
    assert combined["code"] == "chart.py"
    assert combined["evaluation"] == {"valid": True}
    assert combined["errors"] == []
