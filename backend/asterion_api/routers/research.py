from __future__ import annotations

import json
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse

from asterion_api.dependencies import get_contradiction_finder, get_store, get_supervisor_agent
from asterion_api.schemas import (
    ArtifactRecord,
    ContradictionMatch,
    ContradictionRequest,
    DeepResearchRequest,
    DeepResearchResponse,
    ResearchReportExportRequest,
    ResearchReportExportResponse,
    ResearchResult,
)
from asterion_api.services.contradiction_finder import ContradictionFinder
from asterion_api.services.deep_research import SubAgent, SupervisorAgent
from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore

router = APIRouter(prefix="/api/research", tags=["research"])


@router.post("/deep/stream")
async def stream_deep_research(
    request: DeepResearchRequest,
    supervisor: SupervisorAgent = Depends(get_supervisor_agent),
) -> StreamingResponse:
    return StreamingResponse(
        _deep_research_sse(supervisor, request.query, request.max_subtasks, request.web_access),
        media_type="text/event-stream",
    )


async def _deep_research_sse(
    supervisor: SupervisorAgent,
    query: str,
    max_subtasks: int,
    web_access: bool,
) -> AsyncGenerator[str, None]:
    privacy = supervisor.analyzer.analyze(
        model_type="local",
        files_attached=False,
        memory_enabled=False,
        web_access=web_access,
    )
    subtasks = supervisor.decompose(query, max_subtasks)
    results: list[ResearchResult] = []

    if web_access:
        for subtask in subtasks:
            yield f"event: subtask_start\ndata: {json.dumps({'subtask': subtask})}\n\n"
            agent = SubAgent(supervisor.searxng_url, subtask)
            try:
                for item in await agent.search():
                    results.append(item)
                    yield f"event: result_found\ndata: {item.model_dump_json()}\n\n"
            except Exception as e:
                yield f"event: error\ndata: {json.dumps({'subtask': subtask, 'error': str(e)})}\n\n"

    supervisor._aggregate_duckdb(results)
    response = DeepResearchResponse(query=query, subtasks=subtasks, results=results, privacy=privacy)
    yield f"event: done\ndata: {response.model_dump_json()}\n\n"


@router.post("/deep", response_model=DeepResearchResponse)
async def deep_research(
    request: DeepResearchRequest,
    supervisor: SupervisorAgent = Depends(get_supervisor_agent),
) -> DeepResearchResponse:
    try:
        return await supervisor.research(
            query=request.query,
            max_subtasks=request.max_subtasks,
            web_access=request.web_access,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Research failed: {exc}")


@router.post("/contradictions", response_model=list[ContradictionMatch])
async def find_contradictions(
    request: ContradictionRequest,
    finder: ContradictionFinder = Depends(get_contradiction_finder),
) -> list[ContradictionMatch]:
    try:
        return await finder.find(claims=request.claims, threshold=request.threshold)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Contradiction analysis failed: {exc}")


@router.post("/report/export", response_model=ResearchReportExportResponse)
async def export_research_report(
    request: ResearchReportExportRequest,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> ResearchReportExportResponse:
    blocks: list[dict[str, Any]] = [
        {"type": "text", "title": "Query", "content": request.query},
    ]
    for receipt in request.receipts:
        blocks.append({
            "type": "source",
            "title": receipt.source_title,
            "content": receipt.quote or receipt.claim,
            "source": receipt.url,
        })
    artifact = await store.create_artifact(
        room_id=request.room_id,
        kind="research_report",
        title=request.title,
        blocks=blocks,
        source="deep_research",
    )
    for receipt in request.receipts:
        await store.save_research_receipt(
            report_id=artifact["id"],
            source_title=receipt.source_title,
            url=receipt.url,
            quote=receipt.quote,
            claim=receipt.claim,
            confidence=receipt.confidence,
        )
    return ResearchReportExportResponse(
        artifact=ArtifactRecord(**artifact),
        receipts_count=len(request.receipts),
    )


@router.get("/report/{artifact_id}/markdown")
async def get_report_markdown(
    artifact_id: str,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> PlainTextResponse:
    artifact = await store.get_artifact(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    md = f"# {artifact['title']}\n\n"
    for block in artifact.get("blocks", []):
        if block.get("title"):
            md += f"## {block['title']}\n\n"
        if block.get("content"):
            md += f"{block['content']}\n\n"
        if block.get("source"):
            md += f"**Source:** {block['source']}\n\n"
    return PlainTextResponse(content=md, media_type="text/markdown")
