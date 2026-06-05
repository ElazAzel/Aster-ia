from __future__ import annotations

from fastapi import APIRouter, Depends

from asterion_api.dependencies import get_comfyui_service
from asterion_api.schemas import ComfyGenerateRequest
from asterion_api.services.comfyui_service import ComfyUIService

router = APIRouter(prefix="/api/images", tags=["images"])


@router.post("/generate")
async def generate_image(
    request: ComfyGenerateRequest,
    service: ComfyUIService = Depends(get_comfyui_service),
) -> dict[str, object]:
    return await service.generate(request.prompt, request.recipe)
