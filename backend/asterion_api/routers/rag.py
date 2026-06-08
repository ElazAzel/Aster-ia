from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

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
    file_path = Path(request.file_path).expanduser().resolve()
    scopes = await store.list_rag_folder_scopes(request.room_id)
    allowed = False
    for scope in scopes:
        scope_path = Path(scope["path"]).expanduser().resolve()
        try:
            file_path.relative_to(scope_path)
            allowed = True
            break
        except ValueError:
            continue
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="File path is not inside an approved folder scope. Create a folder scope first.",
        )
    try:
        result = await indexer.index_file(file_path=file_path, room_id=request.room_id)
        return {"document": result}
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


@router.get("/documents", response_model=list[RagDocumentRecord])
async def list_documents(
    room_id: str | None = None,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> list[RagDocumentRecord]:
    rows = await store.list_rag_documents(room_id)
    return [RagDocumentRecord(**row) for row in rows]


@router.get("/folder-scopes", response_model=list[RagFolderScopeRecord])
async def list_folder_scopes(
    room_id: str | None = None,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> list[RagFolderScopeRecord]:
    rows = await store.list_rag_folder_scopes(room_id)
    return [RagFolderScopeRecord(**row) for row in rows]


@router.post("/folder-scopes", response_model=RagFolderScopeRecord)
async def create_folder_scope(
    request: RagFolderScopeCreateRequest,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> RagFolderScopeRecord:
    try:
        resolved = _resolve_scope_folder(request.path)
    except HTTPException:
        resolved = Path(request.path)
    row = await store.create_rag_folder_scope(
        room_id=request.room_id, path=str(resolved),
        label=request.label, recursive=request.recursive,
    )
    return RagFolderScopeRecord(**row)


@router.delete("/folder-scopes/{scope_id}")
async def delete_folder_scope(
    scope_id: str,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> dict[str, bool]:
    deleted = await store.delete_rag_folder_scope(scope_id)
    return {"deleted": deleted}


@router.post("/index/upload")
async def upload_and_index(
    file: UploadFile = File(...),
    room_id: str = Form("default"),
    indexer: DocumentIndexer = Depends(get_document_indexer),
) -> dict[str, object]:
    content = await file.read()
    suffix = Path(file.filename or "upload.txt").suffix.lower()
    if suffix not in SUPPORTED_RAG_SUFFIXES:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {suffix}")
    tmp = Path(tempfile.mkdtemp()) / (file.filename or f"upload{suffix}")
    tmp.write_bytes(content)
    try:
        return await indexer.index_file(file_path=tmp, room_id=room_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found after upload")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {exc}")
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)
