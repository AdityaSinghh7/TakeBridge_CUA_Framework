"""Reference JSON formats for orchestrator inputs.

This module documents canonical JSON shapes (and examples) we intend to use
for orchestrator planning state. Keep these in sync with:
- framework/orchestrator/data_types.py
- framework/orchestrator/system_prompts.py

Notes on coherence vs. current implementation:
- "progress" below mirrors OrchestratorInput.progress: a mapping of step labels
  (e.g., "Step 1") to a record that includes reasoning, function_call_payload,
  output, and success. Success uses the canonical string values 'success'|'fail'.
- "last_step_telemetry" here includes the last step's detail. The current
  dataclass requires at least reasoning, function_call, and success; it allows
  additional fields like output. Do not include unrelated keys at the same
  object level (e.g., initial_task) in the live payload until the type is
  updated; track initial_task separately via OrchestratorInput.initial_task.
"""

from typing import Any, Dict


# -----------------------------
# Progress (per-step records)
# -----------------------------

# JSON Schema (draft-07 style) describing the mapping of steps to records.
PROGRESS_JSON_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Orchestrator Progress Map",
    "type": "object",
    "description": (
        "Mapping of step labels (e.g., 'Step 1') to tool call records."
    ),
    "additionalProperties": {
        "type": "object",
        "required": ["reasoning", "function_call_payload", "output", "success"],
        "additionalProperties": True,
        "properties": {
            "reasoning": {"type": "string", "minLength": 1},
            "function_call_payload": {
                "type": "object",
                "description": (
                    "The exact tool/function call payload issued by the model."
                ),
            },
            "output": {
                "type": "object",
                "description": (
                    "The tool/function's JSON output (any shape)."
                ),
            },
            "success": {
                "type": "string",
                "enum": ["success", "fail"],
                "description": "Outcome of the tool call for this step.",
            },
        },
    },
}


# Example coherent progress payload
PROGRESS_EXAMPLE: Dict[str, Any] = {
    "Step 1": {
        "reasoning": "Open the docs in a new browser tab to gather context.",
        "function_call_payload": {
            "name": "continue_or_start",
            "arguments": {
                "current_task": "new_tab_and_go to https://example.com/docs",
                "max_steps": 6,
            },
        },
        "output": {"status": "ok", "tab_opened": True},
        "success": "success",
    },
    "Step 2": {
        "reasoning": "Search for the specific API section using find_in_page.",
        "function_call_payload": {
            "name": "continue_or_start",
            "arguments": {
                "current_task": "find_in_page for 'Authentication'",
                "max_steps": 5,
            },
        },
        "output": {"status": "ok", "matches": 3},
        "success": "success",
    },
}


# ---------------------------------
# Last-step telemetry (diagnostics)
# ---------------------------------

# JSON Schema for a single last-step telemetry record.
LAST_STEP_TELEMETRY_JSON_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Last Step Telemetry",
    "type": "object",
    "required": ["reasoning", "function_call", "success"],
    "additionalProperties": True,
    "properties": {
        "reasoning": {"type": "string", "minLength": 1},
        "function_call": {
            "type": "object",
            "description": (
                "The exact worker function call with name and arguments used at the last step."
            ),
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "arguments": {"type": "object"},
            },
            "required": ["name"],
        },
        "output": {
            "type": "object",
            "description": "The worker function's JSON output (any shape).",
        },
        "success": {"type": "string", "enum": ["success", "fail"]},
    },
}


# Example last-step telemetry payload (kept separate from initial_task).
LAST_STEP_TELEMETRY_EXAMPLE: Dict[str, Any] = {
    "step_label": "Step 2",
    "record": {
        "reasoning": "Attempted to paste credentials and submit the form.",
        "function_call": {
            "name": "paste_and_submit",
            "arguments": {"text": "<redacted>"},
        },
        "output": {"status": "error", "reason": "Field not focused"},
        "success": "fail",
    },
    # Keep the authoritative initial task in OrchestratorInput.initial_task.
}

