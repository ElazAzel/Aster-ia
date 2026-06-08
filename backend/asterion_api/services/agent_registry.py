from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Mapping

from asterion_api.harness import BaseHarness
from asterion_api.schemas import AgentCatalog, AgentManifest, RuntimeSkillManifest


class AgentRegistry(BaseHarness):
    privacy_level = "local"
    _cache_ttl = 30.0

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[3]
        self.agents_dir = self.project_root / "agents"
        self.skills_dir = self.project_root / "skills"
        self._agents_cache: list[AgentManifest] | None = None
        self._skills_cache: list[RuntimeSkillManifest] | None = None
        self._cache_time: float = 0.0

    async def execute(self, payload: Mapping[str, Any] | None = None) -> AgentCatalog:
        return self.catalog()

    def get_state(self) -> dict[str, Any]:
        return {
            "agents_dir": str(self.agents_dir),
            "skills_dir": str(self.skills_dir),
        }

    def set_state(self, state: Mapping[str, Any]) -> None:
        if state.get("agents_dir"):
            self.agents_dir = Path(str(state["agents_dir"]))
            self._invalidate()
        if state.get("skills_dir"):
            self.skills_dir = Path(str(state["skills_dir"]))
            self._invalidate()

    def _invalidate(self) -> None:
        self._agents_cache = None
        self._skills_cache = None
        self._cache_time = 0.0

    def _is_cache_valid(self) -> bool:
        return (self._agents_cache is not None and self._skills_cache is not None
                and (time.monotonic() - self._cache_time) < self._cache_ttl)

    def catalog(self) -> AgentCatalog:
        return AgentCatalog(agents=self.list_agents(), skills=self.list_skills())

    def list_agents(self) -> list[AgentManifest]:
        if not self._is_cache_valid():
            self._agents_cache = [AgentManifest(**data) for data in self._load_json_files(self.agents_dir)]
            self._skills_cache = [RuntimeSkillManifest(**data) for data in self._load_json_files(self.skills_dir)]
            self._cache_time = time.monotonic()
        return self._agents_cache

    def list_skills(self) -> list[RuntimeSkillManifest]:
        if not self._is_cache_valid():
            self.list_agents()
        return self._skills_cache

    def get_agent(self, agent_id: str) -> AgentManifest | None:
        return next((agent for agent in self.list_agents() if agent.id == agent_id), None)

    def get_skill(self, skill_id: str) -> RuntimeSkillManifest | None:
        return next((skill for skill in self.list_skills() if skill.id == skill_id), None)

    @staticmethod
    def _load_json_files(folder: Path) -> list[dict[str, Any]]:
        if not folder.exists():
            return []
        items: list[dict[str, Any]] = []
        for path in sorted(folder.glob("*.json")):
            items.append(json.loads(path.read_text(encoding="utf-8")))
        return items
