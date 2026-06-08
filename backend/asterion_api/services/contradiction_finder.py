from __future__ import annotations

import math
import re
from typing import Any, Mapping

from asterion_api.harness import BaseHarness
from asterion_api.schemas import ContradictionMatch
from asterion_api.services.ollama_service import OllamaService
from asterion_api.structured_logging import StructuredLogger


NEGATORS_EN = {"not", "no", "never", "neither", "nor", "hardly", "barely", "scarcely", "without"}
NEGATORS_RU = {"не", "ни", "никогда", "без", "едва", "чуть", "никак"}

POSITIVE_EN = {
    "good", "works", "safe", "valid", "true", "supports", "correct", "effective",
    "stable", "reliable", "secure", "fast", "efficient", "optimal", "approved",
}
POSITIVE_RU = {
    "хорош", "работает", "безопасн", "правильн", "точн", "поддерживает",
    "стабильн", "надежн", "эффективн", "оптимальн", "утвержд",
}

NEGATIVE_EN = {
    "bad", "fails", "unsafe", "invalid", "false", "breaks", "wrong", "broken",
    "unstable", "unreliable", "insecure", "slow", "inefficient", "denied", "rejected",
}
NEGATIVE_RU = {
    "плох", "ломает", "опасн", "неправильн", "некорректн", "неуспешн",
    "нестабильн", "ненадежн", "нес可靠", "медленн", "отклон",
}

ALL_POSITIVE = POSITIVE_EN | POSITIVE_RU
ALL_NEGATIVE = NEGATIVE_EN | NEGATIVE_RU


class ContradictionFinder(BaseHarness):
    privacy_level = "local"

    def __init__(self, ollama: OllamaService) -> None:
        self.ollama = ollama
        self.embedding_model = "nomic-embed-text"
        self.logger = StructuredLogger("contradiction", self.privacy_level)

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
        if len(claims) < 2:
            return []
        embeddings = await self.ollama.embed(model=self.embedding_model, input_texts=claims)
        matches: list[ContradictionMatch] = []
        for i, left in enumerate(claims):
            for j in range(i + 1, len(claims)):
                similarity = self._cosine(embeddings[i], embeddings[j])
                if similarity < threshold:
                    continue
                left_sentiment = self._sentiment(left)
                right_sentiment = self._sentiment(claims[j])
                if (
                    left_sentiment != "neutral"
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
        self.logger.emit("contradictions.found", count=len(matches), claims=len(claims))
        return matches

    def _sentiment(self, text: str) -> str:
        tokens = re.findall(r"[\wа-яА-ЯёЁ]+", text.lower())
        negated = False
        pos_score = 0
        neg_score = 0

        for token in tokens:
            if token in NEGATORS_EN or token in NEGATORS_RU:
                negated = True
                continue

            if token in ALL_POSITIVE:
                if negated:
                    neg_score += 1
                else:
                    pos_score += 1
                negated = False
            elif token in ALL_NEGATIVE:
                if negated:
                    pos_score += 1
                else:
                    neg_score += 1
                negated = False
            else:
                if len(token) > 3:
                    for stem in ALL_POSITIVE:
                        if token.startswith(stem):
                            if negated:
                                neg_score += 1
                            else:
                                pos_score += 1
                            negated = False
                            break
                    else:
                        for stem in ALL_NEGATIVE:
                            if token.startswith(stem):
                                if negated:
                                    pos_score += 1
                                else:
                                    neg_score += 1
                                negated = False
                                break

        if pos_score > neg_score:
            return "positive"
        if neg_score > pos_score:
            return "negative"
        return "neutral"

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        dot = sum(a * b for a, b in zip(left, right, strict=False))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        return dot / max(left_norm * right_norm, 1e-9)
