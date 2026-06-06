from __future__ import annotations

import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from asterion_api.dependencies import get_contradiction_finder, get_store, get_supervisor_agent
from asterion_api.schemas import (
    ArtifactBlock,
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


@router.get("/report/{artifact_id}/markdown")
async def export_report_markdown(
    artifact_id: str,
    store: EncryptedSQLiteStore = Depends(get_store),
):
    from fastapi import HTTPException
    from fastapi.responses import Response
    
    artifact = await store.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    lines = []
    lines.append(f"# {artifact['title']}")
    lines.append(f"**Created At:** {artifact['created_at']}")
    lines.append(f"**Room ID:** {artifact['room_id']}")
    lines.append(f"**Source:** {artifact['source']}")
    lines.append("")

    for block_data in artifact["blocks"]:
        block = ArtifactBlock(**block_data)
        if block.type == "text":
            if block.title:
                lines.append(f"## {block.title}")
            if block.content:
                lines.append(block.content)
            lines.append("")
        elif block.type == "code":
            if block.title:
                lines.append(f"### {block.title}")
            lang = block.language or ""
            lines.append(f"```{lang}")
            lines.append(block.content or "")
            lines.append("```")
            lines.append("")
        elif block.type == "table":
            if block.title:
                lines.append(f"### {block.title}")
            if block.rows:
                headers = list(block.rows[0].keys())
                header_row = "| " + " | ".join(headers) + " |"
                sep_row = "| " + " | ".join(["---"] * len(headers)) + " |"
                lines.append(header_row)
                lines.append(sep_row)
                for r in block.rows:
                    row_val = "| " + " | ".join(str(r.get(h, "")) for h in headers) + " |"
                    lines.append(row_val)
            lines.append("")
        elif block.type == "source":
            if block.title:
                lines.append(f"### Source: {block.title}")
            if block.source:
                lines.append(f"**URL:** [{block.source}]({block.source})")
            if block.content:
                lines.append(f"**Claim:** {block.content}")
            meta = block.metadata or {}
            if "quote" in meta and meta["quote"]:
                lines.append(f"> {meta['quote']}")
            if "confidence" in meta and meta["confidence"]:
                lines.append(f"**Confidence:** {meta['confidence']}")
            lines.append("")
        elif block.type == "action":
            action_title = block.title or block.action or "Action"
            lines.append(f"- [ ] **{action_title}**: {block.content or ''}")
            lines.append("")

    content = "\n".join(lines)
    return Response(
        content=content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f"attachment; filename=research_report_{artifact_id}.md"
        }
    )
