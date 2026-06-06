from __future__ import annotations

from fastapi import APIRouter, Depends

from asterion_api.dependencies import get_contradiction_finder, get_store, get_supervisor_agent
from asterion_api.schemas import (
    ArtifactBlock,
    ContradictionMatch,
    ContradictionRequest,
    DeepResearchRequest,
    DeepResearchResponse,
    ResearchReportExportRequest,
    ResearchReportExportResponse,
)
from asterion_api.services.contradiction_finder import ContradictionFinder
from asterion_api.services.deep_research import SupervisorAgent
from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore

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


@router.post("/report/export", response_model=ResearchReportExportResponse)
async def export_research_report(
    request: ResearchReportExportRequest,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> ResearchReportExportResponse:
    blocks = [
        ArtifactBlock(
            type="text",
            title="Research goal",
            content=request.query,
            metadata={"receipts_count": len(request.receipts)},
        ),
        *[
            ArtifactBlock(
                type="source",
                title=receipt.source_title,
                content=receipt.claim,
                source=receipt.url,
                metadata={
                    "quote": receipt.quote,
                    "confidence": receipt.confidence,
                    "ts": receipt.ts.isoformat(),
                },
            )
            for receipt in request.receipts
        ],
    ]
    artifact = await store.create_artifact(
        room_id=request.room_id,
        kind="research_report",
        title=request.title,
        blocks=[block.model_dump(mode="json") for block in blocks],
        source="research-studio",
    )
    await store.add_research_receipts(
        report_id=str(artifact["id"]),
        receipts=[receipt.model_dump(mode="json") for receipt in request.receipts],
    )
    return ResearchReportExportResponse(
        artifact=artifact,
        receipts_count=len(request.receipts),
    )
