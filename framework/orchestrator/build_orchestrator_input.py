"""
Utilities for constructing `OrchestratorInput` instances and managing rolling state.

The builder encapsulates prompt templates, state hydration, and incremental updates
that persist across orchestrator runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from framework.orchestrator.data_types import OrchestratorInput
from framework.utils.logger import StructuredLogger

START_USER_PROMPT = """
# Task

You are orchestrating a worker that sees the desktop via screenshots and can execute tools. **Plan the next minimal subgoal and act via tool calls**, grounded strictly in the current screenshot, notes, and progress.

## Inputs

* **initial_task**: `{initial_task}`
* **current_progress** (may be empty):

  ```json
  {current_progress}
  ```
* **current_state_notes** (short, factual bullets):

  ```json
  {current_state_notes}
  ```
* **current_state_image**:

  ```
  {current_state_image}
  ```
* **last_step_telemetry** (optional):

  ```json
  {last_step_telemetry}
  ```

## What to do

1. **Decide state**:

   * If `current_progress` is empty → **start** a new run.
   * If some progress exists and more work remains → **continue**.
   * If the objective is already satisfied with **visible, objective evidence** → **finish**.
   * If blocked or impossible with available tools/permissions → **infeasible** (stuck or impossible).

2. **Plan a short subgoal** (4–8 micro-steps horizon, ≤ 80 words) that measurably advances `{initial_task}`.

   * Prefer anchors in this order: **URL/app identity** > **visible text label** > **nearby anchor text** → **pixels/coordinates** (last resort).
   * Do **not** repeat successful steps; if the screen regressed, issue only the **minimum fix**.

3. **Define exactly one success predicate for the *next* step** (verifier-checkable from the next screenshot or obvious state change). Use one of:

   * `"Visible: <substring> in active window"`
   * `"URL startsWith <prefix>"` or `"URL equals <string>"`
   * `"<button/text> present and enabled"`
   * `"<filename or app name> is the focused window"`

## Output format (TOOLS ONLY)

Choose **one** of the following tools and return it exactly once:

* **Start / Continue** → `continue_or_start`

  * **Start** (when `current_progress` is empty):

    * `current_task` — high-level subgoal, name a tool if it cleanly fits (e.g., *navigate_url*, *paste_and_submit*).
    * `max_steps` — integer in `[4, 8]`.
    * `important_notes` — list of short, factual items distilled from `{initial_task}` (IDs, URLs, constraints).
    * `success_criteria` — single verifier predicate for the *next* step only.
  * **Continue** (when progress exists):

    * `current_task` — the next subgoal now.
    * `max_steps` — integer in `[4, 8]`.

* **Finish** → `finish`

  * Provide `completion_rationale` (1–3 sentences) citing **concrete evidence** from the latest screenshot/progress that the original `{initial_task}` is satisfied.

* **Infeasible** → `infeasible`

  * **Stuck** (hand back to human): provide `stuck_reason` and precise `human_assistance` (the **minimum** action to unblock), and state what you will do immediately after unblocking.
  * **Impossible**: provide `infeasible_reason` naming the missing capability/env (e.g., app unavailable, access denied, paywall, admin rights).

## Constraints

* **Prefer tool calls over text.** Do **not** narrate reasoning or chain-of-thought.
* Keep outputs **short, factual, and actionable**.
* Do **not** invent tool names. If no tool fits or permission is missing, use `infeasible`.
* Respect the planning horizon and single-predicate rule.
"""


@dataclass
class OrchestratorInputBuilder:
    """
    Builds `OrchestratorInput` objects and tracks rolling orchestrator state.

    Responsibilities:
        * hydrate initial fields from observation + system templates
        * maintain progress/telemetry between loop iterations
        * emit log statements that document state transitions
    """

    logger: StructuredLogger = field(default_factory=lambda: StructuredLogger(__name__))
    rolling_progress: Optional[Dict[str, Dict[str, Any]]] = None
    rolling_state_notes: Optional[Dict[str, str]] = None
    rolling_last_step_telemetry: Optional[Dict[str, Dict[str, Any]]] = None

    def build_initial_input(
        self,
        *,
        initial_task: str,
        max_steps: int,
        model_name: str,
        current_state_image: str,
        current_state_notes: Optional[Dict[str, str]] = None,
    ) -> OrchestratorInput:
        """
        Construct the first `OrchestratorInput` for a new orchestrator run.
        """
        prompt = START_USER_PROMPT.format(
            initial_task=initial_task,
            current_progress=self.rolling_progress or {},
            current_state_notes=current_state_notes or self.rolling_state_notes or {},
            current_state_image=current_state_image,
            last_step_telemetry=self.rolling_last_step_telemetry or {},
        )
        self.logger.info("Building initial orchestrator input with prompt template.")
        self.logger.info_lines(
            "Rolling context snapshot:",
            [
                f"progress_keys={list((self.rolling_progress or {}).keys())}",
                f"state_note_keys={list((self.rolling_state_notes or {}).keys())}",
                f"has_last_step_telemetry={bool(self.rolling_last_step_telemetry)}",
            ],
        )
        orchestrator_input = OrchestratorInput(
            initial_task=initial_task,
            max_steps=max_steps,
            model_name=model_name,
            progress=self.rolling_progress,
            last_step_telemetry=self.rolling_last_step_telemetry,
            image_input=current_state_image,
            current_state_notes=current_state_notes or self.rolling_state_notes,
        )
        self.logger.info("Initial orchestrator input constructed successfully.")
        return orchestrator_input

    def update_context(
        self,
        *,
        progress: Optional[Dict[str, Dict[str, Any]]] = None,
        state_notes: Optional[Dict[str, str]] = None,
        last_step_telemetry: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        """
        Persist rolling context between orchestrator iterations.
        """
        self.logger.info("Updating rolling orchestrator context.")
        if progress is not None:
            self.rolling_progress = progress
            self.logger.info(f"- progress updated with keys: {list(progress.keys())}")
        if state_notes is not None:
            self.rolling_state_notes = state_notes
            self.logger.info(f"- state_notes updated with keys: {list(state_notes.keys())}")
        if last_step_telemetry is not None:
            self.rolling_last_step_telemetry = last_step_telemetry
            self.logger.info("- last_step_telemetry updated.")

    def clear_context(self) -> None:
        """
        Reset rolling state, typically when a new task begins.
        """
        self.logger.info("Clearing rolling orchestrator context.")
        self.rolling_progress = None
        self.rolling_state_notes = None
        self.rolling_last_step_telemetry = None


__all__ = ["OrchestratorInputBuilder", "START_USER_PROMPT"]
