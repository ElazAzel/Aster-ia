from __future__ import annotations

import re
import time
from datetime import UTC, datetime
from typing import Any, AsyncIterator, Mapping

from asterion_api.config import Settings
from asterion_api.harness import BaseHarness
from asterion_api.schemas import ArtifactBlock, ChatRequest, ChatResponse
from asterion_api.services.ollama_service import OllamaService
from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore
from asterion_api.structured_logging import StructuredLogger


class ChatService(BaseHarness):
    privacy_level = "local"
    _CODE_FENCE_RE = re.compile(r"```(?P<language>[A-Za-z0-9_.+-]*)\s*\n(?P<code>.*?)```", re.DOTALL)

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
        prompt = await self._build_prompt(conv_id, request.message)
        text = await self.ollama.generate(model=model, prompt=prompt)
        artifact = await self._persist_response_artifact(
            room_id=request.room_id,
            prompt=request.message,
            response=text,
            model=model,
        )
        await self.store.append_message(
            conv_id=conv_id,
            role="assistant",
            content=text,
            model=model,
            artifact_id=str(artifact["id"]),
        )
        latency_ms = (time.perf_counter() - started) * 1000
        self.logger.emit(
            "response.completed",
            model=model,
            latency_ms=round(latency_ms, 2),
            artifact_id=artifact["id"],
        )
        return ChatResponse(
            conversation_id=conv_id,
            room_id=request.room_id,
            model=model,
            response=text,
            latency_ms=latency_ms,
            artifact_id=str(artifact["id"]),
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
        prompt = await self._build_prompt(conv_id, request.message)
        parts: list[str] = []
        started = time.perf_counter()
        async for chunk in self.ollama.stream_generate(model=model, prompt=prompt):
            token = str(chunk.get("response", ""))
            if token:
                parts.append(token)
                yield {
                    "type": "token",
                    "conversation_id": conv_id,
                    "model": model,
                    "response": token,
                    "done": False,
                    "privacy_level": self.privacy_level,
                }
        full_text = "".join(parts)
        artifact = await self._persist_response_artifact(
            room_id=request.room_id,
            prompt=request.message,
            response=full_text,
            model=model,
        )
        await self.store.append_message(
            conv_id=conv_id,
            role="assistant",
            content=full_text,
            model=model,
            artifact_id=str(artifact["id"]),
        )
        yield {
            "type": "done",
            "conversation_id": conv_id,
            "model": model,
            "artifact_id": artifact["id"],
            "latency_ms": (time.perf_counter() - started) * 1000,
            "privacy_level": self.privacy_level,
        }

    async def _build_prompt(self, conv_id: str, current_message: str, max_chars: int = 8000) -> str:
        history = await self.store.list_messages(conv_id)
        parts = [f"User: {current_message}"]
        used = len(parts[0])
        for msg in reversed(history):
            role = msg.get("role", "user")
            content = str(msg.get("content", ""))
            line = f"\n{'User' if role == 'user' else 'Assistant'}: {content}"
            if used + len(line) > max_chars:
                break
            parts.append(line)
            used += len(line)
        parts.reverse()
        return "".join(parts)

    async def _persist_response_artifact(
        self,
        *,
        room_id: str,
        prompt: str,
        response: str,
        model: str,
    ) -> dict[str, Any]:
        blocks = [block.model_dump(mode="json") for block in self._response_blocks(response, model)]
        return await self.store.create_artifact(
            room_id=room_id,
            kind="chat",
            title=self._artifact_title(prompt),
            blocks=blocks,
            source="chat",
        )

    def _response_blocks(self, response: str, model: str) -> list[ArtifactBlock]:
        if not response.strip():
            return [
                ArtifactBlock(
                    type="text",
                    title="Empty response",
                    content="",
                    metadata={"model": model},
                )
            ]

        blocks: list[ArtifactBlock] = []
        cursor = 0
        for match in self._CODE_FENCE_RE.finditer(response):
            preface = response[cursor : match.start()].strip()
            if preface:
                blocks.append(
                    ArtifactBlock(
                        type="text",
                        title="Assistant response",
                        content=preface,
                        metadata={"model": model},
                    )
                )
            language = match.group("language").strip() or None
            blocks.append(
                ArtifactBlock(
                    type="code",
                    title="Code block",
                    content=match.group("code").strip(),
                    language=language,
                    metadata={"model": model},
                )
            )
            cursor = match.end()

        tail = response[cursor:].strip()
        if tail:
            blocks.append(
                ArtifactBlock(
                    type="text",
                    title="Assistant response",
                    content=tail,
                    metadata={"model": model},
                )
            )
        if not blocks:
            blocks.append(
                ArtifactBlock(
                    type="text",
                    title="Assistant response",
                    content=response,
                    metadata={"model": model},
                )
            )
        return blocks

    @staticmethod
    def _artifact_title(prompt: str) -> str:
        normalized = " ".join(prompt.split())
        if not normalized:
            return "Chat response"
        return normalized[:80] + ("..." if len(normalized) > 80 else "")
