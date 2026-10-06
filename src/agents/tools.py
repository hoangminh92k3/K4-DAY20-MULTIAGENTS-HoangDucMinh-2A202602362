"""Small dependency-free tools used by the example worker agents.

The tools intentionally expose one common ``name``/``invoke`` interface so a
real tool implementation can later replace any of them without changing a
worker agent.
"""

from __future__ import annotations

import ast
import csv
from io import StringIO
from pathlib import Path
import subprocess
from typing import Any, Mapping


class QueryDatabaseTool:
    name = "query_database"

    def __init__(self, connection: Any = None):
        self.connection = connection

    def invoke(self, query: str | Mapping[str, Any]) -> list[dict[str, Any]]:
        if self.connection is None:
            raise RuntimeError("No database connection is configured")
        sql = query.get("query", "") if isinstance(query, Mapping) else query
        if not isinstance(sql, str) or not sql.strip().lower().startswith("select"):
            raise ValueError("query_database accepts read-only SELECT statements only")
        cursor = self.connection.execute(sql)
        columns = [column[0] for column in cursor.description or ()]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


class PandasAnalysisTool:
    """A compact tabular-analysis tool that needs no optional pandas install."""

    name = "pandas_analysis"

    def invoke(self, request: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(request, Mapping):
            raise ValueError("pandas_analysis expects an object")
        rows = request.get("rows", [])
        column = request.get("column")
        operation = str(request.get("operation", "count")).lower()
        if not isinstance(rows, list):
            raise ValueError("rows must be a list")
        values = [row.get(column) for row in rows if isinstance(row, Mapping)] if column else []
        numeric = [value for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)]
        if operation == "count":
            return {"count": len(rows)}
        if operation == "sum":
            return {"sum": sum(numeric)}
        if operation in {"average", "mean"}:
            return {"average": sum(numeric) / len(numeric) if numeric else None}
        raise ValueError(f"Unsupported analysis operation: {operation}")


class CSVParserTool:
    name = "parse_csv"

    def invoke(self, source: str | Mapping[str, Any]) -> list[dict[str, str]]:
        if isinstance(source, Mapping):
            text = source.get("text")
            path = source.get("path")
            if text is None and path:
                text = Path(path).read_text(encoding="utf-8")
        else:
            text = source
        if not isinstance(text, str):
            raise ValueError("parse_csv expects CSV text or a file path")
        return list(csv.DictReader(StringIO(text)))


class DataValidationTool:
    name = "validate_data"

    def invoke(self, rows: list[Mapping[str, Any]] | Mapping[str, Any]) -> dict[str, Any]:
        records = rows.get("rows", []) if isinstance(rows, Mapping) else rows
        if not isinstance(records, list):
            raise ValueError("validate_data expects a list of records")
        missing = sum(
            1
            for row in records
            if not isinstance(row, Mapping) or any(value in (None, "") for value in row.values())
        )
        return {"valid": missing == 0, "rows": len(records), "rows_with_missing_values": missing}


class PythonREPLTool:
    name = "python_repl"

    def invoke(self, request: str | Mapping[str, Any]) -> Any:
        code = request.get("code", "") if isinstance(request, Mapping) else request
        if not isinstance(code, str) or not code.strip():
            raise ValueError("python_repl requires non-empty code")
        tree = ast.parse(code, mode="exec")
        namespace: dict[str, Any] = {"__builtins__": {"len": len, "sum": sum, "min": min, "max": max, "range": range}}
        if len(tree.body) == 1 and isinstance(tree.body[0], ast.Expr):
            return eval(compile(ast.Expression(tree.body[0].value), "<repl>", "eval"), namespace, namespace)
        exec(compile(tree, "<repl>", "exec"), namespace, namespace)
        return {key: value for key, value in namespace.items() if not key.startswith("_")}


class _WorkspaceTool:
    def __init__(self, workspace: str | Path | None = None):
        self.workspace = Path(workspace or Path.cwd()).resolve()

    def _path(self, value: str) -> Path:
        path = (self.workspace / value).resolve()
        if path != self.workspace and self.workspace not in path.parents:
            raise ValueError("file path must stay inside the configured workspace")
        return path


class CreateFileTool(_WorkspaceTool):
    name = "create_file"

    def invoke(self, request: Mapping[str, Any]) -> dict[str, Any]:
        path = self._path(str(request["path"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        content = str(request.get("content", ""))
        path.write_text(content, encoding="utf-8")
        return {"path": str(path), "bytes_written": len(content.encode("utf-8"))}


class EditFileTool(_WorkspaceTool):
    name = "edit_file"

    def invoke(self, request: Mapping[str, Any]) -> dict[str, Any]:
        path = self._path(str(request["path"]))
        if not path.exists():
            raise FileNotFoundError(path)
        current = path.read_text(encoding="utf-8")
        if "old" in request:
            old, new = str(request["old"]), str(request.get("new", ""))
            if old not in current:
                raise ValueError("text to replace was not found")
            updated = current.replace(old, new, 1)
        else:
            updated = str(request["content"])
        path.write_text(updated, encoding="utf-8")
        return {"path": str(path), "bytes_written": len(updated.encode("utf-8"))}


class RunScriptTool(_WorkspaceTool):
    name = "run_script"

    def invoke(self, request: str | Mapping[str, Any]) -> dict[str, Any]:
        command = request.get("command") if isinstance(request, Mapping) else request
        if not isinstance(command, str) or not command.strip():
            raise ValueError("run_script requires a command")
        completed = subprocess.run(command, cwd=self.workspace, shell=True, capture_output=True, text=True, timeout=30)
        return {"returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


class ScoringTool:
    name = "score_result"

    def invoke(self, request: Mapping[str, Any]) -> dict[str, Any]:
        scores = request.get("scores", request)
        values = [float(value) for value in scores.values()] if isinstance(scores, Mapping) else []
        return {"score": round(sum(values) / len(values), 2) if values else 0.0}


class ValidationTool:
    name = "validate_result"

    def invoke(self, request: Mapping[str, Any]) -> dict[str, bool]:
        required = request.get("required", [])
        value = request.get("value", {})
        return {"valid": isinstance(value, Mapping) and all(field in value for field in required)}


class QualityCheckTool:
    name = "quality_check"

    def invoke(self, text: str | Mapping[str, Any]) -> dict[str, Any]:
        value = text.get("text", "") if isinstance(text, Mapping) else text
        return {"non_empty": bool(str(value).strip()), "characters": len(str(value))}


class FeedbackGeneratorTool:
    name = "generate_feedback"

    def invoke(self, request: Mapping[str, Any]) -> dict[str, list[str]]:
        issues = list(request.get("issues", []))
        return {"feedback": [f"Improve: {issue}" for issue in issues] or ["Result meets the supplied checks."]}
