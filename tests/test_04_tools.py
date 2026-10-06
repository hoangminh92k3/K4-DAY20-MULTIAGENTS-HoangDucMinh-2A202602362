"""Offline checks for the reusable tools package."""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tools.code_tools import CreateFileTool, PythonREPLTool
from tools.database_tools import QueryDatabaseTool
from tools.evaluation_tools import ScoringTool


def test_query_database_tool():
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE sales (region TEXT, amount INTEGER)")
    connection.executemany("INSERT INTO sales VALUES (?, ?)", [("north", 10), ("south", 20)])
    result = QueryDatabaseTool(connection).invoke({"query": "SELECT region, amount FROM sales", "limit": 10})

    assert result["status"] == "success"
    assert result["rows"] == 2
    assert result["data"] == [{"region": "north", "amount": 10}, {"region": "south", "amount": 20}]


def test_python_repl_tool():
    result = PythonREPLTool().invoke({"code": "value = 2 + 3\nprint(value)"})

    assert result["status"] == "success"
    assert result["stdout"] == "5\n"
    assert result["variables"]["value"] == "5"


def test_create_file_tool(tmp_path):
    result = CreateFileTool(tmp_path).invoke({"filename": "reports/q3.txt", "content": "Revenue: 50"})

    assert result["status"] == "success"
    assert (tmp_path / "reports" / "q3.txt").read_text(encoding="utf-8") == "Revenue: 50"
    assert result["size"] == len("Revenue: 50")


def test_scoring_tool():
    result = ScoringTool().invoke({
        "scores": {"accuracy": 90, "completeness": 80},
        "weights": {"accuracy": 3, "completeness": 1},
    })

    assert result["status"] == "success"
    assert result["score"] == 87.5
    assert result["grade"] == "B"
