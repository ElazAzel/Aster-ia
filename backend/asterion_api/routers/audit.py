from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from asterion_api.dependencies import get_store
from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore

router = APIRouter(prefix="/api/audit", tags=["audit"])


class AuditLogCreate(BaseModel):
    action: str
    resource: str
    details: str | None = None


@router.post("/logs")
async def record_log(
    payload: AuditLogCreate,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> dict[str, Any]:
    return await store.record_audit_log(
        action=payload.action,
        resource=payload.resource,
        details=payload.details,
    )


@router.get("/logs")
async def list_logs(
    store: EncryptedSQLiteStore = Depends(get_store),
) -> list[dict[str, Any]]:
    return await store.list_audit_logs()
