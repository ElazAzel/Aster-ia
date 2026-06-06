"""Smoke-tests для критических сервисов Asterion AI."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Storage ──────────────────────────────────────────────────────────────────

def test_encrypted_store_imports():
    from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore
    from asterion_api.harness import BaseHarness
    assert issubclass(EncryptedSQLiteStore, BaseHarness)


@pytest.mark.asyncio
async def test_store_schema_creates_tables(tmp_path):
    import os
    os.environ["ASTERION_DATA_DIR"] = str(tmp_path)
    os.environ["ASTERION_ALLOW_PLAINTEXT_SQLITE_FOR_DEV"] = "1"
    from asterion_api.config import get_settings
    get_settings.cache_clear()
    from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore
    store = EncryptedSQLiteStore(get_settings())
    await store.ensure_schema()
    health = await store.health_check()
    assert health["ok"] is True


# ── Privacy Analyzer ─────────────────────────────────────────────────────────

def test_privacy_local_is_green():
    from asterion_api.services.privacy_analyzer import PrivacyAnalyzer
    report = PrivacyAnalyzer().analyze(
        model_type="local",
        files_attached=False,
        memory_enabled=False,
        web_access=False,
    )
    assert report.level == "green"


def test_privacy_api_is_red():
    from asterion_api.services.privacy_analyzer import PrivacyAnalyzer
    report = PrivacyAnalyzer().analyze(
        model_type="api",
        files_attached=True,
        memory_enabled=True,
        web_access=True,
    )
    assert report.level == "red"
    assert any(item.risk == "red" for item in report.items)


# ── Model Router ──────────────────────────────────────────────────────────────

def test_model_router_local_high_vram():
    from asterion_api.services.model_router import ModelRouter
    from asterion_api.schemas import HardwareProfile
    router = ModelRouter()
    result = router.select("local coding", HardwareProfile(vram_gb=10.0))
    assert result.mode == "local"
    assert result.model != router.api_fallback


def test_model_router_api_fallback_no_vram():
    from asterion_api.services.model_router import ModelRouter
    from asterion_api.schemas import HardwareProfile
    router = ModelRouter()
    result = router.select("complex task", HardwareProfile(vram_gb=0.5))
    assert result.mode == "api"
    assert result.model == router.api_fallback


# ── RAG chunking ─────────────────────────────────────────────────────────────

def test_rag_chunk_splits_correctly():
    from asterion_api.services.rag import DocumentIndexer
    text = "A" * 3000
    chunks = DocumentIndexer._chunk(text, size=1200, overlap=160)
    assert len(chunks) >= 2
    assert all(len(c) <= 1200 for c in chunks)


def test_rag_bm25_empty_query():
    from asterion_api.services.rag import DocumentIndexer
    rows = [{"id": "1", "content": "hello world"}, {"id": "2", "content": "foo bar"}]
    scores = DocumentIndexer._bm25_scores("", rows)
    assert set(scores.keys()) == {"1", "2"}


# ── BaseHarness compliance ────────────────────────────────────────────────────

def test_all_services_implement_harness():
    from asterion_api.harness import BaseHarness
    from asterion_api.services.ollama_service import OllamaService
    from asterion_api.services.privacy_analyzer import PrivacyAnalyzer
    from asterion_api.services.rag import DocumentIndexer
    from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore
    for cls in [OllamaService, PrivacyAnalyzer, EncryptedSQLiteStore]:
        assert issubclass(cls, BaseHarness), f"{cls.__name__} не реализует BaseHarness"
