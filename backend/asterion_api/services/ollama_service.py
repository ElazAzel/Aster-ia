from __future__ import annotations

import json
from typing import Any, AsyncIterator, Mapping

import httpx

from asterion_api.config import Settings
from asterion_api.harness import BaseHarness
from asterion_api.structured_logging import StructuredLogger


class OllamaService(BaseHarness):
    privacy_level = "local"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = settings.ollama_base_url.rstrip("/")
        self._state: dict[str, Any] = {"base_url": self.base_url}
        self.logger = StructuredLogger("ollama", self.privacy_level)
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=5.0))
        return self._client

    async def aclose(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def is_available(self) -> bool:
        try:
            client = self._get_client()
            resp = await client.get(f"{self.base_url}/api/tags")
            return resp.status_code == 200
        except Exception:
            return False

    async def execute(self, payload: Mapping[str, Any] | None = None) -> Any:
        payload = payload or {}
        action = payload.get("action", "list_models")
        if action == "list_models":
            return await self.list_models()
        if action == "generate":
            return await self.generate(
                model=str(payload.get("model") or self.settings.default_model),
                prompt=str(payload.get("prompt") or ""),
            )
        raise ValueError(f"Unsupported Ollama harness action: {action}")

    def get_state(self) -> dict[str, Any]:
        return dict(self._state)

    def set_state(self, state: Mapping[str, Any]) -> None:
        self._state.update(dict(state))

    async def list_models(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=1.0)) as client:
            response = await client.get(f"{self.base_url}/api/tags")
        response.raise_for_status()
        payload = response.json()
        self.logger.emit("models.listed", count=len(payload.get("models", [])))
        return list(payload.get("models", []))

    async def ensure_models(self, required: list[str]) -> dict[str, str]:
        try:
            existing = {m["name"] for m in await self.list_models()}
        except Exception:
            return {model: "ollama_unavailable" for model in required}
        results: dict[str, str] = {}
        for model in required:
            if model in existing:
                results[model] = "already_installed"
            else:
                try:
                    async for _status in self.pull_model(model):
                        pass
                    results[model] = "pulled"
                except Exception as exc:
                    results[model] = f"error: {exc}"
        return results

    async def pull_model(self, model: str) -> AsyncIterator[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=5.0)) as client:
            async with client.stream(
                "POST", f"{self.base_url}/api/pull",
                json={"name": model},
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.strip():
                        yield json.loads(line)

    async def generate(self, *, model: str, prompt: str, num_predict: int | None = None) -> str:
        timeout = httpx.Timeout(120.0, connect=1.0)
        tokens = num_predict or self.settings.max_tokens
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "keep_alive": "30m",
                    "options": {"num_predict": tokens},
                },
            )
        response.raise_for_status()
        payload = response.json()
        text = str(payload.get("response", ""))
        self.logger.emit("generate.completed", model=model, chars=len(text))
        return text

    async def stream_generate(self, *, model: str, prompt: str, num_predict: int | None = None) -> AsyncIterator[dict[str, Any]]:
        timeout = httpx.Timeout(120.0, connect=1.0, read=None)
        tokens = num_predict or self.settings.max_tokens
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": True,
                    "keep_alive": "30m",
                    "options": {"num_predict": tokens},
                },
            ) as response:
                if response.status_code >= 400:
                    raise httpx.HTTPStatusError(
                        f"Ollama generate {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        yield {"response": line, "done": False}

    async def embed(self, *, model: str, input_texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=1.0)) as client:
            response = await client.post(
                f"{self.base_url}/api/embed",
                json={"model": model, "input": input_texts, "keep_alive": "30m"},
            )
        response.raise_for_status()
        payload = response.json()
        embeddings = payload.get("embeddings")
        if not isinstance(embeddings, list):
            raise ValueError("Ollama embed response did not include embeddings")
        return embeddings

    async def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        num_predict: int | None = None,
    ) -> str:
        timeout = httpx.Timeout(120.0, connect=1.0)
        tokens = num_predict or self.settings.max_tokens
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "keep_alive": "30m",
                    "options": {"num_predict": tokens},
                },
            )
            response.raise_for_status()
            payload = response.json()
        text = str(payload.get("message", {}).get("content", ""))
        self.logger.emit("chat.completed", model=model, chars=len(text))
        return text

    async def stream_chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        num_predict: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        timeout = httpx.Timeout(120.0, connect=1.0, read=None)
        tokens = num_predict or self.settings.max_tokens
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    "keep_alive": "30m",
                    "options": {"num_predict": tokens},
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        yield {"message": {"content": line}, "done": False}
