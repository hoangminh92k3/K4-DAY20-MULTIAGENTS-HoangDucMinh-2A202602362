"""Data parsing and aggregation tools without optional runtime dependencies."""

from __future__ import annotations

import csv
from collections import defaultdict
from collections.abc import Mapping
from io import StringIO
from pathlib import Path
from typing import Any

from .base_tool import BaseTool


class PandasTool(BaseTool):
    """Perform common table operations on a list of record dictionaries."""

    def __init__(self):
        super().__init__("pandas_analysis", "Analyse tabular records with count, sum, mean, or grouping")

    def validate_input(self, input_dict: Mapping[str, Any]) -> None:
        super().validate_input(input_dict)
        if not isinstance(input_dict.get("rows"), list):
            raise ValueError("rows must be a list")

    def invoke(self, input_dict: Mapping[str, Any]) -> dict[str, Any]:
        self.validate_input(input_dict)
        rows = input_dict["rows"]
        operation = str(input_dict.get("operation", "count")).lower()
        column = input_dict.get("column")
        valid_rows = [row for row in rows if isinstance(row, Mapping)]
        if operation == "count":
            return {"status": "success", "count": len(valid_rows)}
        if not isinstance(column, str) or not column:
            raise ValueError("column is required for this operation")
        values = [row.get(column) for row in valid_rows]
        numeric = [value for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)]
        if operation == "sum":
            return {"status": "success", "sum": sum(numeric)}
        if operation in {"mean", "average"}:
            return {"status": "success", "mean": sum(numeric) / len(numeric) if numeric else None}
        if operation == "group_count":
            counts: dict[str, int] = defaultdict(int)
            for value in values:
                counts[str(value)] += 1
            return {"status": "success", "groups": dict(counts)}
        raise ValueError(f"unsupported operation: {operation}")


class CSVParserTool(BaseTool):
    def __init__(self):
        super().__init__("parse_csv", "Parse CSV text or a UTF-8 CSV file")

    def validate_input(self, input_dict: Mapping[str, Any]) -> None:
        super().validate_input(input_dict)
        if not isinstance(input_dict.get("text", input_dict.get("path")), str):
            raise ValueError("provide CSV text or a CSV path")

    def invoke(self, input_dict: Mapping[str, Any]) -> dict[str, Any]:
        self.validate_input(input_dict)
        text = input_dict.get("text")
        if text is None:
            text = Path(input_dict["path"]).read_text(encoding="utf-8")
        rows = list(csv.DictReader(StringIO(text)))
        return {"status": "success", "rows": rows, "count": len(rows)}


class AggregationTool(BaseTool):
    def __init__(self):
        super().__init__("aggregate_data", "Aggregate numeric values with count, sum, mean, minimum, or maximum")

    def validate_input(self, input_dict: Mapping[str, Any]) -> None:
        super().validate_input(input_dict)
        if not isinstance(input_dict.get("values"), list):
            raise ValueError("values must be a list")

    def invoke(self, input_dict: Mapping[str, Any]) -> dict[str, Any]:
        self.validate_input(input_dict)
        values = input_dict["values"]
        numbers = [value for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)]
        operation = str(input_dict.get("operation", "sum")).lower()
        if operation == "count":
            value: int | float | None = len(values)
        elif operation == "sum":
            value = sum(numbers)
        elif operation in {"mean", "average"}:
            value = sum(numbers) / len(numbers) if numbers else None
        elif operation == "min":
            value = min(numbers) if numbers else None
        elif operation == "max":
            value = max(numbers) if numbers else None
        else:
            raise ValueError(f"unsupported aggregation: {operation}")
        return {"status": "success", "operation": operation, "value": value, "numeric_count": len(numbers)}
