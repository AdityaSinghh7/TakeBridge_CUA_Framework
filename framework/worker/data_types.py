"""Data models shared across worker components."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TypedDict


class FunctionCallBody(TypedDict):
    """Shape of the function call emitted by a worker."""

    tool_name: str
    parameters: Dict[str, Any]


@dataclass
class WorkerBaseInputPayload:
    """Common fields passed to the worker irrespective of the step type."""

    current_task: str
    max_steps: int
    step_history: List[Dict[str, Any]] = field(default_factory=list)
    current_state_screenshot: Optional[str] = None


@dataclass
class WorkerStartInputPayload(WorkerBaseInputPayload):
    """Payload used when the worker starts a task."""

    important_notes: Optional[str] = None
    success_criteria: Optional[str] = None


@dataclass
class WorkerContinueInputPayload(WorkerBaseInputPayload):
    """Payload used for subsequent worker iterations."""


@dataclass
class WorkerOutputPayload:
    """Worker response describing the selected tool call and its intent."""

    function_call_body: FunctionCallBody
    reasoning: str
    expected_outcome: str


__all__ = [
    "FunctionCallBody",
    "WorkerBaseInputPayload",
    "WorkerStartInputPayload",
    "WorkerContinueInputPayload",
    "WorkerOutputPayload",
]
