from __future__ import annotations

import math
import re
from typing import Any, Mapping

from asterion_api.harness import BaseHarness
from asterion_api.schemas import ContradictionMatch
from asterion_api.services.ollama_service import OllamaService


class ContradictionFinder(BaseHarness):
    privacy_level = "local"

    def __init__(self, ollama: OllamaService) -> None:
        self.ollama = ollama
        self.embedding_model = "nomic-embed-text"
        self.positive = {"good", "works", "safe", "valid", "true", "supports", "лучше", "работает"}
        self.negative = {"bad", "fails", "unsafe", "invalid", "false", "breaks", "хуже", "не"}

    async def execute(self, payload: Mapping[str, Any] | None = None) -> list[ContradictionMatch]:
        payload = payload or {}
        return await self.find(
            claims=[str(item) for item in payload.get("claims", [])],
            threshold=float(payload.get("threshold", 0.85)),
        )

    def get_state(self) -> dict[str, Any]:
        return {"embedding_model": self.embedding_model}

    def set_state(self, state: Mapping[str, Any]) -> None:
        if state.get("embedding_model"):
            self.embedding_model = str(state["embedding_model"])

    async def find(self, *, claims: list[str], threshold: float) -> list[ContradictionMatch]:
        embeddings = await self.ollama.embed(model=self.embedding_model, input_texts=claims)
        matches: list[ContradictionMatch] = []
        for i, left in enumerate(claims):
            for j in range(i + 1, len(claims)):
                similarity = self._cosine(embeddings[i], embeddings[j])
                left_sentiment = self._sentiment(left)
                right_sentiment = self._sentiment(claims[j])
                if (
                    similarity >= threshold
                    and left_sentiment != "neutral"
                    and right_sentiment != "neutral"
                    and left_sentiment != right_sentiment
                ):
                    matches.append(
                        ContradictionMatch(
                            left=left,
                            right=claims[j],
                            similarity=similarity,
                            sentiment_left=left_sentiment,
                            sentiment_right=right_sentiment,
                        )
                    )
        return matches

    def _sentiment(self, text: str) -> str:
        terms = set(re.findall(r"[\wа-яА-ЯёЁ]+", text.lower()))
        if terms & self.negative:
            return "negative"
        if terms & self.positive:
            return "positive"
        return "neutral"

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        dot = sum(a * b for a, b in zip(left, right, strict=False))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        return dot / max(left_norm * right_norm, 1e-9)
