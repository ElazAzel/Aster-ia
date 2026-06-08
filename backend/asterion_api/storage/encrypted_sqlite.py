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
        self._open_conns: list[Any] = []
        self._conns_lock = threading.Lock()

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

    def _schema_version_sync(self) -> int:
        with self._connect() as conn:
            return current_version(conn)

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

    async def get_memory(self, memory_id: str) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._get_memory_sync, memory_id)

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

    async def cleanup_expired_memories(self) -> int:
        return await asyncio.to_thread(self._cleanup_expired_memories_sync)

    async def expire_memories(self) -> int:
        return await asyncio.to_thread(self._cleanup_expired_memories_sync)

    def _cleanup_expired_memories_sync(self) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at <= ?",
                (datetime.now(UTC).isoformat(),),
            )
            conn.commit()
        return cursor.rowcount

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
                    artifact_id TEXT,
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
            conn.execute(
                "DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at <= ?",
                (datetime.now(UTC).isoformat(),),
            )
            conn.commit()
            version = run_migrations(conn)
        self.logger.emit("schema.ready", db_path=str(self.path), version=version)

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
                    GROUP BY c.id, c.room_id, c.title, c.created_at
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
                    GROUP BY c.id, c.room_id, c.title, c.created_at
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

    # ── Rooms CRUD ──────────────────────────────────────────────────────────

    async def list_rooms(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._list_rooms_sync)

    def _list_rooms_sync(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, name, color, allowed_models, memory_policy, retention_days, "
                "created_at, updated_at, COALESCE(system_prompt, '') AS system_prompt "
                "FROM rooms ORDER BY created_at DESC"
            ).fetchall()
        return [self._deserialize_room(row) for row in rows]

    async def create_room(
        self,
        room_id: str | None,
        name: str,
        color: str,
        allowed_models: list[str],
        memory_policy: str,
        retention_days: int,
        system_prompt: str = "",
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._create_room_sync, room_id, name, color, allowed_models,
            memory_policy, retention_days, system_prompt,
        )

    def _create_room_sync(
        self, room_id: str | None, name: str, color: str,
        allowed_models: list[str], memory_policy: str, retention_days: int,
        system_prompt: str,
    ) -> dict[str, Any]:
        rid = room_id or str(uuid4())
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO rooms (id, name, color, allowed_models, memory_policy, "
                "retention_days, created_at, updated_at, system_prompt) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (rid, name, color, json.dumps(allowed_models), memory_policy,
                 retention_days, now, now, system_prompt),
            )
            conn.commit()
        return self._get_room_sync(rid)  # type: ignore[return-value]

    async def get_room(self, room_id: str) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._get_room_sync, room_id)

    def _get_room_sync(self, room_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, name, color, allowed_models, memory_policy, retention_days, "
                "created_at, updated_at, COALESCE(system_prompt, '') AS system_prompt "
                "FROM rooms WHERE id = ?", (room_id,),
            ).fetchone()
        return self._deserialize_room(row) if row is not None else None

    async def update_room(
        self, room_id: str, *, name: str | None = None, color: str | None = None,
        allowed_models: list[str] | None = None, memory_policy: str | None = None,
        retention_days: int | None = None, system_prompt: str | None = None,
    ) -> dict[str, Any] | None:
        return await asyncio.to_thread(
            self._update_room_sync, room_id, name, color, allowed_models,
            memory_policy, retention_days, system_prompt,
        )

    def _update_room_sync(
        self, room_id: str, name: str | None, color: str | None,
        allowed_models: list[str] | None, memory_policy: str | None,
        retention_days: int | None, system_prompt: str | None,
    ) -> dict[str, Any] | None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            existing = conn.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
            if existing is None:
                return None
            old = dict(existing)
            conn.execute(
                "UPDATE rooms SET name=?, color=?, allowed_models=?, memory_policy=?, "
                "retention_days=?, updated_at=?, system_prompt=? WHERE id=?",
                (
                    name or old["name"],
                    color or old["color"],
                    json.dumps(allowed_models if allowed_models is not None else json.loads(old["allowed_models"])),
                    memory_policy or old["memory_policy"],
                    retention_days if retention_days is not None else old["retention_days"],
                    now,
                    system_prompt if system_prompt is not None else old.get("system_prompt", ""),
                    room_id,
                ),
            )
            conn.commit()
        return self._get_room_sync(room_id)

    async def delete_room(self, room_id: str) -> bool:
        return await asyncio.to_thread(self._delete_room_sync, room_id)

    def _delete_room_sync(self, room_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM rooms WHERE id = ?", (room_id,))
            conn.commit()
        return cursor.rowcount > 0

    @staticmethod
    def _deserialize_room(row: dict[str, Any]) -> dict[str, Any]:
        d = dict(row)
        d["allowed_models"] = json.loads(d["allowed_models"])
        return d

    # ── Artifacts CRUD ──────────────────────────────────────────────────────

    async def create_artifact(
        self, room_id: str, kind: str, title: str,
        blocks: list[dict[str, Any]], source: str,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._create_artifact_sync, room_id, kind, title, blocks, source,
        )

    def _create_artifact_sync(
        self, room_id: str, kind: str, title: str,
        blocks: list[dict[str, Any]], source: str,
    ) -> dict[str, Any]:
        artifact_id = str(uuid4())
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO artifacts (id, room_id, kind, title, blocks, source, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (artifact_id, room_id, kind, title, json.dumps(blocks), source, now),
            )
            conn.commit()
        return {"id": artifact_id, "room_id": room_id, "kind": kind, "title": title,
                "blocks": blocks, "source": source, "created_at": now}

    async def list_artifacts(self, room_id: str | None = None) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._list_artifacts_sync, room_id)

    def _list_artifacts_sync(self, room_id: str | None) -> list[dict[str, Any]]:
        with self._connect() as conn:
            if room_id:
                rows = conn.execute(
                    "SELECT id, room_id, kind, title, blocks, source, created_at "
                    "FROM artifacts WHERE room_id = ? ORDER BY created_at DESC", (room_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, room_id, kind, title, blocks, source, created_at "
                    "FROM artifacts ORDER BY created_at DESC"
                ).fetchall()
        return [self._deserialize_artifact(row) for row in rows]

    async def get_artifact(self, artifact_id: str) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._get_artifact_sync, artifact_id)

    def _get_artifact_sync(self, artifact_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, room_id, kind, title, blocks, source, created_at "
                "FROM artifacts WHERE id = ?", (artifact_id,),
            ).fetchone()
        return self._deserialize_artifact(row) if row is not None else None

    @staticmethod
    def _deserialize_artifact(row: dict[str, Any]) -> dict[str, Any]:
        d = dict(row)
        d["blocks"] = json.loads(d["blocks"])
        return d

    async def update_artifact(
        self, artifact_id: str, title: str | None = None,
        blocks: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._update_artifact_sync, artifact_id, title, blocks)

    def _update_artifact_sync(
        self, artifact_id: str, title: str | None, blocks: list[dict[str, Any]] | None,
    ) -> dict[str, Any] | None:
        with self._connect() as conn:
            if title is not None:
                conn.execute("UPDATE artifacts SET title = ? WHERE id = ?", (title, artifact_id))
            if blocks is not None:
                conn.execute("UPDATE artifacts SET blocks = ? WHERE id = ?", (json.dumps(blocks), artifact_id))
            conn.commit()
            row = conn.execute(
                "SELECT id, room_id, kind, title, blocks, source, created_at "
                "FROM artifacts WHERE id = ?", (artifact_id,),
            ).fetchone()
        return self._deserialize_artifact(row) if row is not None else None

    async def delete_artifact(self, artifact_id: str) -> bool:
        return await asyncio.to_thread(self._delete_artifact_sync, artifact_id)

    def _delete_artifact_sync(self, artifact_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM artifacts WHERE id = ?", (artifact_id,))
            conn.commit()
            return cur.rowcount > 0

    # ── Audit Logs ──────────────────────────────────────────────────────────

    async def record_audit_log(
        self, action: str, resource: str, details: str | None = None,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(self._record_audit_log_sync, action, resource, details)

    def _record_audit_log_sync(
        self, action: str, resource: str, details: str | None,
    ) -> dict[str, Any]:
        log_id = str(uuid4())
        ts = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO audit_logs (id, action, resource, details, ts) VALUES (?, ?, ?, ?, ?)",
                (log_id, action, resource, details, ts),
            )
            conn.commit()
        return {"id": log_id, "action": action, "resource": resource, "details": details, "ts": ts}

    async def list_audit_logs(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._list_audit_logs_sync)

    def _list_audit_logs_sync(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, action, resource, details, ts FROM audit_logs ORDER BY ts DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    # ── Research Receipts ───────────────────────────────────────────────────

    async def save_research_receipt(
        self, report_id: str, source_title: str, url: str | None,
        quote: str | None, claim: str, confidence: str,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._save_research_receipt_sync, report_id, source_title, url, quote, claim, confidence,
        )

    def _save_research_receipt_sync(
        self, report_id: str, source_title: str, url: str | None,
        quote: str | None, claim: str, confidence: str,
    ) -> dict[str, Any]:
        receipt_id = str(uuid4())
        ts = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO research_receipts (id, report_id, source_title, url, quote, claim, confidence, ts) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (receipt_id, report_id, source_title, url, quote, claim, confidence, ts),
            )
            conn.commit()
        return {"id": receipt_id, "report_id": report_id, "source_title": source_title,
                "url": url, "quote": quote, "claim": claim, "confidence": confidence, "ts": ts}

    async def get_all_research_receipts(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._get_all_research_receipts_sync)

    def _get_all_research_receipts_sync(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, report_id, source_title, url, quote, claim, confidence, ts "
                "FROM research_receipts ORDER BY ts DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    # ── Agent Runs / Logs ───────────────────────────────────────────────────

    async def get_all_agent_runs(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._get_all_agent_runs_sync)

    def _get_all_agent_runs_sync(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, agent_id, room_id, status, plan, permissions, created_at, updated_at "
                "FROM agent_runs ORDER BY created_at DESC"
            ).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["plan"] = json.loads(d["plan"])
            d["permissions"] = json.loads(d["permissions"])
            results.append(d)
        return results

    async def create_agent_run(
        self, agent_id: str, room_id: str, task: str,
        plan: dict[str, Any], permissions: dict[str, Any],
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._create_agent_run_sync, agent_id, room_id, task, plan, permissions,
        )

    def _create_agent_run_sync(
        self, agent_id: str, room_id: str, task: str,
        plan: dict[str, Any], permissions: dict[str, Any],
    ) -> dict[str, Any]:
        run_id = str(uuid4())
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO agent_runs (id, agent_id, room_id, status, plan, permissions, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (run_id, agent_id, room_id, "planned", json.dumps(plan), json.dumps(permissions), now, now),
            )
            conn.commit()
        return {"id": run_id, "agent_id": agent_id, "room_id": room_id, "status": "planned",
                "plan": plan, "permissions": permissions, "created_at": now, "updated_at": now}

    async def get_agent_run(self, run_id: str) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._get_agent_run_sync, run_id)

    def _get_agent_run_sync(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, agent_id, room_id, status, plan, permissions, created_at, updated_at "
                "FROM agent_runs WHERE id = ?", (run_id,),
            ).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["plan"] = json.loads(d["plan"])
        d["permissions"] = json.loads(d["permissions"])
        return d

    async def update_agent_run(
        self, run_id: str, *, status: str | None = None, agent_id: str | None = None,
    ) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._update_agent_run_sync, run_id, status, agent_id)

    def _update_agent_run_sync(
        self, run_id: str, status: str | None, agent_id: str | None,
    ) -> dict[str, Any] | None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            existing = conn.execute("SELECT * FROM agent_runs WHERE id = ?", (run_id,)).fetchone()
            if existing is None:
                return None
            old = dict(existing)
            conn.execute(
                "UPDATE agent_runs SET status=?, agent_id=?, updated_at=? WHERE id=?",
                (status or old["status"], agent_id or old["agent_id"], now, run_id),
            )
            conn.commit()
        return self._get_agent_run_sync(run_id)

    async def append_agent_log(
        self, run_id: str, action: str, tool: str,
        input_text: str | None = None, output_text: str | None = None,
        model: str | None = None, privacy_level: str = "local", error: str | None = None,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._append_agent_log_sync, run_id, action, tool,
            input_text, output_text, model, privacy_level, error,
        )

    def _append_agent_log_sync(
        self, run_id: str, action: str, tool: str,
        input_text: str | None, output_text: str | None,
        model: str | None, privacy_level: str, error: str | None,
    ) -> dict[str, Any]:
        log_id = str(uuid4())
        ts = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO agent_logs (id, run_id, ts, action, tool, input, output, model, privacy_level, error) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (log_id, run_id, ts, action, tool, input_text, output_text, model, privacy_level, error),
            )
            conn.commit()
        return {"id": log_id, "run_id": run_id, "ts": ts, "action": action, "tool": tool,
                "input": input_text, "output": output_text, "model": model,
                "privacy_level": privacy_level, "error": error}

    async def list_agent_logs(self, run_id: str) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._list_agent_logs_sync, run_id)

    def _list_agent_logs_sync(self, run_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, run_id, ts, action, tool, input, output, model, privacy_level, error "
                "FROM agent_logs WHERE run_id = ? ORDER BY ts ASC", (run_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    async def get_all_agent_logs(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._get_all_agent_logs_sync)

    def _get_all_agent_logs_sync(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, run_id, ts, action, tool, input, output, model, privacy_level, error "
                "FROM agent_logs ORDER BY ts DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    # ── Dump / Restore / Wipe ───────────────────────────────────────────────

    async def dump_all_data(self) -> dict[str, Any]:
        return await asyncio.to_thread(self._dump_all_data_sync)

    def _dump_all_data_sync(self) -> dict[str, Any]:
        with self._connect() as conn:
            data: dict[str, list[dict[str, Any]]] = {}
            for table in ("rooms", "conversations", "messages", "memories",
                          "artifacts", "research_receipts", "agent_runs",
                          "agent_logs", "audit_logs", "workflow_runs"):
                rows = conn.execute(f"SELECT * FROM {table}").fetchall()
                data[table] = [dict(row) for row in rows]
        return data

    async def restore_all_data(self, dump: dict[str, Any]) -> None:
        await asyncio.to_thread(self._restore_all_data_sync, dump)

    def _restore_all_data_sync(self, dump: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA foreign_keys = OFF")
            for table in ("agent_logs", "messages", "memories", "artifacts",
                          "research_receipts", "agent_runs", "conversations",
                          "rooms", "audit_logs", "workflow_runs"):
                conn.execute(f"DELETE FROM {table}")
            conn.execute("PRAGMA foreign_keys = ON")
            for table, rows in dump.items():
                if not rows:
                    continue
                cols = list(rows[0].keys())
                placeholders = ", ".join(["?"] * len(cols))
                col_names = ", ".join(cols)
                for row in rows:
                    values = [json.dumps(v) if isinstance(v, (dict, list)) else v for v in [row[c] for c in cols]]
                    conn.execute(f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})", values)
            conn.commit()

    async def wipe_all_data(self) -> None:
        await asyncio.to_thread(self._wipe_all_data_sync)

    def _wipe_all_data_sync(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA foreign_keys = OFF")
            for table in ("agent_logs", "messages", "memories", "artifacts",
                          "research_receipts", "agent_runs", "conversations",
                          "rooms", "audit_logs", "workflow_runs", "rag_documents",
                          "rag_folder_scopes", "schema_migrations"):
                conn.execute(f"DELETE FROM {table}")
            conn.execute("PRAGMA foreign_keys = ON")
            conn.commit()

    # ── RAG Documents ───────────────────────────────────────────────────────

    async def list_rag_documents(self, room_id: str | None = None) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._list_rag_documents_sync, room_id)

    def _list_rag_documents_sync(self, room_id: str | None) -> list[dict[str, Any]]:
        with self._connect() as conn:
            if room_id:
                rows = conn.execute(
                    "SELECT id, room_id, source, indexed_chunks, created_at "
                    "FROM rag_documents WHERE room_id = ? ORDER BY created_at DESC", (room_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, room_id, source, indexed_chunks, created_at "
                    "FROM rag_documents ORDER BY created_at DESC"
                ).fetchall()
        return [dict(row) for row in rows]

    # ── RAG Folder Scopes ──────────────────────────────────────────────────

    async def create_rag_folder_scope(
        self, room_id: str, path: str, label: str | None = None, recursive: bool = True,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._create_rag_folder_scope_sync, room_id, path, label, recursive,
        )

    def _create_rag_folder_scope_sync(
        self, room_id: str, path: str, label: str | None, recursive: bool,
    ) -> dict[str, Any]:
        scope_id = str(uuid4())
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO rag_folder_scopes (id, room_id, path, label, recursive, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (scope_id, room_id, path, label, 1 if recursive else 0, now),
            )
            conn.commit()
        return {"id": scope_id, "room_id": room_id, "path": path,
                "label": label, "recursive": recursive, "created_at": now}

    async def list_rag_folder_scopes(self, room_id: str | None = None) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._list_rag_folder_scopes_sync, room_id)

    def _list_rag_folder_scopes_sync(self, room_id: str | None) -> list[dict[str, Any]]:
        with self._connect() as conn:
            if room_id:
                rows = conn.execute(
                    "SELECT id, room_id, path, label, recursive, created_at "
                    "FROM rag_folder_scopes WHERE room_id = ? ORDER BY created_at DESC", (room_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, room_id, path, label, recursive, created_at "
                    "FROM rag_folder_scopes ORDER BY created_at DESC"
                ).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["recursive"] = bool(d["recursive"])
            results.append(d)
        return results

    async def delete_rag_folder_scope(self, scope_id: str) -> bool:
        return await asyncio.to_thread(self._delete_rag_folder_scope_sync, scope_id)

    def _delete_rag_folder_scope_sync(self, scope_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM rag_folder_scopes WHERE id = ?", (scope_id,))
            conn.commit()
        return cursor.rowcount > 0

    def _connect(self) -> Any:
        if hasattr(self._local, "conn"):
            try:
                self._local.conn.execute("SELECT 1")
                return self._local.conn
            except Exception:
                with self._conns_lock:
                    if self._local.conn in self._open_conns:
                        self._open_conns.remove(self._local.conn)
                delattr(self._local, "conn")

        driver = self._driver()
        conn = driver.connect(str(self.path))
        conn.row_factory = self._row_factory
        try:
            if SQLCIPHER_AVAILABLE:
                conn.execute(f"PRAGMA key = {self._sql_literal(self._get_or_create_key())}")
                conn.execute("PRAGMA cipher_page_size = 4096")
                conn.execute("PRAGMA kdf_iter = 256000")
                conn.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA512")
                conn.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512")
            conn.execute("PRAGMA journal_mode = WAL;")
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            # Database might have incorrect/deleted key from keyring (e.g. after a partial wipe on Windows).
            # Attempt to clean up and reconnect to a fresh database.
            try:
                self.path.unlink()
            except Exception:
                pass
            for suffix in ["-wal", "-shm"]:
                try:
                    self.path.with_name(self.path.name + suffix).unlink()
                except Exception:
                    pass
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
        with self._conns_lock:
            self._open_conns.append(conn)
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
