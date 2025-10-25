"""
FastAPI server that exposes the orchestrator loop.

Input/output contracts are defined in `framework.orchestrator.data_types`.
The endpoint performs dataclass validation and returns JSON payloads that
mirror those structures.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, is_dataclass
from typing import Any, Dict

from fastapi import Body, FastAPI, HTTPException

from framework.orchestrator.data_types import OrchestratorInput, OrchestratorOutput
from framework.orchestrator.loop import OrchestratorLoop

logger = logging.getLogger(__name__)

app = FastAPI(title="TakeBridge Orchestrator API", version="0.1.0")


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    if is_dataclass(instance):
        return asdict(instance)
    raise TypeError(f"Expected dataclass instance, got {type(instance)!r}")


@app.post("/orchestrate")
async def orchestrate(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Run a single orchestrator loop using the shared dataclass contracts.
    """
    try:
        orchestrator_input = OrchestratorInput(**payload)
    except (TypeError, ValueError) as exc:
        logger.debug("Invalid orchestrator input: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    loop = OrchestratorLoop()
    try:
        orchestrator_output = loop.run(orchestrator_input)
    except Exception as exc:  # pragma: no cover - placeholder error handling
        logger.exception("Orchestrator loop failed: %s", exc)
        raise HTTPException(status_code=500, detail="Orchestrator execution failed.") from exc

    return _dataclass_to_dict(orchestrator_output)


__all__ = ["app"]
