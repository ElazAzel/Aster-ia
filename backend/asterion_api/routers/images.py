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
        recipe = service.build_recipe(
            preset_id=request.preset_id,
            overrides=request.recipe,
        )
        return await service.generate(request.prompt, recipe)
    except TimeoutError:
        raise HTTPException(status_code=504, detail="ComfyUI generation timed out")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ComfyUI error: {exc}")


@router.get("/recipes", response_model=ComfyRecipeListResponse)
async def list_recipes(
    service: ComfyUIService = Depends(get_comfyui_service),
) -> ComfyRecipeListResponse:
    presets = service.list_recipe_presets()
    return ComfyRecipeListResponse(recipes=presets)


@router.post("/validate", response_model=ComfyRecipeValidationResponse)
async def validate_recipe(
    request: ComfyRecipeValidateRequest,
    service: ComfyUIService = Depends(get_comfyui_service),
) -> ComfyRecipeValidationResponse:
    recipe = service.build_recipe(
        preset_id=request.preset_id,
        overrides=request.recipe,
    )
    result = service.validate_recipe(recipe, prompt=request.prompt)
    return ComfyRecipeValidationResponse(**result)
