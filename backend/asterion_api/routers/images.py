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
        return await service.generate(request.prompt, request.recipe)
    except TimeoutError:
        raise HTTPException(status_code=504, detail="ComfyUI generation timed out")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ComfyUI error: {exc}")
