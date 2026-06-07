from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

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
    file_path = _resolve_indexable_file(request.file_path)
    if not await store.is_rag_file_allowed(room_id=request.room_id, file_path=str(file_path)):
        raise HTTPException(
            status_code=403,
            detail="File path is outside approved RAG folder scopes",
        )
    result = await indexer.index_file(file_path=file_path, room_id=request.room_id)
    document = await store.record_rag_document(
        room_id=request.room_id,
        source=str(result["source"]),
        indexed_chunks=int(result["indexed_chunks"]),
    )
    return {**result, "document": document}


@router.get("/folder-scopes", response_model=list[RagFolderScopeRecord])
async def list_folder_scopes(
    room_id: str | None = None,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> list[RagFolderScopeRecord]:
    return [RagFolderScopeRecord(**row) for row in await store.list_rag_folder_scopes(room_id)]


@router.post("/folder-scopes", response_model=RagFolderScopeRecord)
async def create_folder_scope(
    request: RagFolderScopeCreateRequest,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> RagFolderScopeRecord:
    folder_path = _resolve_scope_folder(request.path)
    scope = await store.create_rag_folder_scope(
        room_id=request.room_id,
        path=str(folder_path),
        label=request.label,
        recursive=request.recursive,
    )
    await store.record_audit_log(
        action="grant",
        resource=f"rag_folder_scope:{scope['id']}",
        details=f"{request.room_id}:{folder_path}",
    )
    return RagFolderScopeRecord(**scope)


@router.delete("/folder-scopes/{scope_id}")
async def delete_folder_scope(
    scope_id: str,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> dict[str, bool]:
    deleted = await store.delete_rag_folder_scope(scope_id)
    if deleted:
        await store.record_audit_log(
            action="revoke",
            resource=f"rag_folder_scope:{scope_id}",
            details=None,
        )
    return {"deleted": deleted}


@router.get("/documents", response_model=list[RagDocumentRecord])
async def list_documents(
    room_id: str | None = None,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> list[RagDocumentRecord]:
    return [RagDocumentRecord(**row) for row in await store.list_rag_documents(room_id)]


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> dict[str, bool]:
    return {"deleted": await store.delete_rag_document(document_id)}


@router.post("/search", response_model=list[RagChunk])
async def search_documents(
    request: RagSearchRequest,
    indexer: DocumentIndexer = Depends(get_document_indexer),
) -> list[RagChunk]:
    return await indexer.hybrid_search(
        query=request.query,
        room_id=request.room_id,
        limit=request.limit,
        source_filter=request.source_filter,
    )


@router.post("/index/upload")
async def index_uploaded_file(
    file: UploadFile = File(...),
    room_id: str = Form(default="default"),
    indexer: DocumentIndexer = Depends(get_document_indexer),
    store: EncryptedSQLiteStore = Depends(get_store),
) -> dict[str, object]:
    suffix = Path(file.filename or "upload").suffix or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)
    try:
        result = await indexer.index_file(file_path=tmp_path, room_id=room_id)
        document = await store.record_rag_document(
            room_id=room_id,
            source=file.filename or tmp_path.name,
            indexed_chunks=int(result["indexed_chunks"]),
        )
        return {**result, "source": file.filename or tmp_path.name, "document": document}
    finally:
        tmp_path.unlink(missing_ok=True)
