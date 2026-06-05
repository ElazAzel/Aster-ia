from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from asterion_api.config import Settings
from asterion_api.harness import BaseHarness
from asterion_api.schemas import RagChunk
from asterion_api.services.ollama_service import OllamaService


class DocumentIndexer(BaseHarness):
    privacy_level = "local"

    def __init__(self, settings: Settings, ollama: OllamaService) -> None:
        self.settings = settings
        self.ollama = ollama
        self.db_path = settings.data_dir / "lancedb"
        self.table_name = "documents"
        self.embedding_model = "nomic-embed-text"

    async def execute(self, payload: Mapping[str, Any] | None = None) -> Any:
        payload = payload or {}
        action = payload.get("action", "search")
        if action == "index":
            return await self.index_file(Path(str(payload["file_path"])), str(payload["room_id"]))
        if action == "search":
            return await self.hybrid_search(
                query=str(payload["query"]),
                room_id=str(payload.get("room_id", "default")),
                limit=int(payload.get("limit", 8)),
            )
        raise ValueError(f"Unsupported RAG action: {action}")

    def get_state(self) -> dict[str, Any]:
        return {
            "db_path": str(self.db_path),
            "table_name": self.table_name,
            "embedding_model": self.embedding_model,
        }

    def set_state(self, state: Mapping[str, Any]) -> None:
        if state.get("embedding_model"):
            self.embedding_model = str(state["embedding_model"])

    def parse(self, file_path: Path) -> list[str]:
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            from pypdf import PdfReader

            reader = PdfReader(str(file_path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        return self._chunk(text)

    async def index_file(self, file_path: Path, room_id: str) -> dict[str, Any]:
        chunks = self.parse(file_path)
        embeddings = await self.ollama.embed(model=self.embedding_model, input_texts=chunks)
        rows = [
            {
                "id": str(uuid4()),
                "room_id": room_id,
                "content": chunk,
                "source": str(file_path),
                "vector": vector,
            }
            for chunk, vector in zip(chunks, embeddings, strict=False)
        ]
        self._upsert(rows)
        return {"indexed_chunks": len(rows), "source": str(file_path), "room_id": room_id}

    async def hybrid_search(self, *, query: str, room_id: str, limit: int) -> list[RagChunk]:
        query_vector = (await self.ollama.embed(model=self.embedding_model, input_texts=[query]))[0]
        rows = self._all_rows(room_id)
        dense = self._dense_scores(query_vector, rows)
        bm25 = self._bm25_scores(query, rows)
        merged = []
        for row in rows:
            score = 0.7 * dense.get(row["id"], 0.0) + 0.3 * bm25.get(row["id"], 0.0)
            merged.append((row, score))
        merged.sort(key=lambda item: item[1], reverse=True)
        return [
            RagChunk(
                id=row["id"],
                room_id=row["room_id"],
                content=row["content"],
                source=row["source"],
                score=score,
            )
            for row, score in merged[:limit]
        ]

    def _upsert(self, rows: list[dict[str, Any]]) -> None:
        import lancedb

        self.db_path.mkdir(parents=True, exist_ok=True)
        db = lancedb.connect(str(self.db_path))
        if self.table_name in db.table_names():
            db.open_table(self.table_name).add(rows)
        elif rows:
            db.create_table(self.table_name, data=rows)

    def _all_rows(self, room_id: str) -> list[dict[str, Any]]:
        import lancedb

        self.db_path.mkdir(parents=True, exist_ok=True)
        db = lancedb.connect(str(self.db_path))
        if self.table_name not in db.table_names():
            return []
        records = db.open_table(self.table_name).to_pandas().to_dict("records")
        return [row for row in records if row.get("room_id") == room_id]

    @staticmethod
    def _chunk(text: str, size: int = 1200, overlap: int = 160) -> list[str]:
        cleaned = re.sub(r"\s+", " ", text).strip()
        if not cleaned:
            return []
        chunks = []
        start = 0
        while start < len(cleaned):
            chunks.append(cleaned[start : start + size])
            start += size - overlap
        return chunks

    @staticmethod
    def _dense_scores(query_vector: list[float], rows: list[dict[str, Any]]) -> dict[str, float]:
        return {
            row["id"]: DocumentIndexer._cosine(query_vector, list(row.get("vector", [])))
            for row in rows
        }

    @staticmethod
    def _bm25_scores(query: str, rows: list[dict[str, Any]]) -> dict[str, float]:
        query_terms = DocumentIndexer._terms(query)
        docs = [DocumentIndexer._terms(row.get("content", "")) for row in rows]
        avgdl = sum(len(doc) for doc in docs) / max(len(docs), 1)
        scores: dict[str, float] = {}
        for row, doc in zip(rows, docs, strict=False):
            score = 0.0
            for term in query_terms:
                df = sum(1 for candidate in docs if term in candidate)
                if df == 0:
                    continue
                tf = doc.count(term)
                idf = math.log(1 + (len(docs) - df + 0.5) / (df + 0.5))
                denom = tf + 1.5 * (1 - 0.75 + 0.75 * len(doc) / max(avgdl, 1))
                score += idf * (tf * 2.5 / max(denom, 1e-9))
            scores[row["id"]] = score
        max_score = max(scores.values(), default=1.0) or 1.0
        return {key: value / max_score for key, value in scores.items()}

    @staticmethod
    def _terms(text: str) -> list[str]:
        return re.findall(r"[\wа-яА-ЯёЁ]+", text.lower())

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        dot = sum(a * b for a, b in zip(left, right, strict=False))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        return dot / max(left_norm * right_norm, 1e-9)
