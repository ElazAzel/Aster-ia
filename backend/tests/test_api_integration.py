from __future__ import annotations

import os
import json
import sqlite3
import pytest
import httpx
from httpx import AsyncClient, ASGITransport

from asterion_api.config import get_settings
from asterion_api.main import app
from asterion_api.dependencies import get_store
from asterion_api.services.ollama_service import OllamaService
from asterion_api.services.comfyui_service import ComfyUIService
from asterion_api.storage.migrations import current_version, run_migrations, migration_001


@pytest.fixture
async def test_app(tmp_path):
    os.environ["ASTERION_DATA_DIR"] = str(tmp_path)
    os.environ["ASTERION_ALLOW_PLAINTEXT_SQLITE_FOR_DEV"] = "1"
    
    get_settings.cache_clear()
    from asterion_api import dependencies
    dependencies.get_store.cache_clear()
    dependencies.get_ollama_service.cache_clear()
    dependencies.get_chat_service.cache_clear()
    dependencies.get_privacy_analyzer.cache_clear()
    dependencies.get_model_router.cache_clear()
    dependencies.get_memory_ledger.cache_clear()
    dependencies.get_document_indexer.cache_clear()
    dependencies.get_supervisor_agent.cache_clear()
    dependencies.get_contradiction_finder.cache_clear()
    dependencies.get_task_simulator.cache_clear()
    dependencies.get_agent_sandbox.cache_clear()
    dependencies.get_agent_registry.cache_clear()
    dependencies.get_agent_executor.cache_clear()
    dependencies.get_comfyui_service.cache_clear()
    dependencies.get_workflow_runner.cache_clear()
    dependencies.get_plugin_manager.cache_clear()
    
    
    # Ensure database schema is created/migrated
    store = get_store()
    await store.ensure_schema()
    
    yield app

    # Reset cached Ollama client to avoid closed event loop errors in subsequent tests
    from asterion_api.dependencies import get_ollama_service
    ollama = get_ollama_service()
    if ollama._client:
        try:
            await ollama._client.aclose()
        except Exception:
            pass
        ollama._client = None


@pytest.mark.asyncio
async def test_health_endpoint(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        res = await ac.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert "status" in data
        assert "database" in data
        assert "schema_version" in data


@pytest.mark.asyncio
async def test_models_endpoints(test_app, monkeypatch):
    async def mock_list_models(self):
        return [{"name": "llama3.2:latest"}]
    monkeypatch.setattr(OllamaService, "list_models", mock_list_models)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        res = await ac.get("/api/models")
        assert res.status_code == 200
        data = res.json()
        assert len(data["models"]) == 1
        assert data["models"][0]["name"] == "llama3.2:latest"


@pytest.mark.asyncio
async def test_rooms_crud(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        # Create
        payload = {
            "name": "Integration Room",
            "color": "#00ff00",
            "allowed_models": ["llama3.2"],
            "memory_policy": "session",
            "retention_days": 15,
            "system_prompt": "Helpful AI"
        }
        res = await ac.post("/api/rooms", json=payload)
        assert res.status_code == 200
        room = res.json()
        room_id = room["id"]
        assert room["name"] == "Integration Room"

        # List
        res = await ac.get("/api/rooms")
        assert res.status_code == 200
        rooms = res.json()
        assert any(r["id"] == room_id for r in rooms)

        # Get
        res = await ac.get(f"/api/rooms/{room_id}")
        assert res.status_code == 200
        assert res.json()["name"] == "Integration Room"

        # Update
        update_payload = {"name": "Updated Room", "color": "#0000ff"}
        res = await ac.patch(f"/api/rooms/{room_id}", json=update_payload)
        assert res.status_code == 200
        assert res.json()["name"] == "Updated Room"
        assert res.json()["color"] == "#0000ff"

        # Delete
        res = await ac.delete(f"/api/rooms/{room_id}")
        assert res.status_code == 200
        assert res.json() == {"deleted": True}


@pytest.mark.asyncio
async def test_chat_history_and_deletion(test_app, monkeypatch):
    async def mock_chat(self, *, model, messages):
        return "Mock Response"
    monkeypatch.setattr(OllamaService, "chat", mock_chat)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        # Create conversation by posting a chat message
        chat_payload = {
            "message": "Hello AI",
            "room_id": "default",
            "model": "llama3.2"
        }
        res = await ac.post("/api/chat", json=chat_payload)
        assert res.status_code == 200
        chat_data = res.json()
        conv_id = chat_data["conversation_id"]

        # List conversations
        res = await ac.get("/api/chat/conversations?room_id=default")
        assert res.status_code == 200
        convs = res.json()
        assert any(c["id"] == conv_id for c in convs)

        # Update title
        res = await ac.patch(f"/api/chat/conversations/{conv_id}", json={"title": "New Title"})
        assert res.status_code == 200
        assert res.json()["title"] == "New Title"

        # List messages
        res = await ac.get(f"/api/chat/conversations/{conv_id}/messages")
        assert res.status_code == 200
        msgs = res.json()
        assert len(msgs) >= 2 # user message + assistant response

        # Delete conversation
        res = await ac.delete(f"/api/chat/conversations/{conv_id}")
        assert res.status_code == 200
        assert res.json() == {"deleted": True}


@pytest.mark.asyncio
async def test_memory_crud(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        # Create memory
        payload = {
            "room_id": "default",
            "content": "Remember this secure code",
            "source": "integration_test"
        }
        res = await ac.post("/api/memory", json=payload)
        assert res.status_code == 200
        mem = res.json()
        mem_id = mem["id"]

        # List memories
        res = await ac.get("/api/memory/default")
        assert res.status_code == 200
        mems = res.json()
        assert any(m["id"] == mem_id for m in mems)

        # Delete memory
        res = await ac.delete(f"/api/memory/{mem_id}")
        assert res.status_code == 200
        assert res.json() == {"deleted": True}


@pytest.mark.asyncio
async def test_rag_crud(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        # Search empty RAG
        search_payload = {"query": "secure documentation"}
        res = await ac.post("/api/rag/search?room_id=default", json=search_payload)
        assert res.status_code == 200
        assert isinstance(res.json(), list)

        # List documents
        res = await ac.get("/api/rag/documents?room_id=default")
        assert res.status_code == 200
        assert isinstance(res.json(), list)


@pytest.mark.asyncio
async def test_agents_endpoints(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        # Catalog
        res = await ac.get("/api/agents/catalog")
        assert res.status_code == 200
        catalog = res.json()
        assert "agents" in catalog
        assert "skills" in catalog

        # Validate Catalog
        res = await ac.get("/api/agents/catalog/validate")
        assert res.status_code == 200
        assert res.json()["ok"] is True

        # Simulate
        res = await ac.post("/api/agents/simulate", json={"task": "Perform a security check"})
        assert res.status_code == 200
        plan = res.json()
        assert "steps" in plan

        # Sandbox run-code
        sandbox_payload = {
            "code": "print('Hello Sandbox')",
            "permissions": {"allowed_folders": [], "network": False, "shell": False}
        }
        res = await ac.post("/api/agents/run-code", json=sandbox_payload)
        assert res.status_code == 200
        assert "stdout" in res.json()

        # Create Agent Run
        run_payload = {
            "agent_id": "chat-orchestrator",
            "room_id": "default",
            "task": "Test Run",
            "plan": plan,
            "permissions": {"allowed_folders": [], "network": False, "shell": False}
        }
        res = await ac.post("/api/agents/runs", json=run_payload)
        assert res.status_code == 200
        run = res.json()
        run_id = run["id"]

        # Get Agent Run
        res = await ac.get(f"/api/agents/runs/{run_id}")
        assert res.status_code == 200
        assert res.json()["id"] == run_id

        # Update Agent Run
        res = await ac.patch(f"/api/agents/runs/{run_id}", json={"status": "paused"})
        assert res.status_code == 200
        assert res.json()["status"] == "paused"

        # List logs
        res = await ac.get(f"/api/agents/runs/{run_id}/logs")
        assert res.status_code == 200
        assert isinstance(res.json(), list)


@pytest.mark.asyncio
async def test_workflows_router(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        # Run workflow with only completed steps (no human_approval step so it returns status: completed immediately)
        run_payload = {
            "workflow": {
                "name": "Integration Workflow",
                "steps": [
                    {"name": "Step 1", "type": "action"},
                    {"name": "Step 2", "type": "action"}
                ]
            }
        }
        res = await ac.post("/api/workflows/run", json=run_payload)
        assert res.status_code == 200
        run_data = res.json()
        assert run_data["status"] == "completed"

        # Seed a dummy paused run directly in WorkflowRunner to test confirm endpoint
        from asterion_api.dependencies import get_workflow_runner
        import asyncio
        runner = get_workflow_runner()
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        runner.paused["test_run_id"] = future

        confirm_payload = {
            "run_id": "test_run_id",
            "approved": True,
            "payload": {}
        }
        res = await ac.post("/api/workflows/confirm", json=confirm_payload)
        assert res.status_code == 200
        assert res.json() == {"confirmed": True}
        assert future.done()


@pytest.mark.asyncio
async def test_plugins_router(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        res = await ac.get("/api/plugins")
        assert res.status_code == 200
        assert isinstance(res.json(), list)


@pytest.mark.asyncio
async def test_images_router(test_app, monkeypatch):
    async def mock_generate(self, prompt, recipe):
        return {"image": "mock_base64_data"}
    monkeypatch.setattr(ComfyUIService, "generate", mock_generate)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        res = await ac.post("/api/images/generate", json={"prompt": "beautiful gradient"})
        assert res.status_code == 200
        assert res.json()["image"] == "mock_base64_data"


@pytest.mark.asyncio
async def test_health_degraded_integration(test_app, monkeypatch):
    async def mock_is_available(self):
        return False
    monkeypatch.setattr(OllamaService, "is_available", mock_is_available)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        res = await ac.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "degraded"
        assert data["ollama"]["available"] is False


@pytest.mark.asyncio
async def test_ensure_models_fallback(monkeypatch):
    async def mock_list_models_fail(self):
        raise httpx.ConnectError("Connection refused")
    monkeypatch.setattr(OllamaService, "list_models", mock_list_models_fail)

    service = OllamaService(get_settings())
    res = await service.ensure_models(["llama3.2"])
    assert res["llama3.2"] == "ollama_unavailable"


@pytest.mark.asyncio
async def test_ensure_models_pull(monkeypatch):
    async def mock_list_models_empty(self):
        return []
    async def mock_pull_model(self, model):
        yield {"status": "downloading"}
        yield {"status": "success"}
    monkeypatch.setattr(OllamaService, "list_models", mock_list_models_empty)
    monkeypatch.setattr(OllamaService, "pull_model", mock_pull_model)

    service = OllamaService(get_settings())
    res = await service.ensure_models(["llama3.2"])
    assert res["llama3.2"] == "pulled"


def test_db_migration_v0_to_latest(tmp_path):
    db_file = tmp_path / "test_migration.db"
    conn = sqlite3.connect(str(db_file))
    
    assert current_version(conn) == 0
    
    # Run v1 migration manually
    migration_001(conn)
    
    # Set version 1 as applied
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, description TEXT, applied_at TEXT)"
    )
    conn.execute(
        "INSERT INTO schema_migrations (version, description, applied_at) VALUES (1, 'Initial', '2026-06-06')"
    )
    # Insert v1 data to check for preservation
    conn.execute(
        "INSERT INTO rooms (id, name, color, allowed_models, memory_policy, retention_days, created_at, updated_at) "
        "VALUES ('room_mig', 'Mig Room', '#000000', '[]', 'session', 10, '2026', '2026')"
    )
    conn.commit()
    
    assert current_version(conn) == 1
    
    # Run remaining migrations (v3)
    new_version = run_migrations(conn)
    assert new_version == 3
    
    # Verify columns were added successfully and data was preserved
    cursor = conn.execute("SELECT * FROM rooms WHERE id='room_mig'")
    row = cursor.fetchone()
    # id, name, color, allowed_models, memory_policy, retention_days, created_at, updated_at, system_prompt
    assert row[1] == "Mig Room"
    assert row[8] == "" # system_prompt default
    
    conn.close()


@pytest.mark.asyncio
async def test_exceptions_and_global_handler():
    from fastapi import Request
    from fastapi.datastructures import URL
    from unittest.mock import MagicMock
    from asterion_api.exceptions import AsterionAPIError, global_exception_handler
    
    mock_request = MagicMock(spec=Request)
    mock_request.url = URL("http://test/some-path")
    
    # Test AsterionAPIError
    exc = AsterionAPIError("Custom error", code="custom_code", status_code=400)
    response = await global_exception_handler(mock_request, exc)
    assert response.status_code == 400
    assert json.loads(response.body) == {"error": "Custom error", "code": "custom_code"}
    
    # Test generic Exception
    generic_exc = ValueError("Oops")
    response_generic = await global_exception_handler(mock_request, generic_exc)
    assert response_generic.status_code == 500
    assert json.loads(response_generic.body) == {
        "error": "An unexpected internal server error occurred.",
        "code": "internal_error"
    }


def test_main_runner(monkeypatch):
    import argparse
    from asterion_api import __main__
    
    # Mock parse_args
    class MockArgs:
        host = "127.0.0.1"
        port = 8000
        
    def mock_parse_args(self):
        return MockArgs()
        
    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", mock_parse_args)
    
    # Mock uvicorn.run
    run_called = []
    def mock_run(app_path, host, port, log_level, reload):
        run_called.append((app_path, host, port))
        
    import uvicorn
    monkeypatch.setattr(uvicorn, "run", mock_run)
    
    __main__.main()
    assert len(run_called) == 1
    assert run_called[0] == ("asterion_api.main:app", "127.0.0.1", 8000)


@pytest.mark.asyncio
async def test_chat_stream_endpoints(test_app, monkeypatch):
    async def mock_stream_chat(self, *, model, messages):
        yield {"message": {"content": "Mock streaming word"}, "done": False}
        yield {"message": {"content": "."}, "done": True}
    monkeypatch.setattr(OllamaService, "stream_chat", mock_stream_chat)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        # Test GET /api/chat/stream
        res = await ac.get("/api/chat/stream?message=hello&room_id=default")
        assert res.status_code == 200
        assert "data:" in res.text

        # Test POST /api/chat/stream
        res = await ac.post("/api/chat/stream", json={"message": "hello", "room_id": "default", "model": "llama3.2"})
        assert res.status_code == 200
        assert "data:" in res.text


@pytest.mark.asyncio
async def test_rag_index_endpoints(test_app, monkeypatch):
    async def mock_index_file(self, file_path, room_id):
        return {"source": "test.txt", "indexed_chunks": 5}
    from asterion_api.services.rag import DocumentIndexer
    monkeypatch.setattr(DocumentIndexer, "index_file", mock_index_file)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        # Test POST /api/rag/index
        index_payload = {"file_path": "test.txt", "room_id": "default"}
        res = await ac.post("/api/rag/index", json=index_payload)
        assert res.status_code == 200
        assert res.json()["document"]["indexed_chunks"] == 5

        # Test POST /api/rag/index/upload
        files = {"file": ("test.txt", b"some mock content", "text/plain")}
        res = await ac.post("/api/rag/index/upload", files=files, data={"room_id": "default"})
        assert res.status_code == 200
        assert res.json()["source"] == "test.txt"


@pytest.mark.asyncio
async def test_research_endpoints(test_app, monkeypatch):
    async def mock_research(self, query, max_subtasks, web_access):
        from asterion_api.schemas import DeepResearchResponse, PrivacyReport
        return DeepResearchResponse(
            query=query,
            subtasks=["sub1"],
            results=[],
            privacy=PrivacyReport(level="green", items=[])
        )
    from asterion_api.services.deep_research import SupervisorAgent
    monkeypatch.setattr(SupervisorAgent, "research", mock_research)

    async def mock_find(self, claims, threshold):
        return []
    from asterion_api.services.contradiction_finder import ContradictionFinder
    monkeypatch.setattr(ContradictionFinder, "find", mock_find)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        # Test POST /api/research/deep
        res = await ac.post("/api/research/deep", json={"query": "privacy check", "max_subtasks": 3})
        assert res.status_code == 200
        assert res.json()["query"] == "privacy check"

        # Test POST /api/research/contradictions
        res = await ac.post("/api/research/contradictions", json={"claims": ["a", "b"], "threshold": 0.8})
        assert res.status_code == 200
        assert isinstance(res.json(), list)
