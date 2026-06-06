from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from asterion_api.dependencies import get_agent_registry, get_agent_sandbox, get_store, get_task_simulator
from asterion_api.schemas import (
    AgentCatalog,
    AgentManifest,
    AgentPlan,
    AgentRun,
    AgentRunCodeRequest,
    AgentRunCreateRequest,
    FlightRecorderEvent,
    RuntimeSkillManifest,
)
from asterion_api.services.agent_registry import AgentRegistry
from asterion_api.services.agent_sandbox import AgentSandbox, TaskSimulator
from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore

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


@router.get("/catalog/validate")
async def validate_catalog(
    registry: AgentRegistry = Depends(get_agent_registry),
) -> dict[str, object]:
    return registry.validate_catalog()


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
    return await sandbox.run_code(code=request.code, permissions=request.permissions)


@router.post("/runs", response_model=AgentRun)
async def create_agent_run(
    request: AgentRunCreateRequest,
    simulator: TaskSimulator = Depends(get_task_simulator),
    store: EncryptedSQLiteStore = Depends(get_store),
) -> AgentRun:
    plan = request.plan or simulator.plan(request.task)
    row = await store.create_agent_run(
        agent_id=request.agent_id,
        room_id=request.room_id,
        status="planned",
        plan=plan.model_dump(),
        permissions=request.permissions.model_dump(),
    )
    await store.append_agent_log(
        run_id=str(row["id"]),
        action="plan.created",
        tool="TaskSimulator",
        privacy_level="local",
        input_text=request.task,
        output_text=json.dumps(plan.model_dump(), ensure_ascii=False),
        model=None,
        error=None,
    )
    return AgentRun(**row)


@router.get("/runs/{run_id}", response_model=AgentRun)
async def get_agent_run(
    run_id: str,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> AgentRun:
    row = await store.get_agent_run(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return AgentRun(**row)


@router.post("/runs/{run_id}/code")
async def run_agent_code(
    run_id: str,
    request: AgentRunCodeRequest,
    sandbox: AgentSandbox = Depends(get_agent_sandbox),
    store: EncryptedSQLiteStore = Depends(get_store),
) -> dict[str, object]:
    result = await sandbox.run_code(code=request.code, permissions=request.permissions)
    await store.append_agent_log(
        run_id=run_id,
        action="run_code",
        tool="python_sandbox",
        privacy_level="local",
        input_text=request.code[:500],
        output_text=result.get("stdout", "")[:500],
        error=result.get("stderr") or None,
    )
    return result


@router.get("/runs/{run_id}/logs", response_model=list[FlightRecorderEvent])
async def list_agent_run_logs(
    run_id: str,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> list[FlightRecorderEvent]:
    return [FlightRecorderEvent(**row) for row in await store.list_agent_logs(run_id)]


@router.get("/runs/{run_id}/events")
async def stream_agent_run_events(
    run_id: str,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> StreamingResponse:
    async def events():
        rows = await store.list_agent_logs(run_id)
        for row in rows:
            yield f"data: {json.dumps(row, ensure_ascii=False)}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
