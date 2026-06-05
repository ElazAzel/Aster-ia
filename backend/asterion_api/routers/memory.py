from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from asterion_api.dependencies import get_memory_ledger, get_store
from asterion_api.schemas import MemoryCreateRequest, MemoryRecord, MemoryUpdateRequest
from asterion_api.services.memory_ledger import MemoryLedger
from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.post("", response_model=MemoryRecord)
async def create_memory(
    request: MemoryCreateRequest,
    ledger: MemoryLedger = Depends(get_memory_ledger),
) -> MemoryRecord:
    return await ledger.create(request)


@router.get("/{room_id}", response_model=list[MemoryRecord])
async def list_memories(
    room_id: str,
    ledger: MemoryLedger = Depends(get_memory_ledger),
) -> list[MemoryRecord]:
    return await ledger.list_by_room(room_id)


@router.patch("/{memory_id}", response_model=MemoryRecord)
async def update_memory(
    memory_id: str,
    request: MemoryUpdateRequest,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> MemoryRecord:
    row = await store.update_memory(
        memory_id,
        content=request.content,
        source=request.source,
        expires_at=request.expires_at.isoformat() if request.expires_at else None,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    return MemoryRecord(**row)


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> dict[str, bool]:
    return {"deleted": await store.delete_memory(memory_id)}
