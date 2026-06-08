from __future__ import annotations

import duckdb
import pandas as pd
from fastapi import APIRouter, Depends

from asterion_api.config import Settings, get_settings
from asterion_api.dependencies import get_store
from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/research/stats")
async def research_stats(
    settings: Settings = Depends(get_settings),
    store: EncryptedSQLiteStore = Depends(get_store),
) -> dict[str, object]:
    receipts = await store.get_all_research_receipts()
    df_receipts = pd.DataFrame(receipts)
    if df_receipts.empty:
        df_receipts = pd.DataFrame(columns=[
            "id", "report_id", "source_title", "url", "quote", "claim", "confidence", "ts", "room_id", "room_name"
        ])

    conn = duckdb.connect(":memory:")
    conn.execute(f"SET memory_limit = '{settings.duckdb_memory_limit}'")
    conn.execute(f"SET threads = {settings.duckdb_threads}")
    conn.register("receipts", df_receipts)

    stats_query = """
    SELECT 
        COUNT(DISTINCT report_id) as total_research_queries,
        COUNT(DISTINCT COALESCE(url, source_title)) as sources_consulted,
        COUNT(*) as claims_verified
    FROM receipts
    """
    row = conn.execute(stats_query).fetchone()
    conn.close()

    return {
        "total_research_queries": row[0] if row else 0,
        "sources_consulted": row[1] if row else 0,
        "claims_verified": row[2] if row else 0,
    }


@router.get("/top-sources")
async def top_sources(
    settings: Settings = Depends(get_settings),
    store: EncryptedSQLiteStore = Depends(get_store),
) -> list[dict[str, object]]:
    receipts = await store.get_all_research_receipts()
    df_receipts = pd.DataFrame(receipts)
    if df_receipts.empty:
        return []

    conn = duckdb.connect(":memory:")
    conn.execute(f"SET memory_limit = '{settings.duckdb_memory_limit}'")
    conn.execute(f"SET threads = {settings.duckdb_threads}")
    conn.register("receipts", df_receipts)

    query = """
    SELECT source_title as source, COUNT(*) as count
    FROM receipts
    GROUP BY source_title
    ORDER BY count DESC
    LIMIT 10
    """
    res = conn.execute(query).fetchall()
    conn.close()
    return [{"source": row[0], "count": row[1]} for row in res]


@router.get("/claims-confidence")
async def claims_confidence(
    settings: Settings = Depends(get_settings),
    store: EncryptedSQLiteStore = Depends(get_store),
) -> list[dict[str, object]]:
    receipts = await store.get_all_research_receipts()
    df_receipts = pd.DataFrame(receipts)
    if df_receipts.empty:
        return []

    conn = duckdb.connect(":memory:")
    conn.execute(f"SET memory_limit = '{settings.duckdb_memory_limit}'")
    conn.execute(f"SET threads = {settings.duckdb_threads}")
    conn.register("receipts", df_receipts)

    query = """
    SELECT confidence, COUNT(*) as count
    FROM receipts
    GROUP BY confidence
    ORDER BY count DESC
    """
    res = conn.execute(query).fetchall()
    conn.close()
    return [{"confidence": row[0], "count": row[1]} for row in res]


@router.get("/rooms-distribution")
async def rooms_distribution(
    settings: Settings = Depends(get_settings),
    store: EncryptedSQLiteStore = Depends(get_store),
) -> list[dict[str, object]]:
    receipts = await store.get_all_research_receipts()
    df_receipts = pd.DataFrame(receipts)
    if df_receipts.empty:
        return []

    conn = duckdb.connect(":memory:")
    conn.execute(f"SET memory_limit = '{settings.duckdb_memory_limit}'")
    conn.execute(f"SET threads = {settings.duckdb_threads}")
    conn.register("receipts", df_receipts)

    query = """
    SELECT report_id as room_name, COUNT(DISTINCT report_id) as count
    FROM receipts
    GROUP BY report_id
    ORDER BY count DESC
    """
    res = conn.execute(query).fetchall()
    conn.close()
    return [{"room_name": row[0], "count": row[1]} for row in res]


@router.get("/agent-stats")
async def agent_stats(
    settings: Settings = Depends(get_settings),
    store: EncryptedSQLiteStore = Depends(get_store),
) -> dict[str, object]:
    runs = await store.get_all_agent_runs()
    logs = await store.get_all_agent_logs()

    df_runs = pd.DataFrame(runs)
    df_logs = pd.DataFrame(logs)

    if df_runs.empty:
        df_runs = pd.DataFrame(columns=["id", "agent_id", "room_id", "status", "created_at", "updated_at", "room_name"])
    if df_logs.empty:
        df_logs = pd.DataFrame(columns=[
            "id", "run_id", "ts", "action", "tool", "input", "output", "model", "privacy_level", "error", "room_id", "room_name"
        ])

    conn = duckdb.connect(":memory:")
    conn.execute(f"SET memory_limit = '{settings.duckdb_memory_limit}'")
    conn.execute(f"SET threads = {settings.duckdb_threads}")
    conn.register("runs", df_runs)
    conn.register("logs", df_logs)

    total_runs = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    total_steps = conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]

    privacy_res = conn.execute("SELECT privacy_level, COUNT(*) FROM logs GROUP BY privacy_level").fetchall()
    privacy_dist = {row[0]: row[1] for row in privacy_res}

    error_count = conn.execute("SELECT COUNT(*) FROM logs WHERE error IS NOT NULL AND error != ''").fetchone()[0]

    conn.close()
    return {
        "total_runs": total_runs,
        "total_steps": total_steps,
        "privacy_distribution": privacy_dist,
        "error_count": error_count,
    }
