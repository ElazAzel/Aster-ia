from __future__ import annotations

import asyncio
import json
import secrets
import sqlite3
import threading
from datetime import UTC, datetime
from typing import Any, Mapping
from uuid import uuid4

import keyring
import keyring.errors

from asterion_api.config import Settings
from asterion_api.harness import BaseHarness
from asterion_api.storage.migrations import current_version, run_migrations
from asterion_api.structured_logging import StructuredLogger

try:
    import sqlcipher3

    SQLCIPHER_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only when dev deps are absent
    sqlcipher3 = None
    SQLCIPHER_AVAILABLE = False


class EncryptedSQLiteStore(BaseHarness):
    privacy_level = "local"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.path = settings.database_path
        self._state: dict[str, Any] = {"path": str(self.path)}
        self.logger = StructuredLogger("sqlite", self.privacy_level)
        self._local = threading.local()

    async def execute(self, payload: Mapping[str, Any] | None = None) -> Any:
        action = (payload or {}).get("action", "health")
        if action == "ensure_schema":
            await self.ensure_schema()
            return {"ok": True}
        if action == "health":
            return await self.health_check()
        raise ValueError(f"Unsupported storage harness action: {action}")

    def get_state(self) -> dict[str, Any]:
        return dict(self._state)

    def set_state(self, state: Mapping[str, Any]) -> None:
        self._state.update(dict(state))

    async def ensure_schema(self) -> None:
        await asyncio.to_thread(self._ensure_schema_sync)

    async def schema_version(self) -> int:
        """Return the current schema migration version."""
        return await asyncio.to_thread(self._schema_version_sync)

    async def health_check(self) -> dict[str, Any]:
        return await asyncio.to_thread(self._health_check_sync)

    async def create_conversation(self, room_id: str, conversation_id: str | None = None) -> str:
        return await asyncio.to_thread(self._create_conversation_sync, room_id, conversation_id)

    async def append_message(
        self,
        *,
        conv_id: str,
        role: str,
        content: str,
        model: str | None,
        artifact_id: str | None = None,
    ) -> str:
        return await asyncio.to_thread(
            self._append_message_sync,
            conv_id,
            role,
            content,
            model,
            artifact_id,
        )

    async def update_conversation(self, conv_id: str, *, title: str) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._update_conversation_sync, conv_id, title)

    async def delete_conversation(self, conv_id: str) -> bool:
        return await asyncio.to_thread(self._delete_conversation_sync, conv_id)

    async def list_conversations(self, room_id: str | None = None) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._list_conversations_sync, room_id)

    async def list_messages(self, conv_id: str) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._list_messages_sync, conv_id)

    async def create_memory(
        self,
        *,
        room_id: str,
        content: str,
        source: str,
        expires_at: str | None,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._create_memory_sync,
            room_id,
            content,
            source,
            expires_at,
        )

    async def list_memories(self, room_id: str) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._list_memories_sync, room_id)

    async def update_memory(
        self,
        memory_id: str,
        *,
        content: str | None,
        source: str | None,
        expires_at: str | None,
    ) -> dict[str, Any] | None:
        return await asyncio.to_thread(
            self._update_memory_sync,
            memory_id,
            content,
            source,
            expires_at,
        )

    async def delete_memory(self, memory_id: str) -> bool:
        return await asyncio.to_thread(self._delete_memory_sync, memory_id)

    async def list_rooms(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._list_rooms_sync)

    async def create_room(
        self,
        *,
        room_id: str | None,
        name: str,
        color: str,
        allowed_models: list[str],
        memory_policy: str,
        retention_days: int,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._create_room_sync,
            room_id,
            name,
            color,
            allowed_models,
            memory_policy,
            retention_days,
        )

    async def get_room(self, room_id: str) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._get_room_sync, room_id)

    async def update_room(
        self,
        room_id: str,
        *,
        name: str | None,
        color: str | None,
        allowed_models: list[str] | None,
        memory_policy: str | None,
        retention_days: int | None,
    ) -> dict[str, Any] | None:
        return await asyncio.to_thread(
            self._update_room_sync,
            room_id,
            name,
            color,
            allowed_models,
            memory_policy,
            retention_days,
        )

    async def delete_room(self, room_id: str) -> bool:
        return await asyncio.to_thread(self._delete_room_sync, room_id)

    async def record_rag_document(
        self,
        *,
        room_id: str,
        source: str,
        indexed_chunks: int,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._record_rag_document_sync,
            room_id,
            source,
            indexed_chunks,
        )

    async def list_rag_documents(self, room_id: str | None = None) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._list_rag_documents_sync, room_id)

    async def delete_rag_document(self, document_id: str) -> bool:
        return await asyncio.to_thread(self._delete_rag_document_sync, document_id)

    async def create_artifact(
        self,
        *,
        room_id: str,
        kind: str,
        title: str,
        blocks: list[dict[str, Any]],
        source: str,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._create_artifact_sync,
            room_id,
            kind,
            title,
            blocks,
            source,
        )

    async def list_artifacts(self, room_id: str | None = None) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._list_artifacts_sync, room_id)

    async def get_artifact(self, artifact_id: str) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._get_artifact_sync, artifact_id)

    async def add_research_receipts(
        self,
        *,
        report_id: str,
        receipts: list[dict[str, Any]],
    ) -> None:
        await asyncio.to_thread(self._add_research_receipts_sync, report_id, receipts)

    async def get_all_research_receipts(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._get_all_research_receipts_sync)

    async def get_all_agent_runs(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._get_all_agent_runs_sync)

    async def get_all_agent_logs(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._get_all_agent_logs_sync)

    async def create_agent_run(
        self,
        *,
        agent_id: str,
        room_id: str,
        status: str,
        plan: dict[str, Any],
        permissions: dict[str, Any],
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._create_agent_run_sync,
            agent_id,
            room_id,
            status,
            plan,
            permissions,
        )

    async def get_agent_run(self, run_id: str) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._get_agent_run_sync, run_id)

    async def update_agent_run(
        self,
        run_id: str,
        status: str | None = None,
        agent_id: str | None = None,
    ) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._update_agent_run_sync, run_id, status, agent_id)

    async def append_agent_log(
        self,
        *,
        run_id: str,
        action: str,
        tool: str,
        privacy_level: str,
        input_text: str | None = None,
        output_text: str | None = None,
        model: str | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._append_agent_log_sync,
            run_id,
            action,
            tool,
            privacy_level,
            input_text,
            output_text,
            model,
            error,
        )

    async def list_agent_logs(self, run_id: str) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._list_agent_logs_sync, run_id)

    def _ensure_schema_sync(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            version = run_migrations(conn)
            self.logger.emit("schema.ready", db_path=str(self.path), schema_version=version)

    def _schema_version_sync(self) -> int:
        with self._connect() as conn:
            return current_version(conn)

    def _health_check_sync(self) -> dict[str, Any]:
        try:
            with self._connect() as conn:
                conn.execute("SELECT 1").fetchone()
            return {
                "ok": True,
                "encrypted": SQLCIPHER_AVAILABLE,
                "path": str(self.path),
            }
        except Exception as exc:  # noqa: BLE001 - health endpoint must report all failures
            self.logger.emit("health.failed", error=str(exc))
            return {
                "ok": False,
                "encrypted": SQLCIPHER_AVAILABLE,
                "path": str(self.path),
                "error": str(exc),
            }

    def _create_conversation_sync(self, room_id: str, conversation_id: str | None) -> str:
        conv_id = conversation_id or str(uuid4())
        created_at = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO conversations (id, room_id, created_at)
                VALUES (?, ?, ?)
                """,
                (conv_id, room_id, created_at),
            )
            conn.commit()
        return conv_id

    def _append_message_sync(
        self,
        conv_id: str,
        role: str,
        content: str,
        model: str | None,
        artifact_id: str | None,
    ) -> str:
        message_id = str(uuid4())
        ts = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO messages (id, conv_id, role, content, model, artifact_id, ts)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (message_id, conv_id, role, content, model, artifact_id, ts),
            )
            conn.commit()
        return message_id

    def _list_conversations_sync(self, room_id: str | None) -> list[dict[str, Any]]:
        with self._connect() as conn:
            if room_id:
                rows = conn.execute(
                    """
                    SELECT
                        c.id,
                        c.room_id,
                        c.title,
                        c.created_at,
                        COUNT(m.id) AS message_count,
                        MAX(m.ts) AS latest_ts
                    FROM conversations c
                    LEFT JOIN messages m ON m.conv_id = c.id
                    WHERE c.room_id = ?
                    GROUP BY c.id, c.room_id, c.created_at
                    ORDER BY COALESCE(latest_ts, c.created_at) DESC
                    """,
                    (room_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT
                        c.id,
                        c.room_id,
                        c.title,
                        c.created_at,
                        COUNT(m.id) AS message_count,
                        MAX(m.ts) AS latest_ts
                    FROM conversations c
                    LEFT JOIN messages m ON m.conv_id = c.id
                    GROUP BY c.id, c.room_id, c.created_at
                    ORDER BY COALESCE(latest_ts, c.created_at) DESC
                    """
                ).fetchall()
        return [dict(row) for row in rows]

    def _update_conversation_sync(self, conv_id: str, title: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            conn.execute("UPDATE conversations SET title = ? WHERE id = ?", (title, conv_id))
            conn.commit()
            row = conn.execute(
                """
                SELECT
                    c.id, c.room_id, c.title, c.created_at,
                    COUNT(m.id) AS message_count, MAX(m.ts) AS latest_ts
                FROM conversations c
                LEFT JOIN messages m ON m.conv_id = c.id
                WHERE c.id = ?
                GROUP BY c.id, c.room_id, c.title, c.created_at
                """,
                (conv_id,),
            ).fetchone()
        return dict(row) if row is not None else None

    def _delete_conversation_sync(self, conv_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
            conn.commit()
        return cursor.rowcount > 0

    def _list_messages_sync(self, conv_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, conv_id, role, content, model, artifact_id, ts
                FROM messages
                WHERE conv_id = ?
                ORDER BY ts ASC
                """,
                (conv_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def _create_memory_sync(
        self,
        room_id: str,
        content: str,
        source: str,
        expires_at: str | None,
    ) -> dict[str, Any]:
        memory_id = str(uuid4())
        created_at = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO memories (id, room_id, content, source, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (memory_id, room_id, content, source, created_at, expires_at),
            )
            conn.commit()
        return {
            "id": memory_id,
            "room_id": room_id,
            "content": content,
            "source": source,
            "created_at": created_at,
            "expires_at": expires_at,
        }

    def _list_memories_sync(self, room_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, room_id, content, source, created_at, expires_at
                FROM memories
                WHERE room_id = ?
                  AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY created_at DESC
                """,
                (room_id, datetime.now(UTC).isoformat()),
            ).fetchall()
        return [dict(row) for row in rows]

    def _update_memory_sync(
        self,
        memory_id: str,
        content: str | None,
        source: str | None,
        expires_at: str | None,
    ) -> dict[str, Any] | None:
        current = self._get_memory_sync(memory_id)
        if current is None:
            return None
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE memories
                SET content = ?, source = ?, expires_at = ?
                WHERE id = ?
                """,
                (
                    content if content is not None else current["content"],
                    source if source is not None else current["source"],
                    expires_at if expires_at is not None else current["expires_at"],
                    memory_id,
                ),
            )
            conn.commit()
        return self._get_memory_sync(memory_id)

    def _delete_memory_sync(self, memory_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
        return cursor.rowcount > 0

    def _get_memory_sync(self, memory_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, room_id, content, source, created_at, expires_at
                FROM memories
                WHERE id = ?
                """,
                (memory_id,),
            ).fetchone()
        return dict(row) if row is not None else None

    def _list_rooms_sync(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, name, color, allowed_models, memory_policy, retention_days, system_prompt, created_at, updated_at
                FROM rooms
                ORDER BY created_at ASC
                """
            ).fetchall()
        return [self._decode_room(row) for row in rows]

    def _create_room_sync(
        self,
        room_id: str | None,
        name: str,
        color: str,
        allowed_models: list[str],
        memory_policy: str,
        retention_days: int,
        system_prompt: str = "",
    ) -> dict[str, Any]:
        new_room_id = room_id or str(uuid4())
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO rooms (
                    id, name, color, allowed_models, memory_policy, retention_days, system_prompt, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_room_id,
                    name,
                    color,
                    json.dumps(allowed_models),
                    memory_policy,
                    retention_days,
                    system_prompt,
                    now,
                    now,
                ),
            )
            conn.commit()
        room = self._get_room_sync(new_room_id)
        if room is None:
            raise RuntimeError("created room could not be read")
        return room

    def _get_room_sync(self, room_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, name, color, allowed_models, memory_policy, retention_days, system_prompt, created_at, updated_at
                FROM rooms
                WHERE id = ?
                """,
                (room_id,),
            ).fetchone()
        return self._decode_room(row) if row is not None else None

    def _update_room_sync(
        self,
        room_id: str,
        name: str | None,
        color: str | None,
        allowed_models: list[str] | None,
        memory_policy: str | None,
        retention_days: int | None,
        system_prompt: str | None = None,
    ) -> dict[str, Any] | None:
        current = self._get_room_sync(room_id)
        if current is None:
            return None
        updated_at = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE rooms
                SET name = ?, color = ?, allowed_models = ?, memory_policy = ?, retention_days = ?, system_prompt = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    name if name is not None else current["name"],
                    color if color is not None else current["color"],
                    json.dumps(allowed_models if allowed_models is not None else current["allowed_models"]),
                    memory_policy if memory_policy is not None else current["memory_policy"],
                    retention_days if retention_days is not None else current["retention_days"],
                    system_prompt if system_prompt is not None else current.get("system_prompt", ""),
                    updated_at,
                    room_id,
                ),
            )
            conn.commit()
        return self._get_room_sync(room_id)

    def _delete_room_sync(self, room_id: str) -> bool:
        if room_id == "default":
            return False
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM rooms WHERE id = ?", (room_id,))
            conn.commit()
        return cursor.rowcount > 0

    def _record_rag_document_sync(
        self,
        room_id: str,
        source: str,
        indexed_chunks: int,
    ) -> dict[str, Any]:
        document_id = str(uuid4())
        created_at = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO rag_documents (id, room_id, source, indexed_chunks, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (document_id, room_id, source, indexed_chunks, created_at),
            )
            conn.commit()
        return {
            "id": document_id,
            "room_id": room_id,
            "source": source,
            "indexed_chunks": indexed_chunks,
            "created_at": created_at,
        }

    def _list_rag_documents_sync(self, room_id: str | None) -> list[dict[str, Any]]:
        with self._connect() as conn:
            if room_id:
                rows = conn.execute(
                    """
                    SELECT id, room_id, source, indexed_chunks, created_at
                    FROM rag_documents
                    WHERE room_id = ?
                    ORDER BY created_at DESC
                    """,
                    (room_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, room_id, source, indexed_chunks, created_at
                    FROM rag_documents
                    ORDER BY created_at DESC
                    """
                ).fetchall()
        return [dict(row) for row in rows]

    def _delete_rag_document_sync(self, document_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM rag_documents WHERE id = ?", (document_id,))
            conn.commit()
        return cursor.rowcount > 0

    def _create_artifact_sync(
        self,
        room_id: str,
        kind: str,
        title: str,
        blocks: list[dict[str, Any]],
        source: str,
    ) -> dict[str, Any]:
        artifact_id = str(uuid4())
        created_at = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO artifacts (id, room_id, kind, title, blocks, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (artifact_id, room_id, kind, title, json.dumps(blocks), source, created_at),
            )
            conn.commit()
        artifact = self._get_artifact_sync(artifact_id)
        if artifact is None:
            raise RuntimeError("created artifact could not be read")
        return artifact

    def _list_artifacts_sync(self, room_id: str | None) -> list[dict[str, Any]]:
        with self._connect() as conn:
            if room_id:
                rows = conn.execute(
                    """
                    SELECT id, room_id, kind, title, blocks, source, created_at
                    FROM artifacts WHERE room_id = ? ORDER BY created_at DESC
                    """,
                    (room_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, room_id, kind, title, blocks, source, created_at
                    FROM artifacts ORDER BY created_at DESC
                    """
                ).fetchall()
        result = []
        for row in rows:
            artifact = dict(row)
            artifact["blocks"] = json.loads(str(artifact["blocks"]))
            result.append(artifact)
        return result

    def _get_artifact_sync(self, artifact_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, room_id, kind, title, blocks, source, created_at
                FROM artifacts
                WHERE id = ?
                """,
                (artifact_id,),
            ).fetchone()
        if row is None:
            return None
        artifact = dict(row)
        artifact["blocks"] = json.loads(str(artifact["blocks"]))
        return artifact

    def _add_research_receipts_sync(
        self,
        report_id: str,
        receipts: list[dict[str, Any]],
    ) -> None:
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO research_receipts (
                    id, report_id, source_title, url, quote, claim, confidence, ts
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        str(uuid4()),
                        report_id,
                        receipt["source_title"],
                        receipt.get("url"),
                        receipt.get("quote"),
                        receipt["claim"],
                        receipt["confidence"],
                        receipt["ts"],
                    )
                    for receipt in receipts
                ],
            )
            conn.commit()

    def _get_all_research_receipts_sync(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    rr.id,
                    rr.report_id,
                    rr.source_title,
                    rr.url,
                    rr.quote,
                    rr.claim,
                    rr.confidence,
                    rr.ts,
                    COALESCE(a.room_id, 'default') as room_id,
                    COALESCE(r.name, 'Default Room') as room_name
                FROM research_receipts rr
                LEFT JOIN artifacts a ON rr.report_id = a.id
                LEFT JOIN rooms r ON a.room_id = r.id
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def _get_all_agent_runs_sync(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    ar.id,
                    ar.agent_id,
                    ar.room_id,
                    ar.status,
                    ar.plan,
                    ar.permissions,
                    ar.created_at,
                    ar.updated_at,
                    COALESCE(r.name, 'Default Room') as room_name
                FROM agent_runs ar
                LEFT JOIN rooms r ON ar.room_id = r.id
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def _get_all_agent_logs_sync(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    al.id,
                    al.run_id,
                    al.ts,
                    al.action,
                    al.tool,
                    al.input,
                    al.output,
                    al.model,
                    al.privacy_level,
                    al.error,
                    COALESCE(ar.room_id, 'default') as room_id,
                    COALESCE(r.name, 'Default Room') as room_name
                FROM agent_logs al
                LEFT JOIN agent_runs ar ON al.run_id = ar.id
                LEFT JOIN rooms r ON ar.room_id = r.id
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def _create_agent_run_sync(
        self,
        agent_id: str,
        room_id: str,
        status: str,
        plan: dict[str, Any],
        permissions: dict[str, Any],
    ) -> dict[str, Any]:
        run_id = str(uuid4())
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_runs (
                    id, agent_id, room_id, status, plan, permissions, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    agent_id,
                    room_id,
                    status,
                    json.dumps(plan),
                    json.dumps(permissions),
                    now,
                    now,
                ),
            )
            conn.commit()
        run = self._get_agent_run_sync(run_id)
        if run is None:
            raise RuntimeError("created agent run could not be read")
        return run

    def _get_agent_run_sync(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, agent_id, room_id, status, plan, permissions, created_at, updated_at
                FROM agent_runs
                WHERE id = ?
                """,
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        run = dict(row)
        run["plan"] = json.loads(str(run["plan"]))
        run["permissions"] = json.loads(str(run["permissions"]))
        return run

    def _update_agent_run_sync(
        self,
        run_id: str,
        status: str | None = None,
        agent_id: str | None = None,
    ) -> dict[str, Any] | None:
        current = self._get_agent_run_sync(run_id)
        if current is None:
            return None
        updated_at = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE agent_runs
                SET status = ?, agent_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    status if status is not None else current["status"],
                    agent_id if agent_id is not None else current["agent_id"],
                    updated_at,
                    run_id,
                ),
            )
            conn.commit()
        return self._get_agent_run_sync(run_id)

    def _append_agent_log_sync(
        self,
        run_id: str,
        action: str,
        tool: str,
        privacy_level: str,
        input_text: str | None,
        output_text: str | None,
        model: str | None,
        error: str | None,
    ) -> dict[str, Any]:
        log_id = str(uuid4())
        ts = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_logs (
                    id, run_id, ts, action, tool, input, output, model, privacy_level, error
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log_id,
                    run_id,
                    ts,
                    action,
                    tool,
                    input_text,
                    output_text,
                    model,
                    privacy_level,
                    error,
                ),
            )
            conn.commit()
        return {
            "id": log_id,
            "run_id": run_id,
            "ts": ts,
            "action": action,
            "tool": tool,
            "input": input_text,
            "output": output_text,
            "model": model,
            "privacy_level": privacy_level,
            "error": error,
        }

    def _list_agent_logs_sync(self, run_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, run_id, ts, action, tool, input, output, model, privacy_level, error
                FROM agent_logs
                WHERE run_id = ?
                ORDER BY ts ASC
                """,
                (run_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _decode_room(row: dict[str, Any]) -> dict[str, Any]:
        room = dict(row)
        room["allowed_models"] = json.loads(str(room["allowed_models"]))
        return room

    def _connect(self) -> Any:
        if hasattr(self._local, "conn"):
            return self._local.conn

        driver = self._driver()
        conn = driver.connect(str(self.path))
        conn.row_factory = self._row_factory
        if SQLCIPHER_AVAILABLE:
            conn.execute(f"PRAGMA key = {self._sql_literal(self._get_or_create_key())}")
            conn.execute("PRAGMA cipher_page_size = 4096")
            conn.execute("PRAGMA kdf_iter = 256000")
            conn.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA512")
            conn.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512")
        
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        
        self._local.conn = conn
        return conn

    def _driver(self) -> Any:
        if SQLCIPHER_AVAILABLE and sqlcipher3 is not None:
            return sqlcipher3
        if self.settings.allow_plaintext_dev_db:
            self.logger.emit("sqlcipher.unavailable.dev_plaintext")
            return sqlite3
        raise RuntimeError(
            "sqlcipher3 is required for encrypted production storage. "
            "Install sqlcipher3-binary or set ASTERION_ALLOW_PLAINTEXT_SQLITE_FOR_DEV=1 "
            "only for local development."
        )

    def _get_or_create_key(self) -> str:
        try:
            key = keyring.get_password(self.settings.keyring_service, self.settings.keyring_db_key_name)
            if key:
                return key
            key = secrets.token_urlsafe(48)
            keyring.set_password(self.settings.keyring_service, self.settings.keyring_db_key_name, key)
            self.logger.emit("keyring.created", key_name=self.settings.keyring_db_key_name)
            return key
        except keyring.errors.KeyringError:
            if self.settings.allow_plaintext_dev_db:
                fallback = f"dev-key-{self.settings.keyring_service}-{self.settings.keyring_db_key_name}"
                self.logger.emit("keyring.fallback_dev", reason="keyring unavailable")
                return fallback
            raise

    @staticmethod
    def _sql_literal(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    @staticmethod
    def _row_factory(cursor: Any, row: tuple[Any, ...]) -> dict[str, Any]:
        return {column[0]: row[index] for index, column in enumerate(cursor.description)}
