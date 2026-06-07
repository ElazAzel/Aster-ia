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

    async def generate(self, *, model: str, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=1.0)) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "keep_alive": "30m",
                    "options": {"num_predict": 256},
                },
            )
        response.raise_for_status()
        payload = response.json()
        text = str(payload.get("response", ""))
        self.logger.emit("generate.completed", model=model, chars=len(text))
        return text

    async def stream_generate(self, *, model: str, prompt: str) -> AsyncIterator[dict[str, Any]]:
        timeout = httpx.Timeout(120.0, connect=1.0, read=None)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": True,
                    "keep_alive": "30m",
                    "options": {"num_predict": 256},
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

    async def chat(self, *, model: str, messages: list[dict[str, Any]]) -> str:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=1.0)) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "keep_alive": "30m",
                    "options": {"num_predict": 1024},
                },
            )
        response.raise_for_status()
        payload = response.json()
        message = payload.get("message", {})
        text = str(message.get("content", ""))
        self.logger.emit("chat.completed", model=model, chars=len(text))
        return text

    async def stream_chat(self, *, model: str, messages: list[dict[str, Any]]) -> AsyncIterator[dict[str, Any]]:
        timeout = httpx.Timeout(120.0, connect=1.0, read=None)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    "keep_alive": "30m",
                    "options": {"num_predict": 1024},
                },
            ) as response:
                if response.status_code >= 400:
                    raise httpx.HTTPStatusError(
                        f"Ollama chat {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        yield {"message": {"content": line}, "done": False}

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

    async def is_available(self) -> bool:
        """Quick connectivity check for Ollama (2s timeout)."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(2.0, connect=1.0)) as client:
                response = await client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except (httpx.HTTPError, OSError):
            return False

    async def pull_model(self, model: str) -> AsyncIterator[dict[str, Any]]:
        """Stream Ollama model pull progress as dicts with status/completed/total."""
        timeout = httpx.Timeout(600.0, connect=5.0, read=None)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/pull",
                json={"name": model, "stream": True},
            ) as response:
                if response.status_code >= 400:
                    raise httpx.HTTPStatusError(
                        f"Ollama pull {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        yield {"status": line}

    async def ensure_models(self, required: list[str] | tuple[str, ...]) -> dict[str, str]:
        """Check required models and pull missing ones. Returns {model: status}."""
        result: dict[str, str] = {}
        try:
            models = await self.list_models()
            installed = {m.get("name", "").split(":")[0] for m in models}
        except (httpx.HTTPError, OSError):
            self.logger.emit("ensure_models.ollama_unavailable", error="cannot connect")
            return {m: "ollama_unavailable" for m in required}

        for model_name in required:
            base_name = model_name.split(":")[0]
            if base_name in installed or model_name in installed:
                result[model_name] = "already_installed"
                self.logger.emit("ensure_models.present", model=model_name)
                continue
            try:
                self.logger.emit("ensure_models.pulling", model=model_name)
                async for chunk in self.pull_model(model_name):
                    status = chunk.get("status", "")
                    if status == "success":
                        break
                result[model_name] = "pulled"
                self.logger.emit("ensure_models.pulled", model=model_name)
            except (httpx.HTTPError, OSError) as exc:
                result[model_name] = f"pull_failed: {exc}"
                self.logger.emit(
                    "ensure_models.pull_failed", model=model_name, error=str(exc)
                )
        return result
