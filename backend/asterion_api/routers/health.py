from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from asterion_api.config import Settings, get_settings
from asterion_api.dependencies import get_store
from asterion_api.schemas import HealthResponse
from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore

router = APIRouter(prefix="/api", tags=["health"])
STARTED_AT = time.perf_counter()


@router.get("/health", response_model=HealthResponse)
async def health(
    settings: Settings = Depends(get_settings),
    store: EncryptedSQLiteStore = Depends(get_store),
) -> HealthResponse:
    database = await store.health_check()
    status = "ok" if database.get("ok") else "degraded"
    return HealthResponse(
        status=status,
        app=settings.app_name,
        uptime_seconds=time.perf_counter() - STARTED_AT,
        database=database,
        privacy={
            "local_first": settings.local_first,
            "external_requests_require_consent": True,
        },
    )
