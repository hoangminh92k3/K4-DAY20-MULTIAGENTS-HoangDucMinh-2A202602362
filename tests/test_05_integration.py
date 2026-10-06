"""Unit, integration, end-to-end, latency, and concurrency coverage."""

import asyncio
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coordinator import Coordinator
from multi_agent_system import MultiAgentSystem


class IntentModel:
    def invoke(self, prompt):
        task_type = "data_analysis" if "simple task" in prompt.lower() else "complex"
        return SimpleNamespace(content=(
            f'{{"task_type": "{task_type}", "parameters": {{"period": "Q3"}}, "priority": "normal"}}'
        ))


class MockWorker:
    def __init__(self, name, result_type, content):
        self.name = name
        self.result_type = result_type
        self.content = content

    async def process_async(self, _task_content, _parameters=None):
        await asyncio.sleep(0)
        return {"status": "success", "type": self.result_type, "content": self.content}


def make_system():
    coordinator = Coordinator(
        IntentModel(),
        [
            MockWorker("data_agent", "data", "Q3 revenue: 5 million"),
            MockWorker("code_agent", "code", "chart.png created with plot"),
            MockWorker("evaluator_agent", "evaluation", "score: 90/100"),
        ],
    )
    return coordinator, MultiAgentSystem(coordinator)


def test_coordinator_parse_request():
    coordinator, _system = make_system()
    result = coordinator.parse_request("Analyze sales data")

    assert result["task_type"] == "complex"
    assert result["parameters"] == {"period": "Q3"}


def test_coordinator_with_workers():
    coordinator, _system = make_system()
    response = asyncio.run(coordinator.handle_request("Calculate revenue and create chart"))

    assert response["status"] == "success"
    assert response["data"] == "Q3 revenue: 5 million"
    assert response["code"] == "chart.png created with plot"


def test_full_pipeline():
    _coordinator, system = make_system()
    result = asyncio.run(system.process("What was Q3 revenue? Create a visualization."))

    assert result["status"] == "success"
    assert "revenue" in result["data"].lower()
    assert "chart" in result["code"] or "plot" in result["code"]
    assert "score" in result["evaluation"]


def test_latency():
    _coordinator, system = make_system()
    started = time.perf_counter()
    result = asyncio.run(system.process("Simple task"))
    latency = time.perf_counter() - started

    assert result["status"] == "success"
    assert latency < 10


def test_concurrent_requests():
    _coordinator, system = make_system()

    async def process_all():
        return await asyncio.gather(*(system.process(f"Task {index}") for index in range(10)))

    results = asyncio.run(process_all())
    assert sum(result["status"] == "success" for result in results) >= 8
