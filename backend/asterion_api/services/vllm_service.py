from __future__ import annotations

import json
import time
from typing import Any, AsyncIterator, Mapping

import httpx

from asterion_api.harness import BaseHarness
from asterion_api.structured_logging import StructuredLogger


class VllmService(BaseHarness):
    privacy_level = "local"
    DEFAULT_BASE_URL = "http://127.0.0.1:8100/v1"
    _CACHE_TTL = 30.0

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self._available: bool | None = None
        self._models: list[str] = []
        self._last_check: float = 0.0
        self.logger = StructuredLogger("vllm", self.privacy_level)

    async def execute(self, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        model = str(payload.get("model", ""))
        messages = payload.get("messages")
        if isinstance(messages, list) and messages:
            return await self.chat_generate(model=model, messages=messages,
                                            max_tokens=int(payload.get("max_tokens", 256)))
        prompt = str(payload.get("prompt", ""))
        max_tokens = int(payload.get("max_tokens", 256))
        return await self.generate(model=model, prompt=prompt, max_tokens=max_tokens)

    def get_state(self) -> dict[str, Any]:
        return {"available": self._available, "base_url": self.base_url,
                "models": self._models, "privacy_level": self.privacy_level}

    def set_state(self, state: Mapping[str, Any]) -> None:
        if "base_url" in state:
            self.base_url = str(state["base_url"]).rstrip("/")
            self._available = None
            self._last_check = 0.0

    async def is_available(self) -> bool:
        now = time.monotonic()
        if self._available is not None and now - self._last_check < self._CACHE_TTL:
            return self._available
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(3.0)) as client:
                resp = await client.get(f"{self.base_url}/models")
                if resp.status_code == 200:
                    data = resp.json()
                    self._models = [m["id"] for m in data.get("data", [])]
                    self._available = True
                    self._last_check = now
                    return True
        except Exception:
            pass
        self._available = False
        self._models = []
        self._last_check = now
        return False

    async def list_models(self) -> list[str]:
        if not await self.is_available():
            return []
        return self._models

    async def has_model(self, model_name: str) -> bool:
        return model_name in await self.list_models()

    async def generate(self, *, model: str, prompt: str,
                        max_tokens: int = 512, temperature: float = 0.7) -> dict[str, Any]:
        if not await self.is_available():
            return {"error": "vLLM server not available", "base_url": self.base_url,
                    "hint": "Start: python -m vllm.entrypoints.openai.api_server --model <name> --port 8100"}

        payload = {
            "model": model, "prompt": prompt,
            "max_tokens": max_tokens, "temperature": temperature, "stream": False,
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
            resp = await client.post(f"{self.base_url}/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [{}])
            return {
                "text": choices[0].get("text", "") if choices else "",
                "model": model, "privacy_level": self.privacy_level,
                "usage": data.get("usage", {}),
            }

    async def stream_generate(self, *, model: str, prompt: str,
                               max_tokens: int = 512,
                               temperature: float = 0.7) -> AsyncIterator[str]:
        if not await self.is_available():
            yield "[vLLM not available]"
            return

        payload = {
            "model": model, "prompt": prompt,
            "max_tokens": max_tokens, "temperature": temperature, "stream": True,
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
            async with client.stream(
                "POST", f"{self.base_url}/completions", json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        text = chunk["choices"][0].get("text", "")
                        if text:
                            yield text
                    except Exception:
                        continue

    async def chat_generate(self, *, model: str, messages: list[dict[str, str]],
                             max_tokens: int = 512, temperature: float = 0.7) -> dict[str, Any]:
        if not await self.is_available():
            return {"error": "vLLM server not available", "base_url": self.base_url,
                    "hint": "Start: python -m vllm.entrypoints.openai.api_server --model <name> --port 8100"}
        payload = {
            "model": model, "messages": messages,
            "max_tokens": max_tokens, "temperature": temperature, "stream": False,
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [{}])
            return {
                "text": choices[0].get("message", {}).get("content", "") if choices else "",
                "model": model, "privacy_level": self.privacy_level,
                "usage": data.get("usage", {}),
            }

    async def chat_stream(self, *, model: str, messages: list[dict[str, str]],
                           max_tokens: int = 512,
                           temperature: float = 0.7) -> AsyncIterator[str]:
        if not await self.is_available():
            yield "[vLLM not available]"
            return
        payload = {
            "model": model, "messages": messages,
            "max_tokens": max_tokens, "temperature": temperature, "stream": True,
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
            async with client.stream(
                "POST", f"{self.base_url}/chat/completions", json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except Exception:
                        continue
