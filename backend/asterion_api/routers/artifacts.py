from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from asterion_api.dependencies import get_store
from asterion_api.schemas import ArtifactCreateRequest, ArtifactRecord
from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


@router.post("", response_model=ArtifactRecord)
async def create_artifact(
    request: ArtifactCreateRequest,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> ArtifactRecord:
    row = await store.create_artifact(
        room_id=request.room_id,
        kind=request.kind,
        title=request.title,
        blocks=[block.model_dump() for block in request.blocks],
        source=request.source,
    )
    return ArtifactRecord(**row)


@router.get("", response_model=list[ArtifactRecord])
async def list_artifacts(
    room_id: str | None = None,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> list[ArtifactRecord]:
    rows = await store.list_artifacts(room_id)
    return [ArtifactRecord(**{**row, "blocks": row["blocks"]}) for row in rows]


@router.get("/{artifact_id}", response_model=ArtifactRecord)
async def get_artifact(
    artifact_id: str,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> ArtifactRecord:
    row = await store.get_artifact(artifact_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return ArtifactRecord(**row)
