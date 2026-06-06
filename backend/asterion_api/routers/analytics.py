from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/research/stats")
async def research_stats() -> dict[str, object]:
    import duckdb
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE stats AS SELECT 'no_data' AS source, 0 AS count")
    row = conn.execute("SELECT * FROM stats").fetchone()
    conn.close()
    return {
        "total_research_queries": row[1] if row else 0,
        "sources_consulted": 0,
        "claims_verified": 0,
    }
