from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from asterion_api.dependencies import get_plugin_manager
from asterion_api.schemas import PluginManifest
from asterion_api.services.plugin_manager import PluginManager

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


@router.get("", response_model=list[PluginManifest])
async def list_plugins(
    manager: PluginManager = Depends(get_plugin_manager),
) -> list[PluginManifest]:
    try:
        return manager.load()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load plugins: {exc}")
