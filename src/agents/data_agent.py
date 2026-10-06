"""Worker specialised in analysing structured data."""

from __future__ import annotations

from typing import Any

from .base_worker import BaseWorker
from tools import AggregationTool, CSVParserTool, PandasTool, QueryDatabaseTool


class DataAgent(BaseWorker):
    def __init__(self, model: Any, db_connection: Any = None):
        tools = [
            QueryDatabaseTool(db_connection),
            PandasTool(),
            CSVParserTool(),
            AggregationTool(),
        ]
        super().__init__("data_agent", model, tools, result_type="data")
        self.system_prompt = """
You are a Data Analysis Specialist. Analyse data requests with the available
database, CSV, validation, and tabular-analysis tools. Check data quality
before calculating results. Return concise, formatted insights rather than raw
records, and state assumptions when data is incomplete.
"""
