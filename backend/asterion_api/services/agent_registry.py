from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Mapping

from pydantic import ValidationError

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

    def validate_catalog(self) -> dict[str, Any]:
        raw_agents = self._load_json_files(self.agents_dir)
        raw_skills = self._load_json_files(self.skills_dir)

        errors: list[str] = []
        warnings: list[str] = []
        agents: list[AgentManifest] = []
        skills: list[RuntimeSkillManifest] = []

        for data in raw_agents:
            try:
                agents.append(AgentManifest(**data))
            except ValidationError as exc:
                errors.append(f"agent:{data.get('id', '<unknown>')}: {exc.errors()}")

        for data in raw_skills:
            try:
                skills.append(RuntimeSkillManifest(**data))
            except ValidationError as exc:
                errors.append(f"skill:{data.get('id', '<unknown>')}: {exc.errors()}")

        agent_ids = [agent.id for agent in agents]
        skill_ids = [skill.id for skill in skills]
        self._append_duplicate_errors("agent", agent_ids, errors)
        self._append_duplicate_errors("skill", skill_ids, errors)

        known_skill_ids = set(skill_ids)
        known_agent_ids = set(agent_ids)
        for agent in agents:
            missing_skills = sorted(set(agent.skills) - known_skill_ids)
            for skill_id in missing_skills:
                errors.append(f"agent:{agent.id}: unknown skill '{skill_id}'")

            missing_handoffs = sorted(set(agent.handoff_targets) - known_agent_ids)
            for target_id in missing_handoffs:
                errors.append(f"agent:{agent.id}: unknown handoff target '{target_id}'")

            if agent.privacy_level == "local" and agent.permissions.network:
                warnings.append(f"agent:{agent.id}: local privacy with network=true")
            if agent.privacy_level == "local" and agent.permissions.shell:
                warnings.append(f"agent:{agent.id}: local privacy with shell=true")
            if not agent.acceptance_checks:
                warnings.append(f"agent:{agent.id}: missing acceptance checks")

        for skill in skills:
            if skill.privacy_level == "external" and not skill.requires_consent:
                errors.append(f"skill:{skill.id}: external skill must declare requires_consent")
            if not skill.acceptance_checks:
                warnings.append(f"skill:{skill.id}: missing acceptance checks")

        return {
            "ok": not errors,
            "agents_count": len(agents),
            "skills_count": len(skills),
            "errors": errors,
            "warnings": warnings,
        }

    @staticmethod
    def _load_json_files(folder: Path) -> list[dict[str, Any]]:
        if not folder.exists():
            return []
        items: list[dict[str, Any]] = []
        for path in sorted(folder.glob("*.json")):
            items.append(json.loads(path.read_text(encoding="utf-8")))
        return items

    @staticmethod
    def _append_duplicate_errors(kind: str, ids: list[str], errors: list[str]) -> None:
        seen: set[str] = set()
        for item_id in ids:
            if item_id in seen:
                errors.append(f"{kind}:{item_id}: duplicate id")
            seen.add(item_id)
