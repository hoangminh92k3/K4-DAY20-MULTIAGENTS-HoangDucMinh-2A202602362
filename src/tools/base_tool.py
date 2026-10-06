"""Shared contract for tools exposed to worker agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from functools import wraps
import logging
from typing import Any


class BaseTool(ABC):
    """A named operation that validates an object input before execution."""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Wrap concrete tool calls with consistent execution/error logging."""
        super().__init_subclass__(**kwargs)
        invoke = cls.__dict__.get("invoke")
        if invoke is None or getattr(invoke, "__isabstractmethod__", False):
            return

        @wraps(invoke)
        def logged_invoke(self: "BaseTool", input_dict: Mapping[str, Any]) -> Any:
            self.logger.info("Tool %s started", self.name)
            try:
                result = invoke(self, input_dict)
            except Exception:
                self.logger.exception("Tool %s failed", self.name)
                raise
            self.logger.info("Tool %s completed", self.name)
            return result

        cls.invoke = logged_invoke

    def __init__(self, name: str, description: str):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("tool name must be a non-empty string")
        if not isinstance(description, str) or not description.strip():
            raise ValueError("tool description must be a non-empty string")
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"tools.{name}")

    @abstractmethod
    def invoke(self, input_dict: Mapping[str, Any]) -> Any:
        """Execute the tool after calling :meth:`validate_input`."""

    def validate_input(self, input_dict: Mapping[str, Any]) -> None:
        """Validate the common object input shape used by all tools."""
        if not isinstance(input_dict, Mapping):
            raise ValueError(f"{self.name} expects an object input")
