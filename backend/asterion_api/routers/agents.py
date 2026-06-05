from __future__ import annotations

from fastapi import APIRouter, Depends

from asterion_api.dependencies import get_agent_sandbox, get_task_simulator
from asterion_api.schemas import AgentPlan, AgentRunCodeRequest
from asterion_api.services.agent_sandbox import AgentSandbox, TaskSimulator

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.post("/simulate", response_model=AgentPlan)
async def simulate_task(
    payload: dict[str, str],
    simulator: TaskSimulator = Depends(get_task_simulator),
) -> AgentPlan:
    return simulator.plan(payload.get("task", ""))


@router.post("/run-code")
async def run_code(
    request: AgentRunCodeRequest,
    sandbox: AgentSandbox = Depends(get_agent_sandbox),
) -> dict[str, object]:
    return await sandbox.run_code(code=request.code, permissions=request.permissions)
