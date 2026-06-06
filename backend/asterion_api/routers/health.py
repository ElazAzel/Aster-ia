from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from asterion_api.config import Settings, get_settings
from asterion_api.dependencies import get_ollama_service, get_store
from asterion_api.schemas import HealthResponse
from asterion_api.services.ollama_service import OllamaService
from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore

router = APIRouter(prefix="/api", tags=["health"])
STARTED_AT = time.perf_counter()


@router.get("/health", response_model=HealthResponse)
async def health(
    settings: Settings = Depends(get_settings),
    store: EncryptedSQLiteStore = Depends(get_store),
    ollama: OllamaService = Depends(get_ollama_service),
) -> HealthResponse:
    database = await store.health_check()
    schema_ver = await store.schema_version()

    ollama_available = await ollama.is_available()
    ollama_info: dict = {"available": ollama_available}
    if ollama_available:
        try:
            models = await ollama.list_models()
            ollama_info["model_count"] = len(models)
        except Exception:  # noqa: BLE001
            ollama_info["model_count"] = -1

    db_ok = database.get("ok", False)
    status = "ok" if db_ok and ollama_available else "degraded"

    return HealthResponse(
        status=status,
        app=settings.app_name,
        uptime_seconds=time.perf_counter() - STARTED_AT,
        database=database,
        ollama=ollama_info,
        schema_version=schema_ver,
        privacy={
            "local_first": settings.local_first,
            "external_requests_require_consent": True,
        },
    )
