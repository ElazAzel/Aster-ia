from __future__ import annotations

import json

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from asterion_api.dependencies import get_chat_service
from asterion_api.schemas import ChatRequest, ChatResponse
from asterion_api.services.chat_service import ChatService

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    try:
        return await service.generate(request)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"Ollama unavailable: {exc}") from exc


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    async def events():
        try:
            async for event in service.stream(request):
                yield f"data: {json.dumps(event, ensure_ascii=True)}\n\n"
        except httpx.HTTPError as exc:
            payload = {"type": "error", "error": f"Ollama unavailable: {exc}"}
            yield f"data: {json.dumps(payload, ensure_ascii=True)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@router.get("/stream")
async def chat_stream_eventsource(
    message: str,
    room_id: str = "default",
    model: str | None = None,
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    request = ChatRequest(message=message, room_id=room_id, model=model)

    async def events():
        try:
            async for event in service.stream(request):
                yield f"data: {json.dumps(event, ensure_ascii=True)}\n\n"
        except httpx.HTTPError as exc:
            payload = {"type": "error", "error": f"Ollama unavailable: {exc}"}
            yield f"data: {json.dumps(payload, ensure_ascii=True)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
