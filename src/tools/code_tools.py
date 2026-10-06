"""Tools for writing, editing, and safely exercising Python code."""

from __future__ import annotations

import ast
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import shlex
import subprocess
from collections.abc import Mapping
from typing import Any

from .base_tool import BaseTool


class PythonREPLTool(BaseTool):
    def __init__(self):
        super().__init__("python_repl", "Execute basic Python expressions and statements")
        self.globals: dict[str, Any] = {
            "__builtins__": {
                "dict": dict, "float": float, "int": int, "len": len, "list": list,
                "max": max, "min": min, "print": print, "range": range, "str": str, "sum": sum,
            }
        }
        self.max_output_len = 10_000

    def validate_input(self, input_dict: Mapping[str, Any]) -> None:
        super().validate_input(input_dict)
        code = input_dict.get("code")
        if not isinstance(code, str) or not code.strip():
            raise ValueError("code must be a non-empty string")
        tree = ast.parse(code, mode="exec")
        if any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(tree)):
            raise ValueError("imports are not allowed in python_repl")

    def invoke(self, input_dict: Mapping[str, Any]) -> dict[str, Any]:
        self.validate_input(input_dict)
        code = input_dict["code"]
        tree = ast.parse(code, mode="exec")
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            if len(tree.body) == 1 and isinstance(tree.body[0], ast.Expr):
                # Preserve the REPL convention: a single expression yields its value.
                return eval(compile(ast.Expression(tree.body[0].value), "<python_repl>", "eval"), self.globals, self.globals)
            exec(compile(tree, "<python_repl>", "exec"), self.globals, self.globals)
        return {
            "status": "success",
            "stdout": stdout.getvalue()[: self.max_output_len],
            "stderr": stderr.getvalue()[: self.max_output_len],
            "variables": {key: repr(value) for key, value in self.globals.items() if not key.startswith("_")},
        }


class _WorkspaceTool(BaseTool):
    def __init__(self, name: str, description: str, base_path: str | Path | None = None):
        super().__init__(name, description)
        self.base_path = Path(base_path or Path.cwd()).resolve()

    def _resolve_path(self, input_dict: Mapping[str, Any]) -> Path:
        value = input_dict.get("filename", input_dict.get("path"))
        if not isinstance(value, str) or not value.strip():
            raise ValueError("filename or path must be a non-empty string")
        path = (self.base_path / value).resolve()
        if path != self.base_path and self.base_path not in path.parents:
            raise ValueError("path must stay inside base_path")
        return path


class CreateFileTool(_WorkspaceTool):
    def __init__(self, base_path: str | Path | None = None):
        super().__init__("create_file", "Create a text file inside the configured workspace", base_path)

    def validate_input(self, input_dict: Mapping[str, Any]) -> None:
        super().validate_input(input_dict)
        self._resolve_path(input_dict)
        if not isinstance(input_dict.get("content", ""), str):
            raise ValueError("content must be a string")

    def invoke(self, input_dict: Mapping[str, Any]) -> dict[str, Any]:
        self.validate_input(input_dict)
        path = self._resolve_path(input_dict)
        content = input_dict.get("content", "")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"status": "success", "path": str(path), "size": len(content.encode("utf-8"))}


class EditFileTool(_WorkspaceTool):
    def __init__(self, base_path: str | Path | None = None):
        super().__init__("edit_file", "Replace file content or one exact text occurrence", base_path)

    def validate_input(self, input_dict: Mapping[str, Any]) -> None:
        super().validate_input(input_dict)
        self._resolve_path(input_dict)
        if "content" not in input_dict and not {"old", "new"} <= set(input_dict):
            raise ValueError("provide content or both old and new")

    def invoke(self, input_dict: Mapping[str, Any]) -> dict[str, Any]:
        self.validate_input(input_dict)
        path = self._resolve_path(input_dict)
        if not path.exists():
            raise FileNotFoundError(path)
        current = path.read_text(encoding="utf-8")
        if "content" in input_dict:
            updated = str(input_dict["content"])
        else:
            old, new = str(input_dict["old"]), str(input_dict["new"])
            if old not in current:
                raise ValueError("old text was not found")
            updated = current.replace(old, new, 1)
        path.write_text(updated, encoding="utf-8")
        return {"status": "success", "path": str(path), "size": len(updated.encode("utf-8"))}


class RunScriptTool(_WorkspaceTool):
    def __init__(self, base_path: str | Path | None = None):
        super().__init__("run_script", "Run a command inside the configured workspace", base_path)

    def validate_input(self, input_dict: Mapping[str, Any]) -> None:
        super().validate_input(input_dict)
        command = input_dict.get("command")
        if not isinstance(command, (str, list)) or not command:
            raise ValueError("command must be a non-empty string or list")

    def invoke(self, input_dict: Mapping[str, Any]) -> dict[str, Any]:
        self.validate_input(input_dict)
        command = input_dict["command"]
        args = shlex.split(command) if isinstance(command, str) else command
        completed = subprocess.run(args, cwd=self.base_path, capture_output=True, text=True, timeout=30, check=False)
        return {"status": "success", "returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}
