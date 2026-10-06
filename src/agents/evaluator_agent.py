"""Worker specialised in evaluating other worker outputs."""

from __future__ import annotations

from typing import Any

from .base_worker import BaseWorker
from .tools import FeedbackGeneratorTool, QualityCheckTool, ScoringTool, ValidationTool


class EvaluatorAgent(BaseWorker):
    def __init__(self, model: Any):
        tools = [
            ScoringTool(),
            ValidationTool(),
            QualityCheckTool(),
            FeedbackGeneratorTool()
        ]
        super().__init__("evaluator_agent", model, tools, result_type="evaluation")
        self.system_prompt = """
You are a Quality Evaluation Specialist. Your job:
1. Evaluate results from data/code agents
2. Score on accuracy, completeness, clarity
3. Identify issues
4. Suggest improvements

Evaluation criteria:
- Accuracy: 30% (correctness)
- Completeness: 30% (all requirements met)
- Clarity: 20% (easy to understand)
- Performance: 20% (efficient)

Return format:
{
  "score": 0-100,
  "feedback": "What's good/bad",
  "issues": ["issue1", "issue2"],
  "suggestions": ["fix1", "fix2"]
}
"""
