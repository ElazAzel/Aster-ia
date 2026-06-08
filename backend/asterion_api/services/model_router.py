from __future__ import annotations

from typing import Any, Mapping

from asterion_api.harness import BaseHarness
from asterion_api.schemas import HardwareProfile, ModelSelection


class ModelRouter(BaseHarness):
    privacy_level = "local"

    def __init__(self) -> None:
        self.local_catalog = [
            {"model": "llama3.2:1b",       "required_vram_gb": 0.0, "ram_gb": 2.0,
             "tags": ["chat", "fast"],       "reason": "ultra-light CPU-only chat"},
            {"model": "qwen2.5:0.5b",       "required_vram_gb": 0.0, "ram_gb": 1.5,
             "tags": ["chat", "fast"],       "reason": "smallest viable model, CPU"},
            {"model": "phi3:mini",          "required_vram_gb": 0.0, "ram_gb": 3.0,
             "tags": ["chat", "reasoning"], "reason": "Microsoft phi-3, excellent CPU perf"},
            {"model": "gemma2:2b",          "required_vram_gb": 0.0, "ram_gb": 3.0,
             "tags": ["chat"],              "reason": "Google Gemma2 2B, balanced"},
            {"model": "llama3.2:3b",        "required_vram_gb": 3.0, "ram_gb": 4.0,
             "tags": ["chat"],              "reason": "Meta 3B, good small GPU model"},
            {"model": "qwen2.5:3b",         "required_vram_gb": 3.0, "ram_gb": 4.0,
             "tags": ["chat", "multilingual"], "reason": "Qwen 3B, strong Russian/Chinese"},
            {"model": "mistral:7b",         "required_vram_gb": 5.0, "ram_gb": 8.0,
             "tags": ["chat", "reasoning"], "reason": "Mistral 7B instruction tuned"},
            {"model": "codellama:7b",        "required_vram_gb": 5.0, "ram_gb": 8.0,
             "tags": ["code"],              "reason": "Meta CodeLlama 7B, strong code"},
            {"model": "qwen2.5:7b",         "required_vram_gb": 5.5, "ram_gb": 8.0,
             "tags": ["chat", "multilingual", "reasoning"], "reason": "Qwen2.5 7B, top Russian"},
            {"model": "llama3.2",           "required_vram_gb": 6.0, "ram_gb": 8.0,
             "tags": ["chat", "general"],   "reason": "Meta Llama 3.2 8B, best general purpose"},
            {"model": "llama3.1:8b",        "required_vram_gb": 6.0, "ram_gb": 8.0,
             "tags": ["chat", "reasoning"], "reason": "Meta Llama 3.1 8B instruction"},
            {"model": "gemma2:9b",           "required_vram_gb": 6.5, "ram_gb": 10.0,
             "tags": ["chat", "reasoning"], "reason": "Google Gemma2 9B, excellent reasoning"},
            {"model": "deepseek-coder-v2",  "required_vram_gb": 10.0, "ram_gb": 16.0,
             "tags": ["code"],              "reason": "DeepSeek Coder V2, GPT-4 level code"},
            {"model": "qwen2.5:14b",        "required_vram_gb": 10.0, "ram_gb": 16.0,
             "tags": ["chat", "multilingual", "reasoning"], "reason": "Qwen2.5 14B, top quality"},
            {"model": "qwen2.5:32b",        "required_vram_gb": 20.0, "ram_gb": 32.0,
             "tags": ["chat", "reasoning", "code"], "reason": "Qwen2.5 32B, near-GPT4 quality"},
            {"model": "llava:13b",          "required_vram_gb": 8.0, "ram_gb": 12.0,
             "tags": ["vision"],            "reason": "LLaVA 1.6 13B, image understanding"},
            {"model": "nomic-embed-text",   "required_vram_gb": 0.0, "ram_gb": 1.0,
             "tags": ["embed"],             "reason": "Nomic embed for RAG, required"},
        ]
        self.api_fallback = "gpt-4o-mini"
        self._task_routing: dict[str, list[str]] = {
            "code":       ["code", "reasoning", "general"],
            "russian":    ["multilingual", "chat"],
            "research":   ["reasoning", "chat"],
            "vision":     ["vision"],
            "embed":      ["embed"],
            "quick":      ["fast", "chat"],
            "general":    ["general", "chat", "reasoning"],
        }

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
        task_lower = task_description.lower()
        preferred_tags: list[str] = []
        for keyword, tags in self._task_routing.items():
            if keyword in task_lower:
                preferred_tags.extend(tags)

        user_ram = hw_profile.ram_gb if hw_profile.ram_gb is not None else float("inf")

        viable = [
            item for item in self.local_catalog
            if hw_profile.vram_gb >= item["required_vram_gb"]
            and user_ram >= item.get("ram_gb", 0)
        ]

        if not viable:
            return ModelSelection(
                model=self.api_fallback, mode="api",
                reason=f"No local model fits VRAM={hw_profile.vram_gb:.1f}GB RAM={hw_profile.ram_gb or 0:.1f}GB; API fallback.",
            )

        def score(item: dict) -> float:
            tag_match = sum(1 for t in item.get("tags", []) if t in preferred_tags)
            vram_headroom = hw_profile.vram_gb - item["required_vram_gb"]
            return tag_match * 10 + min(vram_headroom, 4.0)

        best = max(viable, key=score)
        return ModelSelection(
            model=str(best["model"]), mode="local",
            reason=f"VRAM {hw_profile.vram_gb:g}GB OK; task-matched {best.get('reason', '')}.",
        )
