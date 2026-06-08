from __future__ import annotations

import asyncio
import json
import secrets
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

import keyring

from asterion_api.config import Settings
from asterion_api.harness import BaseHarness
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
    ) -> str:
        return await asyncio.to_thread(
            self._append_message_sync,
            conv_id,
            role,
            content,
            model,
        )

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

    async def save_workflow_run(
        self,
        run_id: str,
        status: str,
        workflow: dict[str, Any],
        results: list[dict[str, Any]],
    ) -> None:
        await asyncio.to_thread(self._save_workflow_run_sync, run_id, status, workflow, results)

    async def get_workflow_run(self, run_id: str) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._get_workflow_run_sync, run_id)

    async def list_active_workflow_runs(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._list_active_workflow_runs_sync)

    def _ensure_schema_sync(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    room_id TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conv_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK(role IN ('system', 'user', 'assistant', 'tool')),
                    content TEXT NOT NULL,
                    model TEXT,
                    ts TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_conversations_room_id ON conversations(room_id)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_conv_ts ON messages(conv_id, ts)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    room_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_room_id ON memories(room_id)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_runs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    workflow TEXT NOT NULL,
                    results TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_workflow_runs_status ON workflow_runs(status)")
            conn.commit()
        self.logger.emit("schema.ready", db_path=str(self.path))

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
    ) -> str:
        message_id = str(uuid4())
        ts = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO messages (id, conv_id, role, content, model, ts)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (message_id, conv_id, role, content, model, ts),
            )
            conn.commit()
        return message_id

    def _list_messages_sync(self, conv_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, conv_id, role, content, model, ts
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

    def _save_workflow_run_sync(
        self,
        run_id: str,
        status: str,
        workflow: dict[str, Any],
        results: list[dict[str, Any]],
    ) -> None:
        now = datetime.now(UTC).isoformat()
        wf_str = json.dumps(workflow)
        res_str = json.dumps(results)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO workflow_runs (id, status, workflow, results, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    results = excluded.results,
                    updated_at = excluded.updated_at
                """,
                (run_id, status, wf_str, res_str, now, now),
            )
            conn.commit()

    def _get_workflow_run_sync(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, status, workflow, results, created_at, updated_at
                FROM workflow_runs
                WHERE id = ?
                """,
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "status": row["status"],
            "workflow": json.loads(row["workflow"]),
            "results": json.loads(row["results"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _list_active_workflow_runs_sync(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, status, workflow, results, created_at, updated_at
                FROM workflow_runs
                WHERE status = 'paused'
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [
            {
                "id": row["id"],
                "status": row["status"],
                "workflow": json.loads(row["workflow"]),
                "results": json.loads(row["results"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    def _connect(self) -> Any:
        driver = self._driver()
        conn = driver.connect(str(self.path))
        conn.row_factory = self._row_factory
        if SQLCIPHER_AVAILABLE:
            conn.execute(f"PRAGMA key = {self._sql_literal(self._get_or_create_key())}")
            conn.execute("PRAGMA cipher_page_size = 4096")
            conn.execute("PRAGMA kdf_iter = 256000")
            conn.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA512")
            conn.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512")
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
        key = keyring.get_password(self.settings.keyring_service, self.settings.keyring_db_key_name)
        if key:
            return key
        key = secrets.token_urlsafe(48)
        keyring.set_password(self.settings.keyring_service, self.settings.keyring_db_key_name, key)
        self.logger.emit("keyring.created", key_name=self.settings.keyring_db_key_name)
        return key

    @staticmethod
    def _sql_literal(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    @staticmethod
    def _row_factory(cursor: Any, row: tuple[Any, ...]) -> dict[str, Any]:
        return {column[0]: row[index] for index, column in enumerate(cursor.description)}
