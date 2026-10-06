"""Offline checks for the specialised worker agents."""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agents.code_agent import CodeAgent
from agents.data_agent import DataAgent
from agents.evaluator_agent import EvaluatorAgent


class ScriptedModel:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return self.responses.pop(0)


def response(content, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls or [])


def test_data_agent_init():
    agent = DataAgent(ScriptedModel(response("unused")))

    assert agent.name == "data_agent"
    assert agent.result_type == "data"
    assert set(agent.tools) == {"query_database", "pandas_analysis", "parse_csv", "validate_data"}
    assert "Data Analysis Specialist" in agent.system_prompt


def test_data_agent_process():
    model = ScriptedModel(response("Sales: $5M, +10% MoM"))
    result = DataAgent(model).process("Analyze sales", {"period": "Q3"})

    assert result["status"] == "success"
    assert result["type"] == "data"
    assert result["content"] == "Sales: $5M, +10% MoM"
    assert "Parameters: {'period': 'Q3'}" in model.prompts[0]


def test_code_agent_process(tmp_path):
    model = ScriptedModel(
        response("", [{"name": "python_repl", "args": {"code": "2 + 3"}}]),
        response("report.py created and tested"),
    )
    result = CodeAgent(model, workspace=tmp_path).process("Create a report")

    assert result["status"] == "success"
    assert result["type"] == "code"
    assert result["content"] == "report.py created and tested"
    assert result["metadata"]["tool_names"] == ["python_repl"]
    assert "Tool python_repl returned: 5" in model.prompts[1]


def test_evaluator_agent():
    model = ScriptedModel(response('{"score": 95, "feedback": "Good", "issues": [], "suggestions": []}'))
    result = EvaluatorAgent(model).process("Evaluate the report")

    assert result["status"] == "success"
    assert result["type"] == "evaluation"
    assert "score" in result["content"]
    assert {"score_result", "validate_result", "quality_check", "generate_feedback"} == set(EvaluatorAgent(model).tools)
