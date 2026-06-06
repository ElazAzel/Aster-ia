from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile

from asterion_api.dependencies import get_document_indexer, get_store
from asterion_api.schemas import RagChunk, RagDocumentRecord, RagIndexRequest, RagSearchRequest
from asterion_api.services.rag import DocumentIndexer
from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/index")
async def index_document(
    request: RagIndexRequest,
    indexer: DocumentIndexer = Depends(get_document_indexer),
    store: EncryptedSQLiteStore = Depends(get_store),
) -> dict[str, object]:
    result = await indexer.index_file(file_path=Path(request.file_path), room_id=request.room_id)
    document = await store.record_rag_document(
        room_id=request.room_id,
        source=str(result["source"]),
        indexed_chunks=int(result["indexed_chunks"]),
    )
    return {**result, "document": document}


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
