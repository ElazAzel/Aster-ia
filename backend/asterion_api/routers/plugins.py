from __future__ import annotations

from fastapi import APIRouter, Depends

from asterion_api.dependencies import get_plugin_manager
from asterion_api.schemas import PluginManifest
from asterion_api.services.plugin_manager import PluginManager

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


@router.get("", response_model=list[PluginManifest])
async def list_plugins(
    manager: PluginManager = Depends(get_plugin_manager),
) -> list[PluginManifest]:
    return manager.load()
