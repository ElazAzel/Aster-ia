from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket

from asterion_api.dependencies import get_workflow_runner
from asterion_api.schemas import WorkflowConfirmRequest, WorkflowRunRequest
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


@router.websocket("/events")
async def workflow_events(
    websocket: WebSocket,
    runner: WorkflowRunner = Depends(get_workflow_runner),
) -> None:
    await websocket.accept()
    while True:
        event = await runner.events.get()
        await websocket.send_json(event)
