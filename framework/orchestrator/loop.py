"""
Core orchestrator loop skeleton.

The `OrchestratorLoop` class exposes a single `run()` method that accepts an
`OrchestratorInput` and returns an `OrchestratorOutput`. The server layer
(`framework/api/server.py`) is responsible for wiring HTTP requests into this
loop. Concrete orchestration logic will be added incrementally.
"""

from __future__ import annotations

from framework.orchestrator.data_types import OrchestratorInput, OrchestratorOutput
from framework.utils.logger import StructuredLogger


class OrchestratorLoop:
    """
    Placeholder loop that will eventually orchestrate the full agent flow.

    As capabilities grow, this class should coordinate observation, planning,
    tool execution, and result aggregation.
    """

    def __init__(self) -> None:
        self._logger = StructuredLogger(__name__)

    def run(self, orchestrator_input: OrchestratorInput) -> OrchestratorOutput:
        """
        Kick off a single orchestrator cycle.

        Args:
            orchestrator_input: Validated dataclass describing the requested run.

        Returns:
            OrchestratorOutput detailing the action the orchestrator decided to take.
        """
        self._logger.info("Received orchestrator input payload:")
        input_lines = [
            f"initial_task={orchestrator_input.initial_task}",
            f"max_steps={orchestrator_input.max_steps}",
            f"model_name={orchestrator_input.model_name}",
            f"progress_keys={list((orchestrator_input.progress or {}).keys())}",
            f"has_last_step_telemetry={bool(orchestrator_input.last_step_telemetry)}",
            f"has_image_input={bool(orchestrator_input.image_input)}",
            f"has_current_state_notes={bool(orchestrator_input.current_state_notes)}",
        ]
        self._logger.info_lines(None, input_lines)

        for step in range(1, orchestrator_input.max_steps + 1):
            self._logger.info(f"Starting orchestrator iteration {step}/{orchestrator_input.max_steps}")
            # TODO: integrate observation, prompt construction, LLM calls, tool execution.
            break  # Placeholder: exit after first iteration until logic is implemented.

        function_call_payload = {"action": "noop", "metadata": {"step": 1}}
        output = {"status": "not_implemented"}
        return OrchestratorOutput(
            function_call_payload=function_call_payload,
            output=output,
        )


__all__ = ["OrchestratorLoop"]
