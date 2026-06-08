from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from asterion_api.dependencies import get_memory_ledger
from asterion_api.schemas import MemoryCreateRequest, MemoryRecord, MemoryUpdateRequest
from asterion_api.services.memory_ledger import MemoryLedger

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
    ledger: MemoryLedger = Depends(get_memory_ledger),
) -> MemoryRecord:
    result = await ledger.update(memory_id, request)
    if result is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    return result


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    ledger: MemoryLedger = Depends(get_memory_ledger),
) -> dict[str, bool]:
    deleted = await ledger.delete(memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"deleted": True}
