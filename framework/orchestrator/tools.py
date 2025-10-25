"""Tool definitions exposed to the orchestrator model."""

from typing import Any, Dict


def continue_start_tool() -> Dict[str, Any]:
    """Tool for starting or continuing the orchestrator loop.

    Choose the schema variant based on the `progress` map in the input:
    - Start: when progress is empty/None. Provide the first subgoal (current_task),
      a short planning horizon (max_steps), and a single immediate success_criteria
      that a verifier LLM will check using the latest image_input, current state,
      and last action.
    - Continue: when progress contains prior steps. Provide the next subgoal
      (current_task) and max_steps.

    Author current_task as a high-level, human-readable subgoal aligned with
    ORCH_SYSTEM guidance: concise, robust to minor UI variation, and naming a
    tool explicitly (e.g., navigate_url, paste_and_submit) when a tool fits the
    action. The success_criteria must be a single, objective, vision/verifier-
    checkable predicate for the next immediate step only (not multi-step), as in
    system_prompts.
    """

    start_variant = {
        "type": "object",
        "description": (
            "Start a new run (no prior progress). Provide the first subgoal as "
            "'current_task', select a short planning horizon via 'max_steps' "
            "(integer in [4, 8]), and include exactly one 'success_criteria' "
            "for the next step only. The verifier LLM will evaluate this single "
            "criterion against the latest image_input, current state, and last action."
        ),
        "properties": {
            "current_task": {
                "type": "string",
                "description": (
                    "The first subgoal the worker must complete now. Use high-level, "
                    "human-readable phrasing and name a specific tool when it matches "
                    "the action."
                ),
                "minLength": 1,
            },
            "max_steps": {
                "type": "integer",
                "description": "Integer in [4, 8] chosen by the model for this subgoal.",
                "minimum": 4,
                "maximum": 8,
            },
            "success_criteria": {
                "type": "string",
                "description": (
                    "A single, objective success check for the next immediate step only; "
                    "concise and vision/verifier-checkable (no multi-step criteria)."
                ),
                "minLength": 1,
            }
        },
        "required": ["current_task", "max_steps", "success_criteria"],
        "additionalProperties": False,
    }

    continue_variant = {
        "type": "object",
        "description": (
            "Continue an in-progress run. Provide the current subtask the worker "
            "should complete now, and the max number of steps for this subgoal."
        ),
        "properties": {
            "current_task": {
                "type": "string",
                "description": "The current subtask the worker must complete next.",
                "minLength": 1,
            },
            "max_steps": {
                "type": "integer",
                "description": "Integer in [4, 8] chosen by the model for this subgoal.",
                "minimum": 4,
                "maximum": 8,
            },
        },
        "required": ["current_task", "max_steps"],
        "additionalProperties": False,
    }

    return {
        "type": "function",
        "function": {
            "name": "continue_or_start",
            "description": (
                "Start the planner loop (progress empty/None) or continue it (progress present). "
                "For start: return 'current_task', 'max_steps' in [4,8], and exactly one 'success_criteria' "
                "for the next immediate step.\n For continue: return 'current_task' and 'max_steps' in [4,8]. "
                "Write current_task per system message's guidance: concise, robust, and reference a named tool when apt. "
                "Success criteria must be a single, objective predicate that a verifier can check using the latest "
                "image_input, current state values, and the worker's last action."
            ),
            "strict": True,
            "parameters": {
                "type": "object",
                "description": (
                    "Choose exactly one variant: start (no prior progress) or continue (some progress)."
                ),
                "oneOf": [start_variant, continue_variant],
            },
        },
    }


def finish_tool() -> Dict[str, Any]:
    """Tool to signal that the initial_task is fully satisfied.

    Use this when the progress map and latest evidence indicate the user's
    initial_task is complete.
    Provide a detailed justification that:
    - Explains why finishing now is correct, grounded in the most recent image_input
      and progress entries.
    - Confirms that the original initial_task has been satisfied per the system
      prompts' guidance (objective, verifier-checkable criteria met).
    """

    return {
        "type": "function",
        "function": {
            "name": "finish",
            "description": (
                "Declare the overall task complete. Include a detailed, objective rationale "
                "that cites the latest image_input and progress map, and explicitly confirms "
                "that the user's initial_task is satisfied according to the stated success criteria."
            ),
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "completion_rationale": {
                        "type": "string",
                        "minLength": 1,
                        "description": (
                            "Detailed reasoning for finishing now, confirming the initial_task is complete, "
                            "and referencing concrete evidence from progress (e.g., tool outputs, URLs, visible UI) "
                            "and the latest image_input."
                        ),
                    }
                },
                "required": ["completion_rationale"],
                "additionalProperties": False,
            },
        },
    }


def infeasible_tool() -> Dict[str, Any]:
    """Tool for either handing back to a human or declaring the task infeasible.

    Two coherent cases aligned with system message's guidance:
    - Stuck/HandBackToHuman: You believe progress has stalled and human
      intervention is needed. Provide why it's stuck and exactly how a human can help.
    - Infeasible: You determine the initial_task cannot be completed given the
      worker's toolset and the current state_image and worker's abilities. Provide a clear rationale.
    """

    stuck_variant = {
        "type": "object",
        "description": (
            "Hand back to a human due to being stuck. Cite concrete blockers from the "
            "progress map and current state_image, then instruct the human precisely on "
            "what assistance is needed to resume."
        ),
        "properties": {
            "stuck_reason": {
                "type": "string",
                "minLength": 1,
                "description": (
                    "Detailed reasoning for why planning/execution is stuck, referencing "
                    "specific steps, tool outputs, or UI constraints seen in current state_image."
                ),
            },
            "human_assistance": {
                "type": "string",
                "minLength": 1,
                "description": (
                    "Concrete, actionable guidance for a human to unblock progress (e.g., "
                    "credentials, enabling permissions, focusing a window, completing a one-time setup)."
                ),
            },
        },
        "required": ["stuck_reason", "human_assistance"],
        "additionalProperties": False,
    }

    infeasible_variant = {
        "type": "object",
        "description": (
            "Declare the user's initial_task infeasible given the worker's tools and the "
            "current environment. Explain precisely why completion is impossible."
        ),
        "properties": {
            "infeasible_reason": {
                "type": "string",
                "minLength": 1,
                "description": (
                    "Detailed rationale for infeasibility grounded in the available toolset, "
                    "system constraints, and what is observable in image_input."
                ),
            }
        },
        "required": ["infeasible_reason"],
        "additionalProperties": False,
    }

    return {
        "type": "function",
        "function": {
            "name": "infeasible",
            "description": (
                "Hand back to a human when stuck, or declare the initial_task infeasible. "
                "For a handback, provide 'stuck_reason' and 'human_assistance' with precise, actionable detail. "
                "For infeasible, provide 'infeasible_reason' explaining why completion is impossible with the "
                "worker's tools and current environment (as seen via image_input and progress)."
            ),
            "strict": True,
            "parameters": {
                "type": "object",
                "description": "Choose exactly one variant: hand back (stuck) or infeasible.",
                "oneOf": [stuck_variant, infeasible_variant],
            },
        },
    }
