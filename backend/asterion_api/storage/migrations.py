"""Lightweight schema migration system for Asterion AI SQLite/SQLCipher storage.

Each migration is a plain function that receives a DB connection and runs DDL.
The ``schema_migrations`` table tracks which versions have been applied.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Callable

MigrationFn = Callable[[Any], None]

MIGRATIONS: list[tuple[int, str, MigrationFn]] = []


def _register(version: int, description: str) -> Callable[[MigrationFn], MigrationFn]:
    def decorator(fn: MigrationFn) -> MigrationFn:
        MIGRATIONS.append((version, description, fn))
        return fn
    return decorator


# ── helpers ──────────────────────────────────────────────────────────────────


def _ensure_migrations_table(conn: Any) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )


def current_version(conn: Any) -> int:
    """Return the latest applied migration version, or 0 if none."""
    _ensure_migrations_table(conn)
    row = conn.execute("SELECT MAX(version) AS v FROM schema_migrations").fetchone()
    if row is None:
        return 0
    # Handle both dict row_factory and plain tuple
    if isinstance(row, dict):
        val = row.get("v") or row.get("MAX(version)")
    else:
        val = row[0]
    return int(val) if val is not None else 0


def run_migrations(conn: Any) -> int:
    """Apply all pending migrations in order. Returns new schema version."""
    _ensure_migrations_table(conn)
    applied = current_version(conn)
    pending = sorted(
        [(v, d, fn) for v, d, fn in MIGRATIONS if v > applied],
        key=lambda t: t[0],
    )
    for version, description, fn in pending:
        fn(conn)
        conn.execute(
            "INSERT INTO schema_migrations (version, description, applied_at) VALUES (?, ?, ?)",
            (version, description, datetime.now(UTC).isoformat()),
        )
        conn.commit()
    return current_version(conn)


# ── Migration 001: Initial schema ────────────────────────────────────────────


@_register(1, "Initial schema: rooms, conversations, messages, memories, rag_documents, artifacts, research_receipts, agent_runs, agent_logs")
def migration_001(conn: Any) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rooms (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            color TEXT NOT NULL,
            allowed_models TEXT NOT NULL,
            memory_policy TEXT NOT NULL CHECK(memory_policy IN ('off', 'session', 'persistent')),
            retention_days INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
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
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_conv_ts ON messages(conv_id, ts)"
    )
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
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_memories_room_id ON memories(room_id)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rag_documents (
            id TEXT PRIMARY KEY,
            room_id TEXT NOT NULL,
            source TEXT NOT NULL,
            indexed_chunks INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_rag_documents_room_id ON rag_documents(room_id)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS artifacts (
            id TEXT PRIMARY KEY,
            room_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            title TEXT NOT NULL,
            blocks TEXT NOT NULL,
            source TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_artifacts_room_id ON artifacts(room_id)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS research_receipts (
            id TEXT PRIMARY KEY,
            report_id TEXT NOT NULL,
            source_title TEXT NOT NULL,
            url TEXT,
            quote TEXT,
            claim TEXT NOT NULL,
            confidence TEXT NOT NULL,
            ts TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_research_receipts_report ON research_receipts(report_id)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_runs (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            room_id TEXT NOT NULL,
            status TEXT NOT NULL,
            plan TEXT NOT NULL,
            permissions TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_runs_room ON agent_runs(room_id)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_logs (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
            ts TEXT NOT NULL,
            action TEXT NOT NULL,
            tool TEXT NOT NULL,
            input TEXT,
            output TEXT,
            model TEXT,
            privacy_level TEXT NOT NULL,
            error TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_logs_run_ts ON agent_logs(run_id, ts)"
    )
    # Seed default room
    now = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT OR IGNORE INTO rooms (
            id, name, color, allowed_models, memory_policy, retention_days, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("default", "Default Room", "#2f80ed", json.dumps([]), "session", 30, now, now),
    )


# ── Migration 002: Phase 2A Chat Context ─────────────────────────────────────


@_register(2, "Add system_prompt to rooms and title to conversations")
def migration_002(conn: Any) -> None:
    try:
        conn.execute("ALTER TABLE rooms ADD COLUMN system_prompt TEXT NOT NULL DEFAULT ''")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE conversations ADD COLUMN title TEXT")
    except Exception:
        pass


# ── Migration 003: Phase 4 Security and Privacy Hardening ─────────────────────


@_register(3, "Create audit_logs table for user consent and privacy decisions")
def migration_003(conn: Any) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY,
            action TEXT NOT NULL,       -- 'approve', 'deny', 'grant', 'revoke', etc.
            resource TEXT NOT NULL,     -- 'plugin:name', 'agent:run_id', 'deep_research', etc.
            details TEXT,               -- JSON details or text
            ts TEXT NOT NULL            -- ISO timestamp
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_ts ON audit_logs(ts)")


# RAG folder approval scopes


@_register(4, "Create room-scoped RAG folder approval scopes")
def migration_004(conn: Any) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rag_folder_scopes (
            id TEXT PRIMARY KEY,
            room_id TEXT NOT NULL,
            path TEXT NOT NULL,
            label TEXT,
            recursive INTEGER NOT NULL DEFAULT 1 CHECK(recursive IN (0, 1)),
            created_at TEXT NOT NULL,
            UNIQUE(room_id, path)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_rag_folder_scopes_room ON rag_folder_scopes(room_id)"
    )

