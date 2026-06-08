from __future__ import annotations

from typing import Any, Mapping

from asterion_api.harness import BaseHarness
from asterion_api.schemas import MemoryCreateRequest, MemoryRecord, MemoryUpdateRequest, PrivacyReport
from asterion_api.services.privacy_analyzer import PrivacyAnalyzer
from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore
from asterion_api.structured_logging import StructuredLogger


class MemoryLedger(BaseHarness):
    privacy_level = "local"

    def __init__(self, store: EncryptedSQLiteStore, analyzer: PrivacyAnalyzer) -> None:
        self.store = store
        self.analyzer = analyzer
        self.logger = StructuredLogger("memory", self.privacy_level)

    async def execute(self, payload: Mapping[str, Any] | None = None) -> Any:
        payload = payload or {}
        action = payload.get("action", "list")
        if action == "create":
            return await self.create(MemoryCreateRequest(**payload))
        if action == "list":
            return await self.list_by_room(str(payload.get("room_id", "default")))
        if action == "update":
            return await self.update(
                str(payload["memory_id"]),
                MemoryUpdateRequest(
                    content=payload.get("content"),
                    source=payload.get("source"),
                    expires_at=payload.get("expires_at"),
                ),
            )
        if action == "delete":
            return await self.delete(str(payload["memory_id"]))
        raise ValueError(f"Unsupported memory ledger action: {action}")

    def get_state(self) -> dict[str, Any]:
        return {"privacy_level": self.privacy_level}

    def set_state(self, state: Mapping[str, Any]) -> None:
        return None

    async def create(self, request: MemoryCreateRequest) -> MemoryRecord:
        privacy = self.analyzer.analyze(**request.privacy.model_dump())
        row = await self.store.create_memory(
            room_id=request.room_id,
            content=request.content,
            source=request.source,
            expires_at=request.expires_at.isoformat() if request.expires_at else None,
        )
        self.logger.emit("memory.created", room_id=request.room_id, risk=privacy.level)
        return self._record(row, privacy)

    async def list_by_room(self, room_id: str) -> list[MemoryRecord]:
        rows = await self.store.list_memories(room_id)
        return [self._record(row, None) for row in rows]

    async def update(self, memory_id: str, request: MemoryUpdateRequest) -> MemoryRecord | None:
        existing = await self.store.get_memory(memory_id)
        if existing is None:
            return None
        privacy = self.analyzer.analyze(
            model_type="local",
            files_attached=False,
            memory_enabled=True,
            web_access=False,
        )
        self.logger.emit("memory.updated", memory_id=memory_id, risk=privacy.level)
        row = await self.store.update_memory(
            memory_id,
            content=request.content,
            source=request.source,
            expires_at=request.expires_at.isoformat() if request.expires_at else None,
        )
        if row is None:
            return None
        return self._record(row, privacy)

    async def delete(self, memory_id: str) -> bool:
        self.logger.emit("memory.deleted", memory_id=memory_id)
        return await self.store.delete_memory(memory_id)

    @staticmethod
    def _record(row: dict[str, Any], privacy: PrivacyReport | None) -> MemoryRecord:
        return MemoryRecord(
            id=row["id"],
            room_id=row["room_id"],
            content=row["content"],
            source=row["source"],
            created_at=row["created_at"],
            expires_at=row.get("expires_at"),
            privacy=privacy,
        )
