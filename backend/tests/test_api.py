"""HTTP integration tests for all major Asterion AI API routers."""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("ASTERION_ALLOW_PLAINTEXT_SQLITE_FOR_DEV", "1")

with patch("asterion_api.services.ollama_service.OllamaService.list_models", new_callable=AsyncMock) as _:
    from asterion_api.main import app


@pytest.fixture()
def client(tmp_path):
    os.environ["ASTERION_DATA_DIR"] = str(tmp_path)
    from asterion_api.config import get_settings
    get_settings.cache_clear()
    import asterion_api.dependencies as dep
    for attr in ["_store_singleton", "_document_indexer_singleton",
                 "_ollama_service_singleton", "_voice_service_singleton",
                 "_benchmark_service_singleton"]:
        fn = getattr(dep, attr, None)
        if fn and hasattr(fn, "cache_clear"):
            fn.cache_clear()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_health_returns_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("ok", "degraded")
    assert "database" in body


def test_health_has_schema_version(client):
    r = client.get("/api/health")
    assert "schema_version" in r.json()


@patch("asterion_api.services.ollama_service.OllamaService.list_models",
       new_callable=AsyncMock,
       return_value=[{"name": "llama3.2", "size": 4700000000, "modified_at": "2026-06-06T00:00:00Z"}])
def test_list_models(mock_list, client):
    r = client.get("/api/models")
    assert r.status_code == 200
    assert "models" in r.json()


def test_model_select_local(client):
    r = client.post("/api/models/select", json={"task_description": "code", "hw_profile": {"vram_gb": 8.0, "ram_gb": 16.0}})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] in ("local", "api")
    assert "model" in body


def test_model_select_api_fallback_no_vram(client):
    r = client.post("/api/models/select", json={"task_description": "complex task", "hw_profile": {"vram_gb": 0.0, "ram_gb": 0.0}})
    assert r.status_code == 200
    assert r.json()["mode"] == "api"


def test_room_create_and_list(client):
    r = client.post("/api/rooms", json={"name": "Test Room", "color": "#ff0000"})
    assert r.status_code == 200
    room = r.json()
    assert room["name"] == "Test Room"
    rooms = client.get("/api/rooms").json()
    assert any(room["id"] == rm["id"] for rm in rooms)


def test_room_update(client):
    created = client.post("/api/rooms", json={"name": "Old Name"}).json()
    r = client.patch(f"/api/rooms/{created['id']}", json={"name": "New Name"})
    assert r.status_code == 200
    assert r.json()["name"] == "New Name"


def test_memory_create_list_delete(client):
    r = client.post("/api/memory", json={"room_id": "default", "content": "Test fact", "source": "test"})
    assert r.status_code == 200
    mem_id = r.json()["id"]
    memories = client.get("/api/memory/default").json()
    assert any(m["id"] == mem_id for m in memories)
    deleted = client.delete(f"/api/memory/{mem_id}").json()
    assert deleted["deleted"] is True


def test_privacy_analyze_local(client):
    r = client.post("/api/privacy/analyze", json={"model_type": "local", "files_attached": False,
                                                   "memory_enabled": False, "web_access": False})
    assert r.status_code == 200
    assert r.json()["level"] == "green"


def test_privacy_analyze_external(client):
    r = client.post("/api/privacy/analyze", json={"model_type": "api", "files_attached": True,
                                                   "memory_enabled": True, "web_access": True})
    assert r.status_code == 200
    assert r.json()["level"] == "red"


def test_rag_list_documents_empty(client):
    r = client.get("/api/rag/documents")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_rag_folder_scope_create_and_list(client, tmp_path):
    r = client.post("/api/rag/folder-scopes",
                    json={"room_id": "default", "path": str(tmp_path), "label": "Test"})
    assert r.status_code == 200
    assert r.json()["path"] == str(tmp_path)
    listed = client.get("/api/rag/folder-scopes").json()
    assert len(listed) >= 1


def test_rag_upload_pdf(client, tmp_path):
    txt = tmp_path / "test.txt"
    txt.write_text("This is a test document for RAG indexing. It contains useful information.")
    with txt.open("rb") as f:
        with patch("asterion_api.services.rag.DocumentIndexer.index_file",
                   new_callable=AsyncMock,
                   return_value={"indexed_chunks": 1, "source": "test.txt", "room_id": "default"}):
            r = client.post("/api/rag/index/upload",
                            files={"file": ("test.txt", f, "text/plain")},
                            data={"room_id": "default"})
    assert r.status_code == 200
    assert r.json()["indexed_chunks"] >= 1


def test_artifact_create_and_get(client):
    r = client.post("/api/artifacts", json={
        "room_id": "default", "kind": "chat", "title": "Test Artifact",
        "blocks": [{"type": "text", "content": "Hello world"}], "source": "test"
    })
    assert r.status_code == 200
    artifact_id = r.json()["id"]
    fetched = client.get(f"/api/artifacts/{artifact_id}").json()
    assert fetched["title"] == "Test Artifact"


def test_artifact_list_by_room(client):
    client.post("/api/artifacts", json={
        "room_id": "room-a", "kind": "chat", "title": "Room A Art",
        "blocks": [], "source": "test"
    })
    listed = client.get("/api/artifacts?room_id=room-a").json()
    assert any(a["room_id"] == "room-a" for a in listed)


def test_agent_catalog_returns_agents(client):
    r = client.get("/api/agents/catalog")
    assert r.status_code == 200
    catalog = r.json()
    assert "agents" in catalog and len(catalog["agents"]) > 0


def test_agent_catalog_validate(client):
    r = client.get("/api/agents/catalog/validate")
    assert r.status_code == 200
    body = r.json()
    assert "ok" in body


def test_benchmark_bad_runs_rejected(client):
    r = client.post("/api/benchmark/run", json={"prompt": "test", "runs_per_model": 99, "max_tokens": 128})
    assert r.status_code in (400, 422)


def test_benchmark_bad_tokens_rejected(client):
    r = client.post("/api/benchmark/run", json={"prompt": "test", "runs_per_model": 2, "max_tokens": 9999})
    assert r.status_code in (400, 422)


def test_benchmark_cache_empty(client):
    r = client.get("/api/benchmark/cache")
    assert r.status_code == 200
    assert r.json()["cache_entries"] == 0


def test_benchmark_cache_clear(client):
    r = client.delete("/api/benchmark/cache")
    assert r.status_code == 200
    assert r.json()["cleared"] is True


def test_voice_status(client):
    r = client.get("/api/voice/status")
    assert r.status_code == 200
    body = r.json()
    assert "ok" in body and body["privacy_level"] == "local"


def test_voice_text_structure(client):
    r = client.post("/api/voice/transcribe/text",
                    data={"text": "We need to call the team. How does this work?", "mode": "notes"})
    assert r.status_code == 200
    body = r.json()
    assert "action_items" in body and "markdown" in body


def test_export_json(client):
    r = client.post("/api/export", json={"scope": "memories", "format": "json"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")


def test_export_markdown(client):
    r = client.post("/api/export", json={"scope": "artifacts", "format": "markdown"})
    assert r.status_code == 200
    assert "markdown" in r.headers["content-type"]


def test_export_csv(client):
    r = client.post("/api/export", json={"scope": "audit_logs", "format": "csv"})
    assert r.status_code == 200
    assert "csv" in r.headers["content-type"]


def test_audit_log_create_and_list(client):
    r = client.post("/api/audit/logs", json={"action": "test", "resource": "pytest"})
    assert r.status_code == 200
    logs = client.get("/api/audit/logs").json()
    assert any(log["action"] == "test" for log in logs)


def test_analytics_research_stats(client):
    r = client.get("/api/analytics/research/stats")
    assert r.status_code == 200
    body = r.json()
    assert "total_research_queries" in body


def test_analytics_agent_stats(client):
    r = client.get("/api/analytics/agent-stats")
    assert r.status_code == 200
    body = r.json()
    assert "total_runs" in body and "privacy_distribution" in body
