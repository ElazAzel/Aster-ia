from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from asterion_api.dependencies import get_comfyui_service
from asterion_api.schemas import (
    ComfyGenerateRequest,
    ComfyRecipeValidateRequest,
    ComfyRecipeValidationResponse,
)
from asterion_api.services.comfyui_service import ComfyUIService

router = APIRouter(prefix="/api/images", tags=["images"])


@router.post("/generate")
async def generate_image(
    request: ComfyGenerateRequest,
    service: ComfyUIService = Depends(get_comfyui_service),
) -> dict[str, object]:
    try:
        return await service.generate(request.prompt, request.recipe)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/validate", response_model=ComfyRecipeValidationResponse)
async def validate_recipe(
    request: ComfyRecipeValidateRequest,
    service: ComfyUIService = Depends(get_comfyui_service),
) -> dict[str, object]:
    return service.validate_recipe(request.recipe, request.prompt)
