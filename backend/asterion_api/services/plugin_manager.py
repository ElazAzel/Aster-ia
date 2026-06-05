from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from asterion_api.config import Settings
from asterion_api.harness import BaseHarness
from asterion_api.schemas import PluginManifest


class PluginManager(BaseHarness):
    privacy_level = "local"
    TRUST_LEVELS = {"verified", "local-only", "network", "file", "shell", "danger"}

    def __init__(self, settings: Settings) -> None:
        self.plugins_dir = settings.data_dir / "plugins"

    async def execute(self, payload: Mapping[str, Any] | None = None) -> list[PluginManifest]:
        return self.load()

    def get_state(self) -> dict[str, Any]:
        return {"plugins_dir": str(self.plugins_dir)}

    def set_state(self, state: Mapping[str, Any]) -> None:
        if state.get("plugins_dir"):
            self.plugins_dir = Path(str(state["plugins_dir"]))

    def load(self) -> list[PluginManifest]:
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        manifests: list[PluginManifest] = []
        for manifest_path in self.plugins_dir.glob("*/manifest.json"):
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            trust_level = data.get("trust_level", "local-only")
            if trust_level not in self.TRUST_LEVELS:
                trust_level = "danger"
            manifests.append(
                PluginManifest(
                    name=str(data.get("name") or manifest_path.parent.name),
                    trust_level=trust_level,
                    path=str(manifest_path.parent),
                    description=data.get("description"),
                )
            )
        return manifests
