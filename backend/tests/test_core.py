"""Smoke-tests для критических сервисов Asterion AI."""
from __future__ import annotations

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
    for cls in [OllamaService, PrivacyAnalyzer, DocumentIndexer, EncryptedSQLiteStore]:
        assert issubclass(cls, BaseHarness), f"{cls.__name__} не реализует BaseHarness"


# ── Workflow Runner ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_workflow_runner_completes():
    from asterion_api.services.workflow_runner import WorkflowRunner
    runner = WorkflowRunner()
    result = await runner.run({
        "steps": [
            {"name": "Шаг А", "type": "action"},
            {"name": "Шаг Б", "type": "action"},
        ]
    })
    assert result["status"] == "completed"
    assert len(result["results"]) == 2


@pytest.mark.asyncio
async def test_workflow_runner_pauses_on_approval():
    import asyncio
    from asterion_api.services.workflow_runner import WorkflowRunner
    runner = WorkflowRunner()
    task = asyncio.create_task(runner.run({
        "steps": [{"name": "Gate", "type": "human_approval"}]
    }))
    await asyncio.sleep(0.05)
    run_id = next(iter(runner.paused), None)
    if run_id:
        runner.confirm(run_id, True, {})
    result = await asyncio.wait_for(task, timeout=2)
    assert result["status"] in ("completed", "rejected")


# ── ContradictionFinder ───────────────────────────────────────────────────────

def test_contradiction_sentiment_positive():
    from asterion_api.services.contradiction_finder import ContradictionFinder
    finder = ContradictionFinder.__new__(ContradictionFinder)
    finder.positive = {"good", "works"}
    finder.negative = {"bad", "fails"}
    assert finder._sentiment("This works great") == "positive"


def test_contradiction_sentiment_negative():
    from asterion_api.services.contradiction_finder import ContradictionFinder
    finder = ContradictionFinder.__new__(ContradictionFinder)
    finder.positive = {"good", "works"}
    finder.negative = {"bad", "fails"}
    assert finder._sentiment("This bad and fails") == "negative"


def test_cosine_identical():
    from asterion_api.services.contradiction_finder import ContradictionFinder
    v = [1.0, 0.0, 0.5]
    assert abs(ContradictionFinder._cosine(v, v) - 1.0) < 1e-6


def test_cosine_orthogonal():
    from asterion_api.services.contradiction_finder import ContradictionFinder
    assert ContradictionFinder._cosine([1.0, 0.0], [0.0, 1.0]) < 0.01


# ── AgentSandbox security ─────────────────────────────────────────────────────

def test_sandbox_blocks_shell_without_permission():
    from asterion_api.services.agent_sandbox import AgentSandbox
    from asterion_api.schemas import AgentPermissions
    sandbox = AgentSandbox()
    with pytest.raises(PermissionError, match="shell"):
        sandbox._validate_code("import subprocess; subprocess.run(['ls'])", AgentPermissions())


def test_sandbox_blocks_network_without_permission():
    from asterion_api.services.agent_sandbox import AgentSandbox
    from asterion_api.schemas import AgentPermissions
    sandbox = AgentSandbox()
    with pytest.raises(PermissionError, match="network"):
        sandbox._validate_code("import httpx; httpx.get('http://x.com')", AgentPermissions())


def test_sandbox_path_traversal_blocked():
    import tempfile
    from asterion_api.services.agent_sandbox import AgentSandbox
    from asterion_api.schemas import AgentPermissions
    sandbox = AgentSandbox()
    perms = AgentPermissions(allowed_folders=[tempfile.gettempdir()])
    with pytest.raises(PermissionError, match="allowed"):
        sandbox._resolve_allowed("/etc/passwd", perms)


# ── TaskSimulator ─────────────────────────────────────────────────────────────

def test_task_simulator_adds_web_permission():
    from asterion_api.services.agent_sandbox import TaskSimulator
    simulator = TaskSimulator()
    plan = simulator.plan("search the web for AI trends")
    assert "web_search" in plan.required_permissions


def test_task_simulator_adds_write_permission():
    from asterion_api.services.agent_sandbox import TaskSimulator
    simulator = TaskSimulator()
    plan = simulator.plan("создай файл отчёта")
    assert "file_write" in plan.required_permissions


def test_task_simulator_token_estimate_reasonable():
    from asterion_api.services.agent_sandbox import TaskSimulator
    simulator = TaskSimulator()
    plan = simulator.plan("Analyse this document and generate a comprehensive report with findings")
    assert 800 <= plan.estimated_tokens <= 8000


# ── PluginManager ─────────────────────────────────────────────────────────────

def test_plugin_manager_empty_dir(tmp_path):
    import os
    os.environ["ASTERION_DATA_DIR"] = str(tmp_path)
    from asterion_api.config import get_settings
    get_settings.cache_clear()
    from asterion_api.services.plugin_manager import PluginManager
    manager = PluginManager(get_settings())
    plugins = manager.load()
    assert plugins == []


def test_plugin_manager_loads_manifest(tmp_path):
    import json
    import os
    os.environ["ASTERION_DATA_DIR"] = str(tmp_path)
    from asterion_api.config import get_settings
    get_settings.cache_clear()
    from asterion_api.services.plugin_manager import PluginManager
    settings = get_settings()
    plugin_dir = settings.data_dir / "plugins" / "test-plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "manifest.json").write_text(json.dumps({
        "name": "Test Plugin",
        "trust_level": "local-only",
        "description": "A test plugin"
    }))
    manager = PluginManager(settings)
    plugins = manager.load()
    assert len(plugins) == 1
    assert plugins[0].name == "Test Plugin"
    assert plugins[0].trust_level == "local-only"


# ── Storage: Rooms CRUD ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_room_create_and_read(tmp_path):
    import os
    os.environ["ASTERION_DATA_DIR"] = str(tmp_path)
    os.environ["ASTERION_ALLOW_PLAINTEXT_SQLITE_FOR_DEV"] = "1"
    from asterion_api.config import get_settings
    get_settings.cache_clear()
    from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore
    store = EncryptedSQLiteStore(get_settings())
    await store.ensure_schema()
    room = await store.create_room(
        room_id=None, name="Test Room", color="#ff0000",
        allowed_models=["llama3.2"], memory_policy="session", retention_days=7
    )
    assert room["name"] == "Test Room"
    fetched = await store.get_room(room["id"])
    assert fetched is not None
    assert fetched["color"] == "#ff0000"


@pytest.mark.asyncio
async def test_memory_create_and_expire(tmp_path):
    import os
    from datetime import UTC, datetime, timedelta
    os.environ["ASTERION_DATA_DIR"] = str(tmp_path)
    os.environ["ASTERION_ALLOW_PLAINTEXT_SQLITE_FOR_DEV"] = "1"
    from asterion_api.config import get_settings
    get_settings.cache_clear()
    from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore
    store = EncryptedSQLiteStore(get_settings())
    await store.ensure_schema()
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    await store.create_memory(room_id="default", content="expired", source="test", expires_at=past)
    await store.create_memory(room_id="default", content="active", source="test", expires_at=None)
    memories = await store.list_memories("default")
    contents = [m["content"] for m in memories]
    assert "active" in contents
    assert "expired" not in contents


@pytest.mark.asyncio
async def test_artifact_create_and_list(tmp_path):
    import os
    os.environ["ASTERION_DATA_DIR"] = str(tmp_path)
    os.environ["ASTERION_ALLOW_PLAINTEXT_SQLITE_FOR_DEV"] = "1"
    from asterion_api.config import get_settings
    get_settings.cache_clear()
    from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore
    store = EncryptedSQLiteStore(get_settings())
    await store.ensure_schema()
    artifact = await store.create_artifact(
        room_id="default", kind="chat", title="Test",
        blocks=[{"type": "text", "content": "hello"}], source="test"
    )
    assert artifact["kind"] == "chat"
    listing = await store.list_artifacts("default")
    assert any(a["id"] == artifact["id"] for a in listing)
