"""Base implementation shared by all specialised worker agents."""

from __future__ import annotations

import asyncio
import logging
from time import perf_counter
from typing import Any, Iterable, Mapping


class BaseWorker:
    """Run a model/tool loop and return a coordinator-friendly result object."""

    max_tool_calls = 20

    def __init__(self, name: str, model: Any, tools: Iterable[Any], result_type: str):
        if not name:
            raise ValueError("worker name is required")
        self.name = name
        self.model = model
        self.tools = {tool.name: tool for tool in tools}
        self.result_type = result_type
        self.system_prompt = ""
        self.logger = logging.getLogger(name)
        self._executed_tools: list[str] = []

    def process(self, task_content: Any, parameters: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Process one task synchronously, returning success or a structured error."""
        started = perf_counter()
        self._executed_tools = []
        try:
            if task_content is None or (isinstance(task_content, str) and not task_content.strip()):
                raise ValueError("task_content must not be empty")
            prompt = self._build_prompt(task_content, parameters)
            self.logger.info("Worker %s started", self.name)
            response = self.model.invoke(prompt)

            calls = 0
            while getattr(response, "tool_calls", None):
                for call in response.tool_calls:
                    calls += 1
                    if calls > self.max_tool_calls:
                        raise RuntimeError("tool-call limit exceeded")
                    tool_name = call["name"]
                    tool_input = call.get("input", call.get("args", {}))
                    result = self._execute_tool(tool_name, tool_input)
                    prompt += f"\nTool {tool_name} returned: {result}"
                response = self.model.invoke(prompt)

            content = getattr(response, "content", str(response))
            duration = round(perf_counter() - started, 6)
            self.logger.info("Worker %s completed in %.3fs", self.name, duration)
            return {
                "status": "success",
                "type": self.result_type,
                "content": content,
                "result": content,
                "metadata": {"tools_used": len(self._executed_tools), "tool_names": list(self._executed_tools), "seconds": duration},
            }
        except Exception as exc:
            duration = round(perf_counter() - started, 6)
            self.logger.exception("Worker %s failed", self.name)
            return {
                "status": "error",
                "type": self.result_type,
                "content": str(exc),
                "error": str(exc),
                "result": None,
                "metadata": {"tools_used": len(self._executed_tools), "tool_names": list(self._executed_tools), "seconds": duration},
            }

    async def process_async(self, task_content: Any, parameters: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Run the synchronous worker in a thread without blocking the event loop."""
        return await asyncio.to_thread(self.process, task_content, parameters)

    def _build_prompt(self, task_content: Any, parameters: Mapping[str, Any] | None) -> str:
        """Build the model prompt with the worker's specialised instructions."""
        return (
            f"{self.system_prompt.strip()}\n\n"
            f"Task: {task_content}\n"
            f"Parameters: {dict(parameters or {})}\n"
            f"Available tools: {list(self.tools)}"
        )

    def _execute_tool(self, tool_name: str, tool_input: Any) -> Any:
        """Execute one named tool and surface failures to ``process``."""
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        try:
            result = self.tools[tool_name].invoke(tool_input)
            self._executed_tools.append(tool_name)
            return result
        except Exception:
            self.logger.exception("Tool %s failed in worker %s", tool_name, self.name)
            raise
