"""Worker specialised in producing and verifying code."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base_worker import BaseWorker
from .tools import CreateFileTool, EditFileTool, PythonREPLTool, RunScriptTool


class CodeAgent(BaseWorker):
    def __init__(self, model: Any, workspace: str | Path | None = None):
        tools = [
            PythonREPLTool(),
            CreateFileTool(workspace),
            EditFileTool(workspace),
            RunScriptTool(workspace)
        ]
        super().__init__("code_agent", model, tools, result_type="code")
        self.system_prompt = """
You are a Code Generation Specialist. Your job:
1. Write Python code to solve tasks
2. Test code locally with REPL
3. Create/edit files if needed
4. Return working code + output

When coordinator asks "create report", you:
- Write Python script using pandas, matplotlib
- Run REPL to test
- Return path to report file + console output

Important: ALWAYS test code before returning!
"""
