from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from asterion_api.dependencies import get_store
from asterion_api.schemas import ContextRoom, ContextRoomCreateRequest, ContextRoomUpdateRequest
from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


@router.get("", response_model=list[ContextRoom])
async def list_rooms(
    store: EncryptedSQLiteStore = Depends(get_store),
) -> list[ContextRoom]:
    return [ContextRoom(**row) for row in await store.list_rooms()]


@router.post("", response_model=ContextRoom)
async def create_room(
    request: ContextRoomCreateRequest,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> ContextRoom:
    row = await store.create_room(
        room_id=request.id,
        name=request.name,
        color=request.color,
        allowed_models=request.allowed_models,
        memory_policy=request.memory_policy,
        retention_days=request.retention_days,
    )
    return ContextRoom(**row)


@router.get("/{room_id}", response_model=ContextRoom)
async def get_room(
    room_id: str,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> ContextRoom:
    row = await store.get_room(room_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Room not found")
    return ContextRoom(**row)


@router.patch("/{room_id}", response_model=ContextRoom)
async def update_room(
    room_id: str,
    request: ContextRoomUpdateRequest,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> ContextRoom:
    row = await store.update_room(
        room_id,
        name=request.name,
        color=request.color,
        allowed_models=request.allowed_models,
        memory_policy=request.memory_policy,
        retention_days=request.retention_days,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Room not found")
    return ContextRoom(**row)


@router.delete("/{room_id}")
async def delete_room(
    room_id: str,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> dict[str, bool]:
    return {"deleted": await store.delete_room(room_id)}
