from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket, HTTPException

from asterion_api.dependencies import get_workflow_runner
from asterion_api.schemas import WorkflowConfirmRequest, WorkflowRunRequest, WorkflowRunStatus
from asterion_api.services.workflow_runner import WorkflowRunner

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.post("/run")
async def run_workflow(
    request: WorkflowRunRequest,
    runner: WorkflowRunner = Depends(get_workflow_runner),
) -> dict[str, object]:
    return await runner.run(request.workflow)


@router.post("/confirm")
async def confirm_workflow(
    request: WorkflowConfirmRequest,
    runner: WorkflowRunner = Depends(get_workflow_runner),
) -> dict[str, bool]:
    return {"confirmed": runner.confirm(request.run_id, request.approved, request.payload)}


@router.get("/runs", response_model=list[WorkflowRunStatus])
async def list_active_runs(
    runner: WorkflowRunner = Depends(get_workflow_runner),
) -> list[WorkflowRunStatus]:
    runs = await runner.store.list_active_workflow_runs()
    return [WorkflowRunStatus(**run) for run in runs]


@router.get("/runs/{run_id}", response_model=WorkflowRunStatus)
async def get_run_status(
    run_id: str,
    runner: WorkflowRunner = Depends(get_workflow_runner),
) -> WorkflowRunStatus:
    run = await runner.store.get_workflow_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return WorkflowRunStatus(**run)


@router.websocket("/events")
async def workflow_events(
    websocket: WebSocket,
    runner: WorkflowRunner = Depends(get_workflow_runner),
) -> None:
    await websocket.accept()
    while True:
        event = await runner.events.get()
        await websocket.send_json(event)
