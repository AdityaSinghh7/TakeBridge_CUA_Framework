"""Data models for orchestrator agent input/output contracts."""

from dataclasses import dataclass
from typing import Any, Dict, Optional


DEFAULT_MODEL_NAME = "o4-mini"
ALLOWED_STATUS_VALUES = {"success", "fail"}


@dataclass
class OrchestratorInput:
    """Input payload describing how the orchestrator should begin a run."""

    initial_task: str
    max_steps: int
    model_name: str = DEFAULT_MODEL_NAME
    progress: Optional[Dict[str, Dict[str, Any]]] = None
    last_step_telemetry: Optional[Dict[str, Dict[str, str]]] = None
    image_input: Optional[str] = None

    def __post_init__(self) -> None:
        self._validate_initial_task()
        self._validate_max_steps()
        self.model_name = self.model_name or DEFAULT_MODEL_NAME
        self._validate_progress()
        self._validate_last_step_telemetry()
        self._validate_image_input()

    def _validate_initial_task(self) -> None:
        if not self.initial_task or not self.initial_task.strip():
            raise ValueError("initial_task must be a non-empty string.")

    def _validate_max_steps(self) -> None:
        if self.max_steps <= 0:
            raise ValueError("max_steps must be a positive integer.")

    def _validate_progress(self) -> None:
        if self.progress is None:
            return
        if not isinstance(self.progress, dict):
            raise TypeError("progress must be a dict mapping step labels to tool call records.")
        for step_label, record in self.progress.items():
            if not isinstance(step_label, str):
                raise TypeError("progress keys must be strings.")
            self._validate_progress_record(step_label, record)

    def _validate_progress_record(self, step_label: str, record: Any) -> None:
        if not isinstance(record, dict):
            raise TypeError(f"progress[{step_label!r}] must be a dict with function_call_payload, output, and success.")
        required_fields = {"function_call_payload", "output", "success"}
        missing = required_fields - record.keys()
        if missing:
            raise ValueError(f"progress[{step_label!r}] is missing required fields: {missing}.")
        if not isinstance(record["success"], str):
            raise TypeError(f"progress[{step_label!r}]['success'] must be a string.")
        if record["success"] not in ALLOWED_STATUS_VALUES:
            raise ValueError("progress success values must be either 'success' or 'fail'.")
        for field in ("function_call_payload", "output"):
            if not isinstance(record[field], dict):
                raise TypeError(f"progress[{step_label!r}]['{field}'] must be a JSON object (dict).")

    def _validate_last_step_telemetry(self) -> None:
        if self.last_step_telemetry is None:
            return
        if not isinstance(self.last_step_telemetry, dict):
            raise TypeError("last_step_telemetry must be a dict mapping the last step label to telemetry details.")
        for step_label, telemetry in self.last_step_telemetry.items():
            if not isinstance(step_label, str):
                raise TypeError("last_step_telemetry keys must be strings.")
            if not isinstance(telemetry, dict):
                raise TypeError("last_step_telemetry values must be dicts describing the worker step.")
            self._ensure_required_telemetry_fields(step_label, telemetry)
            self._validate_telemetry_content(step_label, telemetry)

    def _ensure_required_telemetry_fields(self, step_label: str, telemetry: Dict[str, str]) -> None:
        required_keys = {"reasoning", "function_call", "success"}
        missing_keys = required_keys - telemetry.keys()
        if missing_keys:
            raise ValueError(f"last_step_telemetry is missing required keys: {missing_keys}.")

    def _validate_telemetry_content(self, step_label: str, telemetry: Dict[str, str]) -> None:
        for key in ("reasoning", "function_call"):
            value = telemetry.get(key)
            if value is not None and not isinstance(value, str):
                raise TypeError(f"last_step_telemetry[{step_label!r}]['{key}'] must be a string or None.")
        status = telemetry.get("success")
        if status not in ALLOWED_STATUS_VALUES:
            raise ValueError("last_step_telemetry success value must be either 'success' or 'fail'.")

    def _validate_image_input(self) -> None:
        if self.image_input is None:
            return
        if not isinstance(self.image_input, str):
            raise TypeError("image_input must be a base64 data URI string.")
        if not self.image_input.startswith("data:"):
            raise ValueError("image_input must be a base64 data URI encoded string (e.g., starting with 'data:').")


@dataclass
class OrchestratorOutput:
    """Output payload summarizing a single tool/function call issued by the orchestrator."""

    function_call_payload: Dict[str, Any]
    output: Dict[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.function_call_payload, dict):
            raise TypeError("function_call_payload must be a JSON object (dict).")
        if not isinstance(self.output, dict):
            raise TypeError("output must be a JSON object (dict).")
