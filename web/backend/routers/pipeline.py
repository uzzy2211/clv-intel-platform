"""
pipeline.py — Pipeline API Router

Provides endpoints to trigger ML pipeline re-runs and check pipeline status.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException
from schemas import PipelineRunResponse, PipelineStatusResponse
from services.data_service import get_data_service
from services.ml_service import run_full_pipeline

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

# Simple in-memory state for pipeline run status
_pipeline_state = {"running": False, "last_message": None, "last_duration": None}


def _run_and_reload(state: dict) -> None:
    """Background task: run pipeline then reload data service."""
    state["running"] = True
    success, message, duration = run_full_pipeline()
    state["running"] = False
    state["last_message"] = message
    state["last_duration"] = duration
    if success:
        get_data_service().reload()


@router.post("/run", response_model=PipelineRunResponse)
def trigger_pipeline(background_tasks: BackgroundTasks) -> PipelineRunResponse:
    """Trigger a full ML pipeline re-run in the background."""
    if _pipeline_state["running"]:
        raise HTTPException(status_code=409, detail="Pipeline is already running.")

    background_tasks.add_task(_run_and_reload, _pipeline_state)
    return PipelineRunResponse(
        success=True,
        message="Pipeline started in background. Reload data after completion.",
        duration_seconds=None,
    )


@router.get("/status", response_model=PipelineStatusResponse)
def get_pipeline_status() -> PipelineStatusResponse:
    """Return the last pipeline run status and metrics."""
    svc = get_data_service()
    runs = svc.runs_data

    return PipelineStatusResponse(
        last_run=runs.get("last_run"),
        algorithm=runs.get("algorithm", "kmeans"),
        optimal_k=runs.get("optimal_k", 0),
        metrics=runs.get("metrics", {}),
        segment_counts=runs.get("segment_counts", {}),
    )
