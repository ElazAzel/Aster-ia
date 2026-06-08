from __future__ import annotations

import asyncio
import json

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from asterion_api.dependencies import get_chat_service, get_store
from asterion_api.schemas import (
    ChatConversationRecord,
    ChatConversationUpdateRequest,
    ChatMessageRecord,
    ChatRequest,
    ChatResponse,
)
from asterion_api.services.chat_service import ChatService
from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    try:
        return await service.generate(request)
    except (httpx.RequestError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=503, detail=f"Ollama unavailable: {exc}") from exc


@router.get("/conversations", response_model=list[ChatConversationRecord])
async def list_conversations(
    room_id: str | None = None,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> list[ChatConversationRecord]:
    rows = await store.list_conversations(room_id)
    return [ChatConversationRecord(**row) for row in rows]


@router.patch("/conversations/{conversation_id}", response_model=ChatConversationRecord)
async def update_conversation(
    conversation_id: str,
    request: ChatConversationUpdateRequest,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> ChatConversationRecord:
    row = await store.update_conversation(conversation_id, title=request.title)
    if not row:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ChatConversationRecord(**row)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> dict[str, bool]:
    deleted = await store.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True}


@router.get("/conversations/{conversation_id}/messages", response_model=list[ChatMessageRecord])
async def list_conversation_messages(
    conversation_id: str,
    store: EncryptedSQLiteStore = Depends(get_store),
) -> list[ChatMessageRecord]:
    rows = await store.list_messages(conversation_id)
    return [ChatMessageRecord(**row) for row in rows]


async def _stream_events(service: ChatService, request: ChatRequest):
    async def events():
        try:
            async for event in service.stream(request):
                yield f"data: {json.dumps(event, ensure_ascii=True)}\n\n"
        except (httpx.RequestError, httpx.StreamError, httpx.ResponseNotRead) as exc:
            payload = {"type": "error", "error": f"Ollama unavailable: {exc}"}
            yield f"data: {json.dumps(payload, ensure_ascii=True)}\n\n"
        except asyncio.CancelledError:
            # Client disconnected — propagate so the server cancels the upstream
            raise
        except Exception as exc:  # noqa: BLE001
            payload = {"type": "error", "error": f"stream error: {exc}"}
            yield f"data: {json.dumps(payload, ensure_ascii=True)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    return await _stream_events(service, request)


@router.get("/stream")
async def chat_stream_eventsource(
    message: str,
    room_id: str = "default",
    conversation_id: str | None = None,
    model: str | None = None,
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    request = ChatRequest(
        message=message,
        room_id=room_id,
        conversation_id=conversation_id,
        model=model,
    )
    return await _stream_events(service, request)
