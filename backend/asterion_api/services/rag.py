from __future__ import annotations

import asyncio
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
        self.watching = False
        self.watcher_task: asyncio.Task | None = None

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

    async def start_watching(self) -> None:
        if self.watching:
            return
        self.watching = True
        self.watch_dir = self.settings.data_dir / "watch"
        self.watch_dir.mkdir(parents=True, exist_ok=True)
        (self.watch_dir / "default").mkdir(exist_ok=True)
        self.watcher_task = asyncio.create_task(self._watch_loop())

    def stop_watching(self) -> None:
        self.watching = False
        if self.watcher_task:
            self.watcher_task.cancel()
            self.watcher_task = None

    def _get_indexed_sources(self) -> set[str]:
        try:
            import lancedb
            if not self.db_path.exists():
                return set()
            db = lancedb.connect(str(self.db_path))
            if self.table_name not in db.table_names():
                return set()
            tbl = db.open_table(self.table_name)
            df = tbl.search().select(["source"]).to_pandas()
            if "source" in df.columns:
                return set(df["source"].dropna().unique())
        except Exception:
            pass
        return set()

    async def _watch_loop(self) -> None:
        from asterion_api.structured_logging import StructuredLogger

        logger = StructuredLogger("rag_watcher", self.privacy_level)
        logger.emit("watcher.started")
        import json
        state_file = self.settings.data_dir / "watcher_state.json"
        
        watcher_state = {}
        if state_file.exists():
            try:
                watcher_state = json.loads(state_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        indexed_sources = self._get_indexed_sources()
        known_files: dict[Path, tuple[float, int]] = {}
        try:
            for room_dir in self.watch_dir.iterdir():
                if room_dir.is_dir():
                    for file_path in room_dir.glob("**/*"):
                        if file_path.is_file():
                            stat = file_path.stat()
                            file_str = str(file_path)
                            if file_str in indexed_sources and file_str in watcher_state:
                                saved = watcher_state[file_str]
                                if saved.get("mtime") == stat.st_mtime and saved.get("size") == stat.st_size:
                                    known_files[file_path] = (stat.st_mtime, stat.st_size)
            logger.emit("watcher.scan_complete", known_count=len(known_files))
        except Exception as e:
            logger.emit("watcher.scan_error", error=str(e))

        while self.watching:
            await asyncio.sleep(5)
            logger.emit("watcher.poll")
            try:
                current_files: dict[Path, tuple[float, int]] = {}
                state_changed = False
                
                for room_dir in self.watch_dir.iterdir():
                    if room_dir.is_dir():
                        room_id = room_dir.name
                        for file_path in room_dir.glob("**/*"):
                            try:
                                if file_path.is_file():
                                    stat = file_path.stat()
                                    current_files[file_path] = (stat.st_mtime, stat.st_size)

                                    last_state = known_files.get(file_path)
                                    if last_state is None or last_state[0] < stat.st_mtime or last_state[1] != stat.st_size:
                                        await asyncio.sleep(0.5)
                                        if file_path.exists():
                                            current_stat = file_path.stat()
                                            if current_stat.st_size == stat.st_size and current_stat.st_mtime == stat.st_mtime:
                                                await self.index_file(file_path, room_id)
                                                
                                                watcher_state[str(file_path)] = {
                                                    "mtime": stat.st_mtime,
                                                    "size": stat.st_size
                                                }
                                                state_changed = True
                                                logger.emit("watcher.indexed", file_path=str(file_path), room_id=room_id)
                            except Exception as fe:
                                logger.emit("watcher.file_error", file_path=str(file_path), error=str(fe))

                deleted_files = set(known_files.keys()) - set(current_files.keys())
                for file_path in deleted_files:
                    try:
                        import lancedb
                        if self.db_path.exists():
                            db = lancedb.connect(str(self.db_path))
                            if self.table_name in db.table_names():
                                tbl = db.open_table(self.table_name)
                                escaped_source = str(file_path).replace("'", "''")
                                tbl.delete(f"source = '{escaped_source}'")
                    except Exception as e:
                        logger.emit("watcher.delete_failed", file_path=str(file_path), error=str(e))
                    
                    file_str = str(file_path)
                    if file_str in watcher_state:
                        del watcher_state[file_str]
                        state_changed = True
                        
                    logger.emit("watcher.deleted", file_path=str(file_path))

                if state_changed:
                    try:
                        state_file.write_text(json.dumps(watcher_state, indent=2), encoding="utf-8")
                    except Exception:
                        pass

                known_files = current_files
            except asyncio.CancelledError:
                logger.emit("watcher.stopped")
                break
            except Exception as exc:
                logger.emit("watcher.failed", error=str(exc))

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

        if file_path.exists():
            try:
                import json
                state_file = self.settings.data_dir / "watcher_state.json"
                watcher_state = {}
                if state_file.exists():
                    try:
                        watcher_state = json.loads(state_file.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                stat = file_path.stat()
                watcher_state[str(file_path)] = {
                    "mtime": stat.st_mtime,
                    "size": stat.st_size
                }
                state_file.write_text(json.dumps(watcher_state, indent=2), encoding="utf-8")
            except Exception:
                pass

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
            tbl = db.open_table(self.table_name)
            sources = {row["source"] for row in rows if "source" in row}
            for source in sources:
                escaped_source = source.replace("'", "''")
                tbl.delete(f"source = '{escaped_source}'")
            if rows:
                tbl.add(rows)
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
