from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException

from asterion_api.dependencies import get_model_router, get_ollama_service
from asterion_api.schemas import ModelInfo, ModelSelectRequest, ModelSelection, ModelsResponse
from asterion_api.services.model_router import ModelRouter
from asterion_api.services.ollama_service import OllamaService

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("", response_model=ModelsResponse)
async def list_models(
    ollama: OllamaService = Depends(get_ollama_service),
) -> ModelsResponse:
    try:
        models = await ollama.list_models()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"Ollama unavailable: {exc}") from exc
    return ModelsResponse(models=[ModelInfo(**model) for model in models])


@router.post("/select", response_model=ModelSelection)
async def select_model(
    request: ModelSelectRequest,
    model_router: ModelRouter = Depends(get_model_router),
) -> ModelSelection:
    return model_router.select(request.task_description, request.hw_profile)
