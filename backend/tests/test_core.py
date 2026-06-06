from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from asterion_api.schemas import ChatRequest, PrivacyItem, PrivacyReport, RagChunk
from asterion_api.services.privacy_analyzer import PrivacyAnalyzer
from asterion_api.services.rag import DocumentIndexer
from asterion_api.services.agent_registry import AgentRegistry


class TestPrivacyAnalyzer:
    def test_local_model_returns_green(self) -> None:
        pa = PrivacyAnalyzer()
        report = pa.analyze(model_type="local", files_attached=False, memory_enabled=False, web_access=False)
        assert report.level == "green"
        assert len(report.items) == 1
        assert report.items[0].risk == "green"

    def test_api_model_returns_red(self) -> None:
        pa = PrivacyAnalyzer()
        report = pa.analyze(model_type="api", files_attached=False, memory_enabled=False, web_access=False)
        assert report.level == "red"
        assert any(item.risk == "red" for item in report.items)

    def test_memory_enabled_adds_yellow_item(self) -> None:
        pa = PrivacyAnalyzer()
        report = pa.analyze(model_type="local", files_attached=False, memory_enabled=True, web_access=False)
        assert report.level == "yellow"
        risks = [item.risk for item in report.items]
        assert "yellow" in risks

    def test_all_red_when_api_with_web_access(self) -> None:
        pa = PrivacyAnalyzer()
        report = pa.analyze(model_type="api", files_attached=True, memory_enabled=True, web_access=True)
        assert report.level == "red"


class TestRagChunking:
    def test_chunk_splits_text(self) -> None:
        text = "hello world " * 500
        chunks = DocumentIndexer._chunk(text, size=200, overlap=20)
        assert len(chunks) > 1
        assert all(len(c) <= 200 for c in chunks)

    def test_chunk_empty_text(self) -> None:
        assert DocumentIndexer._chunk("") == []

    def test_terms_extracts_words(self) -> None:
        result = DocumentIndexer._terms("Hello World! Привет мир")
        assert result == ["hello", "world", "привет", "мир"]


class TestSchemas:
    def test_chat_request_valid(self) -> None:
        req = ChatRequest(message="hello")
        assert req.message == "hello"
        assert req.room_id == "default"

    def test_chat_request_message_too_short(self) -> None:
        with pytest.raises(ValueError):
            ChatRequest(message="")

    def test_rag_chunk_roundtrip(self) -> None:
        chunk = RagChunk(id="abc", room_id="r1", content="test", source="/x.txt", score=0.9)
        data = chunk.model_dump(mode="json")
        restored = RagChunk(**data)
        assert restored.id == "abc"
        assert restored.score == 0.9

    def test_privacy_report_serialization(self) -> None:
        report = PrivacyReport(
            level="yellow",
            items=[PrivacyItem(what="memory", destination="local_db", risk="yellow")],
        )
        d = report.model_dump(mode="json")
        assert d["level"] == "yellow"


class TestAgentRegistry:
    def test_catalog_loads_without_error(self) -> None:
        root = Path(__file__).resolve().parents[2]
        registry = AgentRegistry(project_root=root)
        catalog = registry.catalog()
        assert len(catalog.agents) > 0
        assert len(catalog.skills) > 0

    def test_agent_manifest_has_required_fields(self) -> None:
        root = Path(__file__).resolve().parents[2]
        registry = AgentRegistry(project_root=root)
        for agent in registry.list_agents():
            assert agent.id
            assert agent.name
            assert agent.privacy_level in ("local", "hybrid", "external")
