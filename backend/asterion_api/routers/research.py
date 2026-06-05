from __future__ import annotations

from fastapi import APIRouter, Depends

from asterion_api.dependencies import get_contradiction_finder, get_supervisor_agent
from asterion_api.schemas import (
    ContradictionMatch,
    ContradictionRequest,
    DeepResearchRequest,
    DeepResearchResponse,
)
from asterion_api.services.contradiction_finder import ContradictionFinder
from asterion_api.services.deep_research import SupervisorAgent

router = APIRouter(prefix="/api/research", tags=["research"])


@router.post("/deep", response_model=DeepResearchResponse)
async def deep_research(
    request: DeepResearchRequest,
    supervisor: SupervisorAgent = Depends(get_supervisor_agent),
) -> DeepResearchResponse:
    return await supervisor.research(
        query=request.query,
        max_subtasks=request.max_subtasks,
        web_access=request.web_access,
    )


@router.post("/contradictions", response_model=list[ContradictionMatch])
async def find_contradictions(
    request: ContradictionRequest,
    finder: ContradictionFinder = Depends(get_contradiction_finder),
) -> list[ContradictionMatch]:
    return await finder.find(claims=request.claims, threshold=request.threshold)
