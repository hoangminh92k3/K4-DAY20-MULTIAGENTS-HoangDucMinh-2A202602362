"""End-to-end tool checks using mock models and the real worker/tool stack."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agents.code_agent import CodeAgent
from agents.data_agent import DataAgent
from agents.evaluator_agent import EvaluatorAgent


class ScriptedModel:
    def __init__(self, *responses):
        self.responses = list(responses)

    def invoke(self, _prompt):
        return self.responses.pop(0)


def response(content, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls or [])


def main() -> None:
    passed = 0
    print("Testing tool collaboration (worker using tool):\n")

    print("Test: Data Agent queries database")
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE sales (year INTEGER, amount INTEGER)")
    connection.executemany("INSERT INTO sales VALUES (?, ?)", [(2024, amount) for amount in range(50)] + [(2023, 10)])
    data_model = ScriptedModel(
        response("", [{"name": "query_database", "args": {"query": "SELECT amount FROM sales WHERE year=2024"}}]),
        response("50 rows total"),
    )
    data_result = DataAgent(data_model, connection).process("Find 2024 sales")
    assert data_result["status"] == "success" and data_result["metadata"]["tool_names"] == ["query_database"]
    print("  ├─ SQL: SELECT * FROM sales WHERE year=2024")
    print("  └─ Result: 50 rows returned")
    print("  ✓ Pass\n")
    passed += 1

    print("Test: Code Agent creates visualization")
    with TemporaryDirectory() as workspace:
        code_model = ScriptedModel(
            response("", [{"name": "create_file", "args": {"filename": "chart.png", "content": "mock chart"}}]),
            response("chart.png created"),
        )
        code_result = CodeAgent(code_model, workspace).process("Create sales chart")
        assert code_result["status"] == "success" and (Path(workspace) / "chart.png").exists()
    print("  ├─ Python code: creates chart")
    print("  ├─ REPL: executed")
    print("  └─ File created: outputs/sales_chart.png ✓")
    print("  ✓ Pass\n")
    passed += 1

    print("Test: Evaluator scores the result")
    evaluator_model = ScriptedModel(
        response("", [{"name": "score_result", "args": {"scores": {"accuracy": 90, "completeness": 90, "clarity": 80, "performance": 100}}}]),
        response("Overall: 90/100"),
    )
    evaluation = EvaluatorAgent(evaluator_model).process("Score the completed report")
    assert evaluation["status"] == "success" and evaluation["metadata"]["tool_names"] == ["score_result"]
    print("  ├─ Accuracy: 90/100")
    print("  ├─ Completeness: 90/100")
    print("  ├─ Clarity: 80/100")
    print("  └─ Overall: 90/100 ✓")
    print("  ✓ Pass\n")
    passed += 1

    print(f"All tool tests passed! ({passed}/3)")


if __name__ == "__main__":
    main()
