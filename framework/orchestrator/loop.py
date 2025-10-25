"""
Core orchestrator loop skeleton.

The `OrchestratorLoop` class exposes a single `run()` method that accepts an
`OrchestratorInput` and returns an `OrchestratorOutput`. The server layer
(`framework/api/server.py`) is responsible for wiring HTTP requests into this
loop. Concrete orchestration logic will be added incrementally.
"""

from __future__ import annotations

from typing import Optional, Tuple, List, Dict, Any

from framework.api.oai_client import OAIClient, ResponseSession, Response
from framework.orchestrator.build_orchestrator_input import (
    OrchestratorInputBuilder,
    snapshot_to_state_notes,
)
from framework.orchestrator.data_types import OrchestratorInput, OrchestratorOutput
from framework.orchestrator.system_prompts import ORCH_DEVELOPER_GUIDANCE
from framework.orchestrator.tools import (
    continue_start_tool,
    finish_tool,
    infeasible_tool,
)
from framework.utils.logger import StructuredLogger
from framework.vm_controller.observe import VMObserver


class OrchestratorLoop:
    """
    Placeholder loop that will eventually orchestrate the full agent flow.

    As capabilities grow, this class should coordinate observation, planning,
    tool execution, and result aggregation.
    """

    def __init__(self) -> None:
        self._logger = StructuredLogger(__name__)
        self._observer = VMObserver()
        self._input_builder = OrchestratorInputBuilder()
        self._oai_client = OAIClient()
        self._session = ResponseSession()

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

        snapshot = self._observer.snapshot(
            include_screenshot=True,
            encode_screenshot=True,
            downsample=True,
            max_width=1280,
            max_height=720,
        )
        image_data_uri: Optional[str] = None
        if snapshot.screenshot_b64:
            image_data_uri = f"data:image/png;base64,{snapshot.screenshot_b64}"

        snapshot_notes = snapshot_to_state_notes(snapshot)
        self._input_builder.update_context(
            progress=orchestrator_input.progress,
            state_notes=snapshot_notes,
            last_step_telemetry=orchestrator_input.last_step_telemetry,
        )
        enriched_input, user_prompt = self._input_builder.build_initial_input(
            initial_task=orchestrator_input.initial_task,
            max_steps=orchestrator_input.max_steps,
            model_name=orchestrator_input.model_name,
            current_state_image=image_data_uri or orchestrator_input.image_input,
            current_state_notes=snapshot_notes,
        )
        self._logger.info("Orchestrator input enriched with fresh VM snapshot.")

        for step in range(1, orchestrator_input.max_steps + 1):
            self._logger.info(f"Starting orchestrator iteration {step}/{orchestrator_input.max_steps}")
            messages = [
                {"role": "developer", "content": ORCH_DEVELOPER_GUIDANCE},
                {"role": "user", "content": user_prompt},
            ]
            tools_payload = [
                continue_start_tool(),
                finish_tool(),
                infeasible_tool(),
            ]
            self._logger.info("Prepared messages and tool payload for orchestrator LLM call.")
            response = self._oai_client.respond_with_session(
                self._session,
                messages=messages,
                tools=tools_payload,
                max_output_tokens=4092 * 3,
                reasoning_effort="medium",
                reasoning_summary="auto",
            )
            function_call = self._extract_function_call(response)
            if function_call is None:
                self._logger.info("No function call returned; terminating orchestrator loop.")
                break

            tool_name = function_call.get("name")
            arguments = function_call.get("arguments") or {}
            self._logger.info(f"Received tool call: {tool_name}")

            if tool_name == "finish":
                self._logger.info("Finish tool invoked; concluding orchestration.")
                return OrchestratorOutput(
                    function_call_payload={"tool": tool_name, "arguments": arguments},
                    output={"status": "finished", "completion_rationale": arguments.get("completion_rationale")},
                )
            if tool_name == "infeasible":
                self._logger.info("Infeasible tool invoked; concluding orchestration.")
                return OrchestratorOutput(
                    function_call_payload={"tool": tool_name, "arguments": arguments},
                    output={"status": "infeasible", "details": arguments},
                )

            if tool_name == "continue_or_start":
                self._logger.info("continue_or_start tool invoked; delegating to worker agent stub.")
                self._handle_continue_or_start(arguments)
            else:
                error_message = f"Unhandled tool '{tool_name}' received from orchestrator LLM."
                self._logger.info(error_message)
                raise RuntimeError(error_message)

    def _extract_function_call(self, response: Response) -> Optional[Dict[str, Any]]:
        for item in getattr(response, "output", []) or []:
            if item.get("type") == "function_call":
                return {
                    "name": item.get("name"),
                    "arguments": item.get("arguments"),
                }
        return None

    def _handle_continue_or_start(self, arguments: Dict[str, Any]) -> None:
        self._logger.info("Worker agent execution stub: continue_or_start arguments received.")
        self._logger.info_lines(
            "continue_or_start payload:",
            [f"{key}: {value}" for key, value in arguments.items()],
        )
        return OrchestratorOutput(
            function_call_payload={"tool": "continue_or_start", "arguments": arguments},
            output={"status": "not_implemented"},
        )


__all__ = ["OrchestratorLoop"]
