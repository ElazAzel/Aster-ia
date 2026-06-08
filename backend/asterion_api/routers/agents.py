from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from asterion_api.dependencies import (
    get_agent_executor,
    get_agent_registry,
    get_agent_sandbox,
    get_store,
    get_task_simulator,
)
from asterion_api.schemas import (
    AgentCatalog,
    AgentManifest,
    AgentPlan,
    AgentRun,
    AgentRunCodeRequest,
    AgentRunCreateRequest,
    AgentRunUpdateRequest,
    FlightRecorderEvent,
    RuntimeSkillManifest,
)
from asterion_api.services.agent_executor import AgentExecutor
from asterion_api.services.agent_registry import AgentRegistry
from asterion_api.services.agent_sandbox import AgentSandbox, TaskSimulator
from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore

router = APIRouter(prefix="/api/agents", tags=["agents"])

_CODE_RATE_LIMIT = 5
_CODE_RATE_WINDOW = 60
_code_history: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=_CODE_RATE_LIMIT * 2))


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
    request: Request,
    payload: AgentRunCodeRequest,
    sandbox: AgentSandbox = Depends(get_agent_sandbox),
) -> dict[str, object]:
    client_ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()
    history = _code_history[client_ip]
    while history and history[0] < now - _CODE_RATE_WINDOW:
        history.popleft()
    if len(history) >= _CODE_RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={"detail": f"Code execution rate limit: {_CODE_RATE_LIMIT} requests per minute."},
        )
    history.append(now)
    try:
        return await sandbox.run_code(code=payload.code, permissions=payload.permissions)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Code execution failed: {exc}")


@router.post("/runs", response_model=AgentRun)
async def create_run(
    request: AgentRunCreateRequest,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> AgentRun:
    plan_dict = request.plan.model_dump() if request.plan else {"steps": [], "estimated_tokens": 0}
    perms_dict = request.permissions.model_dump()
    row = await store.create_agent_run(
        agent_id=request.agent_id,
        room_id=request.room_id,
        task=request.task,
        plan=plan_dict,
        permissions=perms_dict,
    )
    return AgentRun(**row)


@router.get("/runs/{run_id}", response_model=AgentRun)
async def get_run(
    run_id: str,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> AgentRun:
    row = await store.get_agent_run(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return AgentRun(**row)


@router.patch("/runs/{run_id}", response_model=AgentRun)
async def update_run(
    run_id: str,
    request: AgentRunUpdateRequest,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> AgentRun:
    row = await store.update_agent_run(run_id, status=request.status, agent_id=request.agent_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return AgentRun(**row)


@router.get("/runs/{run_id}/logs", response_model=list[FlightRecorderEvent])
async def list_run_logs(
    run_id: str,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> list[FlightRecorderEvent]:
    rows = await store.list_agent_logs(run_id)
    return [FlightRecorderEvent(**row) for row in rows]


@router.post("/runs/{run_id}/execute")
async def execute_run(
    run_id: str,
    executor: AgentExecutor = Depends(get_agent_executor),
    store: EncryptedSQLiteStore = Depends(get_store),
) -> dict[str, str]:
    row = await store.get_agent_run(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Agent run not found")
    if row["status"] not in ("planned",):
        raise HTTPException(status_code=409, detail=f"Run status '{row['status']}' is not executable")
    import asyncio
    asyncio.create_task(executor.execute_run(run_id))
    return {"status": "executing", "run_id": run_id}
