"""Validation helpers for orchestrator data models.

Centralizes all input/output validation logic to keep the dataclass module
clean and focused on structure. Functions raise ValueError/TypeError on
invalid inputs and otherwise return None.
"""

from typing import Any, Dict, Optional


# Canonical status values for step outcomes in progress/telemetry
ALLOWED_STATUS_VALUES = {"success", "fail"}


def validate_initial_task(initial_task: str) -> None:
    if not initial_task or not str(initial_task).strip():
        raise ValueError("initial_task must be a non-empty string.")


def validate_max_steps(max_steps: int) -> None:
    if not isinstance(max_steps, int) or max_steps <= 0:
        raise ValueError("max_steps must be a positive integer.")


def validate_progress(progress: Optional[Dict[str, Dict[str, Any]]]) -> None:
    if progress is None:
        return
    if not isinstance(progress, dict):
        raise TypeError(
            "progress must be a dict mapping step labels to tool call records."
        )
    for step_label, record in progress.items():
        if not isinstance(step_label, str):
            raise TypeError("progress keys must be strings.")
        _validate_progress_record(step_label, record)


def _validate_progress_record(step_label: str, record: Any) -> None:
    if not isinstance(record, dict):
        raise TypeError(
            f"progress[{step_label!r}] must be a dict with function_call_payload, output, and success."
        )
    required_fields = {"function_call_payload", "output", "success"}
    missing = required_fields - record.keys()
    if missing:
        raise ValueError(
            f"progress[{step_label!r}] is missing required fields: {missing}."
        )
    if not isinstance(record["success"], str):
        raise TypeError(
            f"progress[{step_label!r}]['success'] must be a string."
        )
    if record["success"] not in ALLOWED_STATUS_VALUES:
        raise ValueError(
            "progress success values must be either 'success' or 'fail'."
        )
    for field in ("function_call_payload", "output"):
        if not isinstance(record[field], dict):
            raise TypeError(
                f"progress[{step_label!r}]['{field}'] must be a JSON object (dict)."
            )


def validate_last_step_telemetry(
    last_step_telemetry: Optional[Dict[str, Dict[str, Any]]]
) -> None:
    if last_step_telemetry is None:
        return
    if not isinstance(last_step_telemetry, dict):
        raise TypeError(
            "last_step_telemetry must be a dict mapping the last step label to telemetry details."
        )
    for step_label, telemetry in last_step_telemetry.items():
        if not isinstance(step_label, str):
            raise TypeError("last_step_telemetry keys must be strings.")
        if not isinstance(telemetry, dict):
            raise TypeError(
                "last_step_telemetry values must be dicts describing the worker step."
            )
        _ensure_required_telemetry_fields(step_label, telemetry)
        _validate_telemetry_content(step_label, telemetry)


def _ensure_required_telemetry_fields(step_label: str, telemetry: Dict[str, Any]) -> None:
    required_keys = {"reasoning", "function_call", "success"}
    missing_keys = required_keys - telemetry.keys()
    if missing_keys:
        raise ValueError(
            f"last_step_telemetry is missing required keys: {missing_keys}."
        )


def _validate_telemetry_content(step_label: str, telemetry: Dict[str, Any]) -> None:
    for key in ("reasoning", "function_call"):
        value = telemetry.get(key)
        if value is not None and not isinstance(value, str):
            raise TypeError(
                f"last_step_telemetry[{step_label!r}]['{key}'] must be a string or None."
            )
    status = telemetry.get("success")
    if status not in ALLOWED_STATUS_VALUES:
        raise ValueError(
            "last_step_telemetry success value must be either 'success' or 'fail'."
        )


def validate_image_input(image_input: Optional[str]) -> None:
    if image_input is None:
        return
    if not isinstance(image_input, str):
        raise TypeError("image_input must be a base64 data URI string.")
    if not image_input.startswith("data:"):
        raise ValueError(
            "image_input must be a base64 data URI encoded string (e.g., starting with 'data:')."
        )


def validate_orchestrator_output(function_call_payload: Any, output: Any) -> None:
    if not isinstance(function_call_payload, dict):
        raise TypeError("function_call_payload must be a JSON object (dict).")
    if not isinstance(output, dict):
        raise TypeError("output must be a JSON object (dict).")


def validate_current_state_notes(
    current_state_notes: Optional[Dict[str, str]]
) -> None:
    if current_state_notes is None:
        return
    if not isinstance(current_state_notes, dict):
        raise TypeError(
            "current_state_notes must be a dict mapping step labels to strings."
        )
    for step_label, note in current_state_notes.items():
        if not isinstance(step_label, str):
            raise TypeError("current_state_notes keys must be strings.")
        if not isinstance(note, str):
            raise TypeError("current_state_notes values must be strings.")
