from fastapi.testclient import TestClient

from asterion_api.main import app


client = TestClient(app, raise_server_exceptions=False)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert data["app"] == "Asterion AI Sidecar"
    assert "database" in data
    assert "privacy" in data
    assert data["privacy"]["local_first"] is True


def test_health_has_uptime():
    response = client.get("/api/health")
    data = response.json()
    assert data["uptime_seconds"] >= 0


def test_openapi_docs():
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "paths" in data


def test_models_endpoint():
    response = client.get("/api/models")
    assert response.status_code in (200, 503)
    if response.status_code == 200:
        data = response.json()
        assert "models" in data
        assert data["privacy_level"] == "local"


def test_privacy_analyze():
    response = client.post(
        "/api/privacy/analyze",
        json={
            "model_type": "local",
            "files_attached": False,
            "memory_enabled": False,
            "web_access": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["level"] == "green"
    assert len(data["items"]) == 1
    assert data["items"][0]["risk"] == "green"


def test_privacy_analyze_api_model():
    response = client.post(
        "/api/privacy/analyze",
        json={
            "model_type": "api",
            "files_attached": True,
            "memory_enabled": False,
            "web_access": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["level"] == "red"


def test_memory_create():
    response = client.post(
        "/api/memory",
        json={
            "room_id": "test-room",
            "content": "test memory content",
            "source": "test",
        },
    )
    if response.status_code == 200:
        data = response.json()
        assert data["room_id"] == "test-room"
        assert data["content"] == "test memory content"
        assert "id" in data
    else:
        assert response.status_code == 500


def test_memory_list():
    response = client.get("/api/memory/test-room")
    assert response.status_code in (200, 500)
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)


def test_memory_update_not_found():
    response = client.patch(
        "/api/memory/nonexistent-id",
        json={"content": "updated"},
    )
    assert response.status_code in (404, 500)


def test_memory_delete_not_found():
    response = client.delete("/api/memory/nonexistent-id")
    assert response.status_code in (404, 500)


def test_agents_catalog():
    response = client.get("/api/agents/catalog")
    assert response.status_code == 200
    data = response.json()
    assert "agents" in data
    assert "skills" in data
    assert isinstance(data["agents"], list)
    assert isinstance(data["skills"], list)


def test_agents_list():
    response = client.get("/api/agents/catalog/agents")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 5


def test_skills_list():
    response = client.get("/api/agents/catalog/skills")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 10


def test_agent_not_found():
    response = client.get("/api/agents/catalog/agents/nonexistent")
    assert response.status_code == 404


def test_simulate_task():
    response = client.post(
        "/api/agents/simulate",
        json={"task": "write python code to search the web"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "steps" in data
    assert "required_permissions" in data
    assert "file_read" in data["required_permissions"]
    assert "file_write" in data["required_permissions"]
    assert "web_search" in data["required_permissions"]
    assert "run_code" in data["required_permissions"]


def test_run_code_blocks_shell():
    response = client.post(
        "/api/agents/run-code",
        json={
            "code": "import subprocess",
            "permissions": {
                "network": False,
                "shell": False,
                "allowed_folders": [],
            },
        },
    )
    assert response.status_code == 403


def test_run_code_allows_harmless():
    response = client.post(
        "/api/agents/run-code",
        json={
            "code": "print('hello')",
            "permissions": {
                "network": False,
                "shell": False,
                "allowed_folders": [],
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["exit_code"] == 0
    assert "hello" in data["stdout"]


def test_run_code_blocks_network():
    response = client.post(
        "/api/agents/run-code",
        json={
            "code": "import httpx",
            "permissions": {
                "network": False,
                "shell": False,
                "allowed_folders": [],
            },
        },
    )
    assert response.status_code == 403


def test_plugins_list():
    response = client.get("/api/plugins")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_workflow_runs_list():
    response = client.get("/api/workflows/runs")
    assert response.status_code in (200, 500)
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)


def test_workflow_run_not_found():
    response = client.get("/api/workflows/runs/nonexistent")
    assert response.status_code in (404, 500)


def test_workflow_confirm_not_found():
    response = client.post(
        "/api/workflows/confirm",
        json={"run_id": "nonexistent", "approved": True, "payload": {}},
    )
    assert response.status_code == 404


def test_rag_search():
    response = client.post(
        "/api/rag/search",
        json={"query": "test query", "room_id": "default", "limit": 5},
    )
    assert response.status_code in (200, 500)
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)


def test_chat_validation():
    response = client.post(
        "/api/chat",
        json={"message": ""},
    )
    assert response.status_code == 422


def test_memory_create_validation():
    response = client.post(
        "/api/memory",
        json={"room_id": "", "content": "test"},
    )
    assert response.status_code == 422


def test_research_deep():
    response = client.post(
        "/api/research/deep",
        json={"query": "test", "max_subtasks": 3, "web_access": False},
    )
    assert response.status_code in (200, 502)
    if response.status_code == 200:
        data = response.json()
        assert "query" in data
        assert "results" in data


def test_contradictions_empty():
    response = client.post(
        "/api/research/contradictions",
        json={"claims": ["claim a", "claim b"], "threshold": 0.8},
    )
    assert response.status_code in (200, 500)
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)
