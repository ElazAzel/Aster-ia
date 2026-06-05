from __future__ import annotations

import asyncio
from typing import Any, Mapping
from uuid import uuid4

import httpx

from asterion_api.harness import BaseHarness


class ComfyUIService(BaseHarness):
    privacy_level = "local"

    def __init__(self) -> None:
        self.base_url = "http://127.0.0.1:8188"

    async def execute(self, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        return await self.generate(str(payload["prompt"]), dict(payload.get("recipe", {})))

    def get_state(self) -> dict[str, Any]:
        return {"base_url": self.base_url}

    def set_state(self, state: Mapping[str, Any]) -> None:
        if state.get("base_url"):
            self.base_url = str(state["base_url"]).rstrip("/")

    async def generate(self, prompt: str, recipe: dict[str, Any]) -> dict[str, Any]:
        workflow = recipe.get("workflow") or self._workflow(prompt)
        client_id = recipe.get("client_id") or str(uuid4())
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=1.0)) as client:
            response = await client.post(
                f"{self.base_url}/prompt",
                json={"prompt": workflow, "client_id": client_id},
            )
            response.raise_for_status()
            prompt_id = response.json()["prompt_id"]
            for _ in range(120):
                history = await client.get(f"{self.base_url}/history/{prompt_id}")
                history.raise_for_status()
                payload = history.json()
                if payload.get(prompt_id):
                    return {"prompt_id": prompt_id, "history": payload[prompt_id]}
                await asyncio.sleep(1)
        raise TimeoutError("ComfyUI generation did not finish in time")

    @staticmethod
    def _workflow(prompt: str) -> dict[str, Any]:
        return {
            "1": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": prompt, "clip": ["4", 1]},
            }
        }
