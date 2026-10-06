"""Tools for deterministic quality evaluation and reporting."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .base_tool import BaseTool


class ScoringTool(BaseTool):
    def __init__(self):
        super().__init__("score_result", "Calculate a 0-100 weighted score from criterion scores")

    def validate_input(self, input_dict: Mapping[str, Any]) -> None:
        super().validate_input(input_dict)
        if not isinstance(input_dict.get("scores"), Mapping):
            raise ValueError("scores must be an object mapping criteria to 0-100 values")

    def invoke(self, input_dict: Mapping[str, Any]) -> dict[str, Any]:
        self.validate_input(input_dict)
        scores = {str(name): float(value) for name, value in input_dict["scores"].items()}
        if not scores or any(not 0 <= score <= 100 for score in scores.values()):
            raise ValueError("scores must contain values from 0 to 100")
        weights = input_dict.get("weights", input_dict.get("criteria", {}))
        if weights:
            if not isinstance(weights, Mapping) or set(weights) != set(scores):
                raise ValueError("weights must cover exactly the scored criteria")
            total_weight = sum(float(weight) for weight in weights.values())
            if total_weight <= 0:
                raise ValueError("weights must sum to a positive value")
            score = sum(scores[name] * float(weights[name]) for name in scores) / total_weight
        else:
            score = sum(scores.values()) / len(scores)
        score = round(score, 2)
        return {"status": "success", "scores": scores, "score": score, "weighted_score": score, "grade": self._score_to_grade(score)}

    @staticmethod
    def _score_to_grade(score: float) -> str:
        if score >= 90:
            return "A"
        if score >= 80:
            return "B"
        if score >= 70:
            return "C"
        if score >= 60:
            return "D"
        return "F"


class ValidationTool(BaseTool):
    def __init__(self):
        super().__init__("validate_result", "Check that a mapping includes required fields")

    def invoke(self, input_dict: Mapping[str, Any]) -> dict[str, Any]:
        self.validate_input(input_dict)
        value, required = input_dict.get("value", {}), input_dict.get("required", [])
        if not isinstance(value, Mapping) or not isinstance(required, list):
            raise ValueError("value must be an object and required must be a list")
        missing = [field for field in required if field not in value]
        return {"status": "success", "valid": not missing, "missing": missing}


class ComparisonTool(BaseTool):
    def __init__(self):
        super().__init__("compare_results", "Compare expected and actual mapping values")

    def invoke(self, input_dict: Mapping[str, Any]) -> dict[str, Any]:
        self.validate_input(input_dict)
        expected, actual = input_dict.get("expected"), input_dict.get("actual")
        if not isinstance(expected, Mapping) or not isinstance(actual, Mapping):
            raise ValueError("expected and actual must be objects")
        differences = {key: {"expected": value, "actual": actual.get(key)} for key, value in expected.items() if actual.get(key) != value}
        return {"status": "success", "matches": not differences, "differences": differences}


class ReportGeneratorTool(BaseTool):
    def __init__(self):
        super().__init__("generate_report", "Generate a compact text report from a title and sections")

    def invoke(self, input_dict: Mapping[str, Any]) -> dict[str, str]:
        self.validate_input(input_dict)
        title, sections = input_dict.get("title", "Report"), input_dict.get("sections", {})
        if not isinstance(title, str) or not isinstance(sections, Mapping):
            raise ValueError("title must be a string and sections must be an object")
        body = "\n".join(f"## {name}\n{value}" for name, value in sections.items())
        return {"status": "success", "report": f"# {title}\n\n{body}".rstrip()}
