from __future__ import annotations

from typing import Any, Mapping

from asterion_api.harness import BaseHarness
from asterion_api.schemas import HardwareProfile, ModelSelection


class ModelRouter(BaseHarness):
    privacy_level = "local"

    def __init__(self) -> None:
        self.local_catalog = [
            {"model": "llama3.2", "required_vram_gb": 6.0, "reason": "general local chat"},
            {"model": "mistral", "required_vram_gb": 8.0, "reason": "reasoning-heavy work"},
            {"model": "qwen2.5:0.5b", "required_vram_gb": 2.0, "reason": "low-VRAM fallback"},
        ]
        self.api_fallback = "gpt-4o-mini"

    async def execute(self, payload: Mapping[str, Any] | None = None) -> ModelSelection:
        payload = payload or {}
        profile = HardwareProfile(**payload.get("hw_profile", {}))
        return self.select(str(payload.get("task_description", "")), profile)

    def get_state(self) -> dict[str, Any]:
        return {"local_catalog": self.local_catalog, "api_fallback": self.api_fallback}

    def set_state(self, state: Mapping[str, Any]) -> None:
        if isinstance(state.get("local_catalog"), list):
            self.local_catalog = list(state["local_catalog"])
        if state.get("api_fallback"):
            self.api_fallback = str(state["api_fallback"])

    def select(self, task_description: str, hw_profile: HardwareProfile) -> ModelSelection:
        viable = [
            item for item in self.local_catalog if hw_profile.vram_gb >= item["required_vram_gb"]
        ]
        if viable:
            chosen = sorted(viable, key=lambda item: item["required_vram_gb"], reverse=True)[0]
            return ModelSelection(
                model=str(chosen["model"]),
                mode="local",
                reason=(
                    f"VRAM {hw_profile.vram_gb:g} GB >= "
                    f"{chosen['required_vram_gb']:g} GB; selected {chosen['reason']}."
                ),
            )
        return ModelSelection(
            model=self.api_fallback,
            mode="api",
            reason=(
                f"VRAM {hw_profile.vram_gb:g} GB is below local model requirements; "
                f"API fallback selected for {task_description[:120]}."
            ),
        )
