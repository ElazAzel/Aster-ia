from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from asterion_api.dependencies import get_agent_registry, get_agent_sandbox, get_task_simulator
from asterion_api.schemas import AgentCatalog, AgentManifest, AgentPlan, AgentRunCodeRequest, RuntimeSkillManifest
from asterion_api.services.agent_registry import AgentRegistry
from asterion_api.services.agent_sandbox import AgentSandbox, TaskSimulator

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("/catalog", response_model=AgentCatalog)
async def catalog(
    registry: AgentRegistry = Depends(get_agent_registry),
) -> AgentCatalog:
    return registry.catalog()


@router.get("/catalog/agents", response_model=list[AgentManifest])
async def list_agent_manifests(
    registry: AgentRegistry = Depends(get_agent_registry),
) -> list[AgentManifest]:
    return registry.list_agents()


@router.get("/catalog/skills", response_model=list[RuntimeSkillManifest])
async def list_skill_manifests(
    registry: AgentRegistry = Depends(get_agent_registry),
) -> list[RuntimeSkillManifest]:
    return registry.list_skills()


@router.get("/catalog/agents/{agent_id}", response_model=AgentManifest)
async def get_agent_manifest(
    agent_id: str,
    registry: AgentRegistry = Depends(get_agent_registry),
) -> AgentManifest:
    agent = registry.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


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
    try:
        return await sandbox.run_code(code=request.code, permissions=request.permissions)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Code execution failed: {exc}")
