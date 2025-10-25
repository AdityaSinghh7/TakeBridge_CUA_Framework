"""
Core orchestrator loop skeleton.

The `OrchestratorLoop` class exposes a single `run()` method that accepts an
`OrchestratorInput` and returns an `OrchestratorOutput`. The server layer
(`framework/api/server.py`) is responsible for wiring HTTP requests into this
loop. Concrete orchestration logic will be added incrementally.
"""

from __future__ import annotations

from framework.orchestrator.data_types import OrchestratorInput, OrchestratorOutput


class OrchestratorLoop:
    """
    Placeholder loop that will eventually orchestrate the full agent flow.

    As capabilities grow, this class should coordinate observation, planning,
    tool execution, and result aggregation.
    """

    def run(self, orchestrator_input: OrchestratorInput) -> OrchestratorOutput:
        """
        Kick off a single orchestrator cycle.

        Args:
            orchestrator_input: Validated dataclass describing the requested run.

        Returns:
            OrchestratorOutput detailing the action the orchestrator decided to take.
        """
        # TODO: integrate observation, prompt construction, LLM calls, tool execution.
        placeholder_payload = {
            "initial_task": orchestrator_input.initial_task,
            "model": orchestrator_input.model_name,
        }
        function_call_payload = {"action": "noop", "metadata": placeholder_payload}
        output = {"status": "not_implemented"}
        return OrchestratorOutput(
            function_call_payload=function_call_payload,
            output=output,
        )


__all__ = ["OrchestratorLoop"]
