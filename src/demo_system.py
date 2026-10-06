"""Deterministic offline system used by debug, profile, and benchmark scripts."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any

from coordinator import Coordinator
from multi_agent_system import MultiAgentSystem


class DemoModel:
    """Classifies prompts without network calls so diagnostic scripts are reproducible."""

    def invoke(self, prompt: str) -> SimpleNamespace:
        text = prompt.lower()
        if any(word in text for word in (" and ", "chart", "visual", "report", "analyze")):
            task_type = "complex"
        elif any(word in text for word in ("write", "python", "script", "code")):
            task_type = "code_generation"
        else:
            task_type = "data_analysis"
        return SimpleNamespace(content=json.dumps({
            "task_type": task_type,
            "parameters": {"source": "offline-demo"},
            "priority": "normal",
        }))


class DemoWorker:
    def __init__(self, name: str, result_type: str, response: str):
        self.name = name
        self.result_type = result_type
        self.response = response

    async def process_async(self, _content: Any, _parameters: Any = None) -> dict[str, Any]:
        await asyncio.sleep(0)
        return {"status": "success", "type": self.result_type, "content": self.response}


def create_demo_system() -> MultiAgentSystem:
    """Return a fully local data/code/evaluation system for diagnostics."""
    workers = [
        DemoWorker("data_agent", "data", "Revenue analysis: Q3 revenue is 5M."),
        DemoWorker("code_agent", "code", "chart.png created using a revenue plot."),
        DemoWorker("evaluator_agent", "evaluation", "score: 90/100; result is complete."),
    ]
    return MultiAgentSystem(Coordinator(DemoModel(), workers), workers)
