from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from asterion_api.dependencies import get_document_indexer
from asterion_api.schemas import RagChunk, RagIndexRequest, RagSearchRequest
from asterion_api.services.rag import DocumentIndexer

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/index")
async def index_document(
    request: RagIndexRequest,
    indexer: DocumentIndexer = Depends(get_document_indexer),
) -> dict[str, object]:
    try:
        return await indexer.index_file(file_path=Path(request.file_path), room_id=request.room_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {exc}")


@router.post("/search", response_model=list[RagChunk])
async def search_documents(
    request: RagSearchRequest,
    indexer: DocumentIndexer = Depends(get_document_indexer),
) -> list[RagChunk]:
    try:
        return await indexer.hybrid_search(
            query=request.query,
            room_id=request.room_id,
            limit=request.limit,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Search failed: {exc}")
