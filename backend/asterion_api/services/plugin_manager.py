from __future__ import annotations

import json
import threading
import time
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
        self._watcher_active: bool = False
        self._watcher_thread: threading.Thread | None = None

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

    def start_watcher(self, interval: float = 5.0) -> None:
        self._watcher_active = True
        self._last_plugins: list[PluginManifest] = []
        def _watch() -> None:
            while self._watcher_active:
                current = self.load()
                current_dump = [p.model_dump() for p in current]
                last_dump = [p.model_dump() for p in self._last_plugins]
                if current_dump != last_dump:
                    self._last_plugins = current
                time.sleep(interval)
        self._watcher_thread = threading.Thread(target=_watch, daemon=True)
        self._watcher_thread.start()

    def stop_watcher(self) -> None:
        self._watcher_active = False

    def get_plugin_names(self) -> list[str]:
        return [p.name for p in self.load()]
