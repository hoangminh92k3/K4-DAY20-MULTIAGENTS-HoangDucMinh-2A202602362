"""Read-only SQLite database tool."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from typing import Any

from .base_tool import BaseTool


class QueryDatabaseTool(BaseTool):
    """Run bounded, read-only SELECT queries and return JSON-ready rows."""

    def __init__(self, connection_string: str | sqlite3.Connection | None = None):
        super().__init__("query_database", "Execute a read-only SELECT query against SQLite")
        self.connection_string = connection_string
        self.connection: sqlite3.Connection | None = (
            connection_string if isinstance(connection_string, sqlite3.Connection) else None
        )
        if self.connection is not None:
            self.connection.row_factory = sqlite3.Row

    def connect(self) -> sqlite3.Connection:
        if self.connection is None:
            database = self.connection_string or ":memory:"
            if not isinstance(database, str):
                raise TypeError("connection_string must be a SQLite path or connection")
            self.connection = sqlite3.connect(database)
            self.connection.row_factory = sqlite3.Row
        return self.connection

    def validate_input(self, input_dict: Mapping[str, Any]) -> None:
        super().validate_input(input_dict)
        query = input_dict.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        normalized = query.lstrip().upper()
        if not normalized.startswith("SELECT"):
            raise ValueError("only SELECT queries are allowed")
        if ";" in query.rstrip(";"):
            raise ValueError("multiple SQL statements are not allowed")
        limit = input_dict.get("limit", 1000)
        if not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise ValueError("limit must be an integer from 1 to 1000")

    def invoke(self, input_dict: Mapping[str, Any]) -> dict[str, Any]:
        self.validate_input(input_dict)
        cursor = self.connect().execute(input_dict["query"])
        columns = [description[0] for description in cursor.description or ()]
        rows = cursor.fetchmany(input_dict.get("limit", 1000))
        return {
            "status": "success",
            "rows": len(rows),
            "columns": columns,
            "data": [dict(row) for row in rows],
        }
