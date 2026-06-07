from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from asterion_api.dependencies import get_comfyui_service
from asterion_api.schemas import (
    ComfyGenerateRequest,
    ComfyRecipeListResponse,
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
        recipe = service.build_recipe(request.preset_id, request.recipe)
        return await service.generate(request.prompt, recipe)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/recipes", response_model=ComfyRecipeListResponse)
async def list_recipes(
    service: ComfyUIService = Depends(get_comfyui_service),
) -> dict[str, object]:
    return {"recipes": service.list_recipe_presets(), "privacy_level": service.privacy_level}


@router.post("/validate", response_model=ComfyRecipeValidationResponse)
async def validate_recipe(
    request: ComfyRecipeValidateRequest,
    service: ComfyUIService = Depends(get_comfyui_service),
) -> dict[str, object]:
    try:
        recipe = service.build_recipe(request.preset_id, request.recipe)
        return service.validate_recipe(recipe, request.prompt)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
