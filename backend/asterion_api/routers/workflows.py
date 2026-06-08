from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from asterion_api.dependencies import get_workflow_runner
from asterion_api.schemas import WorkflowConfirmRequest, WorkflowRunRequest, WorkflowRunStatus
from asterion_api.services.workflow_runner import WorkflowRunner

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.post("/run")
async def run_workflow(
    request: WorkflowRunRequest,
    runner: WorkflowRunner = Depends(get_workflow_runner),
) -> dict[str, object]:
    try:
        return await runner.run(request.workflow)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Workflow failed: {exc}")


@router.post("/confirm")
async def confirm_workflow(
    request: WorkflowConfirmRequest,
    runner: WorkflowRunner = Depends(get_workflow_runner),
) -> dict[str, bool]:
    confirmed = runner.confirm(request.run_id, request.approved, request.payload)
    if not confirmed:
        raise HTTPException(status_code=404, detail="No paused workflow found for this run_id")
    return {"confirmed": True}


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
    try:
        while True:
            event = await runner.events.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass
