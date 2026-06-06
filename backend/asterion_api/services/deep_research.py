from __future__ import annotations

import asyncio
from typing import Any, Mapping

import httpx

from asterion_api.harness import BaseHarness
from asterion_api.schemas import DeepResearchResponse, ResearchResult
from asterion_api.services.privacy_analyzer import PrivacyAnalyzer


class SupervisorAgent(BaseHarness):
    privacy_level = "local"

    def __init__(self, analyzer: PrivacyAnalyzer) -> None:
        self.analyzer = analyzer
        self.searxng_url = "http://127.0.0.1:8080"

    async def execute(self, payload: Mapping[str, Any] | None = None) -> DeepResearchResponse:
        payload = payload or {}
        return await self.research(
            query=str(payload["query"]),
            max_subtasks=int(payload.get("max_subtasks", 5)),
            web_access=bool(payload.get("web_access", True)),
        )

    def get_state(self) -> dict[str, Any]:
        return {"searxng_url": self.searxng_url}

    def set_state(self, state: Mapping[str, Any]) -> None:
        if state.get("searxng_url"):
            self.searxng_url = str(state["searxng_url"]).rstrip("/")

    def decompose(self, query: str, max_subtasks: int) -> list[str]:
        aspects = [
            "core facts and definitions",
            "recent evidence and examples",
            "risks and constraints",
            "implementation options",
            "open questions",
        ]
        return [f"{query} - {aspect}" for aspect in aspects[:max_subtasks]]

    async def research(self, *, query: str, max_subtasks: int, web_access: bool) -> DeepResearchResponse:
        privacy = self.analyzer.analyze(
            model_type="local",
            files_attached=False,
            memory_enabled=False,
            web_access=web_access,
        )
        subtasks = self.decompose(query, max_subtasks)
        if not web_access:
            return DeepResearchResponse(query=query, subtasks=subtasks, results=[], privacy=privacy)

        agents = [SubAgent(self.searxng_url, subtask) for subtask in subtasks]
        nested = await asyncio.gather(*(agent.search() for agent in agents))
        results = [item for group in nested for item in group]
        self._aggregate_duckdb(results)
        return DeepResearchResponse(query=query, subtasks=subtasks, results=results, privacy=privacy)

    @staticmethod
    def _aggregate_duckdb(results: list[ResearchResult]) -> None:
        import duckdb

        conn = duckdb.connect(":memory:")
        conn.execute(
            "CREATE TABLE research_results(subtask VARCHAR, title VARCHAR, url VARCHAR, snippet VARCHAR)"
        )
        conn.executemany(
            "INSERT INTO research_results VALUES (?, ?, ?, ?)",
            [(item.subtask, item.title, item.url, item.snippet) for item in results],
        )
        conn.execute("SELECT count(*) FROM research_results").fetchone()
        conn.close()


class SubAgent:
    def __init__(self, searxng_url: str, subtask: str) -> None:
        self.searxng_url = searxng_url.rstrip("/")
        self.subtask = subtask

    async def search(self) -> list[ResearchResult]:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=1.0)) as client:
            response = await client.get(
                f"{self.searxng_url}/search",
                params={"q": self.subtask, "format": "json"},
            )
            response.raise_for_status()
            payload = response.json()
        rows = payload.get("results", [])[:5]
        return [
            ResearchResult(
                subtask=self.subtask,
                title=str(row.get("title", "")),
                url=row.get("url"),
                snippet=row.get("content") or row.get("snippet"),
            )
            for row in rows
        ]
