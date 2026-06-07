from __future__ import annotations

import asyncio
import re
from typing import Any, Mapping
from urllib.parse import urlparse
from uuid import uuid4

import httpx

from asterion_api.harness import BaseHarness


class ComfyUIService(BaseHarness):
    privacy_level = "local"
    MAX_NODES = 128
    MAX_STRING_LENGTH = 16_000
    LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
    BLOCKED_CLASS_MARKERS = ("download", "http", "url")
    BLOCKED_URI_PREFIXES = ("http://", "https://", "ftp://", "s3://", "file://")
    WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")
    RECIPE_KEYS = {
        "workflow",
        "client_id",
        "checkpoint",
        "width",
        "height",
        "steps",
        "cfg",
        "sampler_name",
        "scheduler",
        "seed",
        "negative_prompt",
        "batch_size",
        "filename_prefix",
    }

    def __init__(self) -> None:
        self.base_url = "http://127.0.0.1:8188"

    async def execute(self, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        return await self.generate(str(payload["prompt"]), dict(payload.get("recipe", {})))

    def get_state(self) -> dict[str, Any]:
        return {
            "base_url": self.base_url,
            "privacy_level": self.privacy_level,
            "recipe_limits": {"max_nodes": self.MAX_NODES, "max_string_length": self.MAX_STRING_LENGTH},
        }

    def set_state(self, state: Mapping[str, Any]) -> None:
        if state.get("base_url"):
            self.base_url = self._normalize_base_url(str(state["base_url"]))

    def validate_recipe(self, recipe: Mapping[str, Any] | None, prompt: str = "") -> dict[str, Any]:
        recipe = recipe or {}
        errors: list[str] = []
        warnings: list[str] = []

        if not isinstance(recipe, Mapping):
            errors.append("recipe must be a JSON object")
            return self._validation_response(errors, warnings, nodes_count=0)

        unknown_keys = sorted(set(recipe.keys()) - self.RECIPE_KEYS)
        if unknown_keys:
            warnings.append(f"ignored top-level recipe keys: {', '.join(unknown_keys)}")

        client_id = recipe.get("client_id")
        if client_id is not None and (not isinstance(client_id, str) or len(client_id) > 128):
            errors.append("client_id must be a string with at most 128 characters")

        workflow = recipe.get("workflow") or self._workflow(prompt or "{{prompt}}", recipe)
        if not isinstance(workflow, Mapping):
            errors.append("workflow must be a JSON object keyed by ComfyUI node id")
            return self._validation_response(errors, warnings, nodes_count=0)
        if not workflow:
            errors.append("workflow must contain at least one node")
        if len(workflow) > self.MAX_NODES:
            errors.append(f"workflow has too many nodes: {len(workflow)} > {self.MAX_NODES}")

        node_ids = {str(node_id) for node_id in workflow.keys()}
        for node_id, raw_node in workflow.items():
            node_path = f"workflow.{node_id}"
            if not isinstance(node_id, str) or not node_id.strip():
                errors.append(f"{node_path}: node id must be a non-empty string")
            if not isinstance(raw_node, Mapping):
                errors.append(f"{node_path}: node must be an object")
                continue

            class_type = raw_node.get("class_type")
            if not isinstance(class_type, str) or not class_type.strip():
                errors.append(f"{node_path}: class_type is required")
            elif any(marker in class_type.lower() for marker in self.BLOCKED_CLASS_MARKERS):
                errors.append(f"{node_path}: class_type '{class_type}' can route data outside local ComfyUI")

            inputs = raw_node.get("inputs")
            if not isinstance(inputs, Mapping):
                errors.append(f"{node_path}: inputs must be an object")
                continue
            if class_type == "SaveImage":
                filename_prefix = inputs.get("filename_prefix")
                if isinstance(filename_prefix, str) and (
                    "/" in filename_prefix or "\\" in filename_prefix
                ):
                    errors.append(
                        f"{node_path}.inputs.filename_prefix: subdirectories are not allowed"
                    )
            self._validate_value(inputs, node_ids, f"{node_path}.inputs", errors)

        if not any(
            isinstance(node, Mapping) and node.get("class_type") == "SaveImage"
            for node in workflow.values()
        ):
            warnings.append("workflow has no SaveImage node; ComfyUI may finish without image output")

        return self._validation_response(errors, warnings, nodes_count=len(workflow))

    async def generate(self, prompt: str, recipe: dict[str, Any]) -> dict[str, Any]:
        self.base_url = self._normalize_base_url(self.base_url)
        validation = self.validate_recipe(recipe, prompt)
        if not validation["ok"]:
            raise ValueError("; ".join(validation["errors"]))

        workflow = recipe.get("workflow") or self._workflow(prompt, recipe)
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

    @classmethod
    def _workflow(cls, prompt: str, recipe: Mapping[str, Any] | None = None) -> dict[str, Any]:
        recipe = recipe or {}
        checkpoint = cls._recipe_string(recipe, "checkpoint", "model.safetensors")
        negative_prompt = cls._recipe_string(recipe, "negative_prompt", "")
        filename_prefix = cls._recipe_string(recipe, "filename_prefix", "asterion")
        return {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": checkpoint},
            },
            "2": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": prompt, "clip": ["1", 1]},
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": negative_prompt, "clip": ["1", 1]},
            },
            "4": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": cls._recipe_int(recipe, "width", 1024),
                    "height": cls._recipe_int(recipe, "height", 1024),
                    "batch_size": cls._recipe_int(recipe, "batch_size", 1),
                },
            },
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": cls._recipe_int(recipe, "seed", 1),
                    "steps": cls._recipe_int(recipe, "steps", 20),
                    "cfg": cls._recipe_float(recipe, "cfg", 7.0),
                    "sampler_name": cls._recipe_string(recipe, "sampler_name", "euler"),
                    "scheduler": cls._recipe_string(recipe, "scheduler", "normal"),
                    "denoise": 1.0,
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["4", 0],
                },
            },
            "6": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
            },
            "7": {
                "class_type": "SaveImage",
                "inputs": {"images": ["6", 0], "filename_prefix": filename_prefix},
            },
        }

    @staticmethod
    def _recipe_int(recipe: Mapping[str, Any], key: str, default: int) -> int:
        value = recipe.get(key)
        return value if isinstance(value, int) and not isinstance(value, bool) else default

    @staticmethod
    def _recipe_float(recipe: Mapping[str, Any], key: str, default: float) -> float:
        value = recipe.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        return default

    @staticmethod
    def _recipe_string(recipe: Mapping[str, Any], key: str, default: str) -> str:
        value = recipe.get(key)
        return value if isinstance(value, str) and value.strip() else default

    @classmethod
    def _validation_response(
        cls,
        errors: list[str],
        warnings: list[str],
        nodes_count: int,
    ) -> dict[str, Any]:
        return {
            "ok": not errors,
            "errors": errors,
            "warnings": warnings,
            "nodes_count": nodes_count,
            "privacy_level": cls.privacy_level,
        }

    @classmethod
    def _normalize_base_url(cls, value: str) -> str:
        parsed = urlparse(value.rstrip("/"))
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("ComfyUI base_url must use http or https")
        if parsed.hostname not in cls.LOOPBACK_HOSTS:
            raise ValueError("ComfyUI base_url must point to localhost or 127.0.0.1")
        return value.rstrip("/")

    @classmethod
    def _validate_value(
        cls,
        value: Any,
        node_ids: set[str],
        path: str,
        errors: list[str],
    ) -> None:
        if isinstance(value, str):
            lowered = value.lower()
            if len(value) > cls.MAX_STRING_LENGTH:
                errors.append(f"{path}: string value exceeds {cls.MAX_STRING_LENGTH} characters")
            if lowered.startswith(cls.BLOCKED_URI_PREFIXES):
                errors.append(f"{path}: external URI values are not allowed in local recipes")
            if "../" in value or "..\\" in value or value.startswith(("/", "\\")):
                errors.append(f"{path}: path traversal or absolute paths are not allowed in recipes")
            if re_match := cls.WINDOWS_ABSOLUTE_PATH.match(value):
                errors.append(
                    f"{path}: absolute Windows paths are not allowed in recipes ({re_match.group(0)})"
                )
            return
        if isinstance(value, (int, float, bool)) or value is None:
            return
        if isinstance(value, list):
            if len(value) == 2 and isinstance(value[0], str) and isinstance(value[1], int):
                if value[0] not in node_ids:
                    errors.append(f"{path}: references missing node '{value[0]}'")
                if value[1] < 0:
                    errors.append(f"{path}: output index must be non-negative")
                return
            for index, item in enumerate(value):
                cls._validate_value(item, node_ids, f"{path}[{index}]", errors)
            return
        if isinstance(value, Mapping):
            for key, item in value.items():
                cls._validate_value(item, node_ids, f"{path}.{key}", errors)
            return
        errors.append(f"{path}: unsupported JSON value type {type(value).__name__}")
