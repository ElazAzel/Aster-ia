from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any, AsyncIterator, Mapping

from asterion_api.config import Settings
from asterion_api.harness import BaseHarness
from asterion_api.schemas import ChatRequest, ChatResponse
from asterion_api.services.ollama_service import OllamaService
from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore
from asterion_api.structured_logging import StructuredLogger


class ChatService(BaseHarness):
    privacy_level = "local"

    def __init__(
        self,
        *,
        settings: Settings,
        ollama: OllamaService,
        store: EncryptedSQLiteStore,
    ) -> None:
        self.settings = settings
        self.ollama = ollama
        self.store = store
        self._state: dict[str, Any] = {"default_model": settings.default_model}
        self.logger = StructuredLogger("chat", self.privacy_level)

    async def execute(self, payload: Mapping[str, Any] | None = None) -> Any:
        payload = payload or {}
        request = ChatRequest(
            message=str(payload.get("message") or payload.get("prompt") or "ping"),
            room_id=str(payload.get("room_id") or "harness"),
            conversation_id=payload.get("conversation_id"),
            model=payload.get("model"),
        )
        return await self.generate(request)

    def get_state(self) -> dict[str, Any]:
        return dict(self._state)

    def set_state(self, state: Mapping[str, Any]) -> None:
        self._state.update(dict(state))

    async def _build_history(self, conv_id: str) -> list[dict[str, str]]:
        messages = await self.store.list_messages(conv_id)
        history = messages[-self.settings.chat_history_limit:]
        return [{"role": m["role"], "content": m["content"]} for m in history]

    async def generate(self, request: ChatRequest) -> ChatResponse:
        model = request.model or self.settings.default_model
        started = time.perf_counter()
        conv_id = await self.store.create_conversation(request.room_id, request.conversation_id)
        await self.store.append_message(
            conv_id=conv_id,
            role="user",
            content=request.message,
            model=model,
        )
        history = await self._build_history(conv_id)
        text = await self.ollama.chat(model=model, messages=history)
        await self.store.append_message(
            conv_id=conv_id,
            role="assistant",
            content=text,
            model=model,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        self.logger.emit("response.completed", model=model, latency_ms=round(latency_ms, 2))
        return ChatResponse(
            conversation_id=conv_id,
            room_id=request.room_id,
            model=model,
            response=text,
            latency_ms=latency_ms,
            ts=datetime.now(UTC),
        )

    async def stream(self, request: ChatRequest) -> AsyncIterator[dict[str, Any]]:
        model = request.model or self.settings.default_model
        conv_id = await self.store.create_conversation(request.room_id, request.conversation_id)
        await self.store.append_message(
            conv_id=conv_id,
            role="user",
            content=request.message,
            model=model,
        )
        history = await self._build_history(conv_id)
        parts: list[str] = []
        started = time.perf_counter()
        async for chunk in self.ollama.stream_chat(model=model, messages=history):
            token = str(chunk.get("message", {}).get("content", ""))
            if token:
                parts.append(token)
            yield {
                "type": "token",
                "conversation_id": conv_id,
                "model": model,
                "response": token,
                "done": bool(chunk.get("done", False)),
                "privacy_level": self.privacy_level,
            }
        full_text = "".join(parts)
        await self.store.append_message(
            conv_id=conv_id,
            role="assistant",
            content=full_text,
            model=model,
        )
        yield {
            "type": "done",
            "conversation_id": conv_id,
            "model": model,
            "latency_ms": (time.perf_counter() - started) * 1000,
            "privacy_level": self.privacy_level,
        }
