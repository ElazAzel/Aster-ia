from __future__ import annotations

import json
import statistics
import time
from typing import Any, Mapping

import httpx

from asterion_api.harness import BaseHarness
from asterion_api.structured_logging import StructuredLogger


VRAM_ESTIMATES: dict[str, float] = {
    "phi3:mini":          1.8,
    "phi3":               2.4,
    "llama3.2:1b":        1.3,
    "llama3.2:3b":        2.0,
    "llama3.2":           4.7,
    "llama3.1:8b":        4.9,
    "mistral:7b":         4.1,
    "mistral":            4.1,
    "gemma2:2b":          1.6,
    "gemma2:9b":          5.5,
    "qwen2.5:0.5b":       0.4,
    "qwen2.5:1.5b":       1.0,
    "qwen2.5:3b":         1.9,
    "qwen2.5:7b":         4.4,
    "qwen2.5:14b":        8.9,
    "qwen2.5:32b":        19.0,
    "codellama:7b":       3.8,
    "deepseek-coder-v2":  8.9,
    "nomic-embed-text":   0.3,
    "llava:13b":          8.0,
}

_CACHE_TTL_SECONDS = 3600


class BenchmarkService(BaseHarness):
    privacy_level = "local"

    def __init__(self, ollama_base_url: str = "http://127.0.0.1:11434") -> None:
        self.ollama_base_url = ollama_base_url.rstrip("/")
        self._cache: dict[str, dict[str, Any]] = {}
        self.logger = StructuredLogger("benchmark", self.privacy_level)

    async def execute(self, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        models = payload.get("models") or await self._list_installed_models()
        prompt = str(payload.get("prompt", "Explain recursion in one paragraph."))
        max_tokens = int(payload.get("max_tokens", 128))
        runs = int(payload.get("runs_per_model", 3))
        results = await self.run(models=models, prompt=prompt,
                                  max_tokens=max_tokens, runs_per_model=runs)
        return {"results": [r for r in results], "privacy_level": self.privacy_level}

    def get_state(self) -> dict[str, Any]:
        return {"cache_entries": len(self._cache),
                "cached_models": list(self._cache.keys())}

    def set_state(self, state: Mapping[str, Any]) -> None:
        if "clear_cache" in state:
            self._cache.clear()

    async def run(self, *, models: list[str], prompt: str,
                   max_tokens: int = 128, runs_per_model: int = 3) -> list[dict[str, Any]]:
        results = []
        for model in models:
            result = await self._benchmark_model(
                model=model, prompt=prompt,
                max_tokens=max_tokens, runs=runs_per_model)
            results.append(result)
        return results

    def get_cached(self, model: str) -> dict[str, Any] | None:
        entry = self._cache.get(model)
        if not entry:
            return None
        age = time.time() - entry["ts"]
        if age > _CACHE_TTL_SECONDS:
            del self._cache[model]
            return None
        return entry["result"]

    def clear_cache(self) -> None:
        self._cache.clear()

    async def _list_installed_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                resp = await client.get(f"{self.ollama_base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    async def _benchmark_model(self, *, model: str, prompt: str,
                                 max_tokens: int, runs: int) -> dict[str, Any]:
        cached = self.get_cached(model)
        if cached:
            return {**cached, "cached_at": self._cache[model]["ts"]}

        tps_samples: list[float] = []
        ttft_samples: list[float] = []
        total_samples: list[float] = []
        last_error: str | None = None

        for _ in range(runs):
            try:
                sample = await self._single_run(model=model, prompt=prompt,
                                                  max_tokens=max_tokens)
                tps_samples.append(sample["tps"])
                ttft_samples.append(sample["ttft_ms"])
                total_samples.append(sample["total_ms"])
            except Exception as exc:
                last_error = str(exc)

        vram_est = self._estimate_vram(model)

        if not tps_samples:
            result = {
                "model": model, "runs": 0,
                "avg_tokens_per_second": 0.0, "avg_time_to_first_token_ms": 0.0,
                "avg_total_time_ms": 0.0, "min_tps": 0.0, "max_tps": 0.0,
                "stddev_tps": 0.0, "vram_estimate_gb": vram_est,
                "privacy_level": self.privacy_level, "error": last_error,
            }
        else:
            result = {
                "model": model, "runs": len(tps_samples),
                "avg_tokens_per_second": round(statistics.mean(tps_samples), 2),
                "avg_time_to_first_token_ms": round(statistics.mean(ttft_samples), 1),
                "avg_total_time_ms": round(statistics.mean(total_samples), 1),
                "min_tps": round(min(tps_samples), 2),
                "max_tps": round(max(tps_samples), 2),
                "stddev_tps": round(statistics.stdev(tps_samples) if len(tps_samples) > 1 else 0.0, 2),
                "vram_estimate_gb": vram_est,
                "privacy_level": self.privacy_level,
                "error": None,
            }

        self._cache[model] = {"result": result, "ts": time.time()}
        return result

    async def _single_run(self, *, model: str, prompt: str, max_tokens: int) -> dict[str, float]:
        payload = {
            "model": model, "prompt": prompt,
            "options": {"num_predict": max_tokens},
            "stream": True,
        }
        t0 = time.perf_counter()
        ttft: float | None = None
        token_count = 0

        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
            async with client.stream(
                "POST", f"{self.ollama_base_url}/api/generate", json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if chunk.get("response"):
                        if ttft is None:
                            ttft = (time.perf_counter() - t0) * 1000
                        token_count += 1
                    if chunk.get("done"):
                        break

        total_ms = (time.perf_counter() - t0) * 1000
        tps = (token_count / (total_ms / 1000)) if total_ms > 0 and token_count > 0 else 0.0
        return {"tps": tps, "ttft_ms": ttft or total_ms, "total_ms": total_ms,
                "tokens": token_count}

    @staticmethod
    def _estimate_vram(model: str) -> float:
        for key, vram in VRAM_ESTIMATES.items():
            if model.lower().startswith(key.lower()):
                return vram
        return 4.0
