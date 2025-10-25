"""Tool definitions exposed to the orchestrator model."""

from typing import Any, Dict


def continue_start_tool() -> Dict[str, Any]:
    """Start a new subgoal or continue with the next subgoal.

    Start when progress is empty/None; otherwise continue. Keep current_task concise and robust,
    naming a worker tool when it cleanly fits. For a start, also return a single immediate
    success_criteria and initial important_notes distilled from the initial_task.
    """

    start_variant = {
        "type": "object",
        "description": "Start a new run (no prior progress).",
        "properties": {
            "current_task": {"type": "string", "minLength": 1},
            "max_steps": {"type": "integer", "minimum": 4, "maximum": 8},
            "important_notes": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
                "minItems": 1,
            },
            "success_criteria": {"type": "string", "minLength": 1},
        },
        "required": ["current_task", "max_steps", "important_notes", "success_criteria"],
        "additionalProperties": False,
    }

    continue_variant = {
        "type": "object",
        "description": "Continue an in-progress run.",
        "properties": {
            "current_task": {"type": "string", "minLength": 1},
            "max_steps": {"type": "integer", "minimum": 4, "maximum": 8},
        },
        "required": ["current_task", "max_steps"],
        "additionalProperties": False,
    }

    return {
        "type": "function",
        "name": "continue_or_start",
        "description": (
            "Start the planner loop (no prior progress) or continue it (progress present). "
            "Start: return current_task, max_steps [4,8], important_notes[], and exactly one success_criteria. "
            "Continue: return current_task and max_steps [4,8]."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "description": "Choose exactly one variant: start or continue.",
            "oneOf": [start_variant, continue_variant],
            # Optional discriminator if variants add a 'mode' field
            # "discriminator": {"propertyName": "mode"},
        },
    }


def finish_tool() -> Dict[str, Any]:
    """Declare the task complete with an objective, evidence-based rationale."""

    return {
        "type": "function",
        "name": "finish",
        "description": (
            "Declare the overall task complete with an objective rationale citing the latest image and progress evidence."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "completion_rationale": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 2000,
                }
            },
            "required": ["completion_rationale"],
            "additionalProperties": False,
        },
    }


def infeasible_tool() -> Dict[str, Any]:
    """Hand back to a human when stuck, or declare the task infeasible."""

    stuck_variant = {
        "type": "object",
        "description": "Hand back to a human due to being stuck.",
        "properties": {
            "stuck_reason": {"type": "string", "minLength": 1},
            "human_assistance": {"type": "string", "minLength": 1},
        },
        "required": ["stuck_reason", "human_assistance"],
        "additionalProperties": False,
    }

    infeasible_variant = {
        "type": "object",
        "description": "Declare the task infeasible with current tools/environment.",
        "properties": {
            "infeasible_reason": {"type": "string", "minLength": 1},
        },
        "required": ["infeasible_reason"],
        "additionalProperties": False,
    }

    return {
        "type": "function",
        "name": "infeasible",
        "description": "Hand back to a human when stuck, or declare the task infeasible.",
        "strict": True,
        "parameters": {
            "type": "object",
            "description": "Choose exactly one variant: stuck or infeasible.",
            "oneOf": [stuck_variant, infeasible_variant],
            # Optional discriminator if variants add a 'mode' field
            # "discriminator": {"propertyName": "mode"},
        },
    }
