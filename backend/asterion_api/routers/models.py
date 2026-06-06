from __future__ import annotations

import json

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from asterion_api.config import Settings, get_settings
from asterion_api.dependencies import get_model_router, get_ollama_service
from asterion_api.schemas import (
    ModelEnsureResponse,
    ModelInfo,
    ModelPullRequest,
    ModelSelectRequest,
    ModelSelection,
    ModelsResponse,
)
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


@router.post("/pull")
async def pull_model(
    request: ModelPullRequest,
    ollama: OllamaService = Depends(get_ollama_service),
) -> StreamingResponse:
    """Pull a model from Ollama with SSE progress streaming."""
    if not await ollama.is_available():
        raise HTTPException(status_code=503, detail="Ollama is not available")

    async def event_stream():
        try:
            async for chunk in ollama.pull_model(request.model):
                yield f"data: {json.dumps(chunk, ensure_ascii=True)}\n\n"
        except httpx.HTTPError as exc:
            yield f"data: {json.dumps({'status': 'error', 'error': str(exc)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/ensure", response_model=ModelEnsureResponse)
async def ensure_models(
    ollama: OllamaService = Depends(get_ollama_service),
    settings: Settings = Depends(get_settings),
) -> ModelEnsureResponse:
    """Check and pull all required models defined in settings."""
    results = await ollama.ensure_models(settings.required_models)
    return ModelEnsureResponse(results=results)
