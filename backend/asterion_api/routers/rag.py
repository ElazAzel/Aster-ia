from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from asterion_api.dependencies import get_document_indexer, get_store
from asterion_api.schemas import (
    RagChunk,
    RagDocumentRecord,
    RagFolderScopeCreateRequest,
    RagFolderScopeRecord,
    RagIndexRequest,
    RagSearchRequest,
)
from asterion_api.services.rag import DocumentIndexer
from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore

router = APIRouter(prefix="/api/rag", tags=["rag"])
SUPPORTED_RAG_SUFFIXES = {".pdf", ".docx", ".txt", ".md"}


def _resolve_indexable_file(file_path: str) -> Path:
    try:
        resolved = Path(file_path).expanduser().resolve(strict=True)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc
    if not resolved.is_file():
        raise HTTPException(status_code=400, detail="Path must point to a file")
    if resolved.suffix.lower() not in SUPPORTED_RAG_SUFFIXES:
        raise HTTPException(status_code=415, detail="Unsupported file type for RAG indexing")
    return resolved


def _resolve_scope_folder(folder_path: str) -> Path:
    try:
        resolved = Path(folder_path).expanduser().resolve(strict=True)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Folder not found") from exc
    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail="RAG folder scope must be a directory")
    if _is_broad_scope(resolved):
        raise HTTPException(status_code=400, detail="RAG folder scope is too broad")
    return resolved


def _is_broad_scope(path: Path) -> bool:
    home = Path.home().resolve(strict=False)
    return path == path.parent or path == home


@router.post("/index")
async def index_document(
    request: RagIndexRequest,
    indexer: DocumentIndexer = Depends(get_document_indexer),
    store: EncryptedSQLiteStore = Depends(get_store),
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
