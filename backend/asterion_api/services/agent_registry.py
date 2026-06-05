from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from asterion_api.harness import BaseHarness
from asterion_api.schemas import AgentCatalog, AgentManifest, RuntimeSkillManifest


class AgentRegistry(BaseHarness):
    privacy_level = "local"

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[3]
        self.agents_dir = self.project_root / "agents"
        self.skills_dir = self.project_root / "skills"

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
        if state.get("skills_dir"):
            self.skills_dir = Path(str(state["skills_dir"]))

    def catalog(self) -> AgentCatalog:
        return AgentCatalog(agents=self.list_agents(), skills=self.list_skills())

    def list_agents(self) -> list[AgentManifest]:
        return [AgentManifest(**data) for data in self._load_json_files(self.agents_dir)]

    def list_skills(self) -> list[RuntimeSkillManifest]:
        return [RuntimeSkillManifest(**data) for data in self._load_json_files(self.skills_dir)]

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
