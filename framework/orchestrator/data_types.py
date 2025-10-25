"""Data models for orchestrator agent input/output contracts."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .validation import (
    validate_initial_task,
    validate_max_steps,
    validate_progress,
    validate_last_step_telemetry,
    validate_image_input,
    validate_current_state_notes,
    validate_orchestrator_output,
)


DEFAULT_MODEL_NAME = "o4-mini"


@dataclass
class OrchestratorInput:
    """Input payload describing how the orchestrator should begin a run."""

    initial_task: str
    max_steps: int
    model_name: str = DEFAULT_MODEL_NAME
    progress: Optional[Dict[str, Dict[str, Any]]] = None
    last_step_telemetry: Optional[Dict[str, Dict[str, Any]]] = None
    image_input: Optional[str] = None
    current_state_notes: Optional[Dict[str, str]] = None

    def __post_init__(self) -> None:
        # Normalize defaults
        self.model_name = self.model_name or DEFAULT_MODEL_NAME
        # Delegate validation to centralized helpers
        validate_initial_task(self.initial_task)
        validate_max_steps(self.max_steps)
        validate_progress(self.progress)
        validate_last_step_telemetry(self.last_step_telemetry)
        validate_image_input(self.image_input)
        validate_current_state_notes(self.current_state_notes)

    

@dataclass
class OrchestratorOutput:
    """Output payload summarizing a single tool/function call issued by the orchestrator."""

    function_call_payload: Dict[str, Any]
    output: Dict[str, Any]

    def __post_init__(self) -> None:
        validate_orchestrator_output(self.function_call_payload, self.output)
