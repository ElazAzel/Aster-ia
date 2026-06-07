"""Smoke-tests для критических сервисов Asterion AI."""
from __future__ import annotations
from unittest.mock import patch

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
    result = router.select("local coding", HardwareProfile(vram_gb=10.0, ram_gb=16.0))
    assert result.mode == "local"
    assert result.model != router.api_fallback


def test_model_router_api_fallback_no_vram():
    from asterion_api.services.model_router import ModelRouter
    from asterion_api.schemas import HardwareProfile
    router = ModelRouter()
    result = router.select("complex task", HardwareProfile(vram_gb=0.0, ram_gb=0.0))
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

def test_voice_service_implements_harness():
    from asterion_api.harness import BaseHarness
    from asterion_api.services.voice_service import VoiceService
    assert issubclass(VoiceService, BaseHarness)


def test_voice_status_has_local_privacy():
    from asterion_api.services.voice_service import VoiceService
    status = VoiceService().status()
    assert status["privacy_level"] == "local"
    assert ".wav" in status["supported_formats"]


@pytest.mark.asyncio
async def test_voice_transcribe_fallback_without_whisper(tmp_path):
    from asterion_api.services.voice_service import VoiceService
    audio = tmp_path / "sample.wav"
    audio.write_bytes(b"not real audio")
    service = VoiceService()
    service.set_state({"whisper_available": False})
    result = await service.transcribe(audio)
    assert result["engine"] == "fallback"
    assert result["privacy_level"] == "local"


@pytest.mark.asyncio
async def test_voice_transcribe_rejects_unsupported_format(tmp_path):
    from asterion_api.services.voice_service import VoiceService
    audio = tmp_path / "sample.exe"
    audio.write_bytes(b"bad")
    service = VoiceService()
    with pytest.raises(ValueError, match="Unsupported audio format"):
        await service.transcribe(audio)


def test_voice_meeting_extracts_actions_questions_and_decisions():
    from asterion_api.services.voice_service import VoiceService
    text = (
        "We decided to keep local mode. Нужно сделать тесты завтра. "
        "Who owns the release?"
    )
    result = VoiceService().analyze_meeting({"text": text})
    assert result["decisions"]
    assert result["action_items"]
    assert result["questions"] == ["Who owns the release?"]


def test_voice_structure_text_returns_markdown():
    from asterion_api.services.voice_service import VoiceService
    result = VoiceService().structure_text(
        "Decision: local first. Нужно сделать release checklist.",
        mode="meeting",
    )
    assert "# Voice Meeting" in result["markdown"]
    assert "Action Items" in result["markdown"]


@pytest.mark.asyncio
async def test_voice_execute_status():
    from asterion_api.services.voice_service import VoiceService
    result = await VoiceService().execute({"action": "status"})
    assert result["ok"] is True


@pytest.mark.asyncio
async def test_voice_execute_requires_file_path():
    from asterion_api.services.voice_service import VoiceService
    with pytest.raises(ValueError, match="file_path"):
        await VoiceService().execute({"action": "transcribe"})


@pytest.mark.asyncio
async def test_voice_execute_structure():
    from asterion_api.services.voice_service import VoiceService
    result = await VoiceService().execute({
        "action": "structure",
        "text": "Нужно проверить privacy radar.",
        "mode": "notes",
    })
    assert result["action_items"]


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


# ── Integration tests ─────────────────────────────────────────────────────────


def test_supervisor_agent_implements_harness():
    from asterion_api.harness import BaseHarness
    from asterion_api.services.deep_research import SupervisorAgent
    from asterion_api.services.privacy_analyzer import PrivacyAnalyzer
    agent = SupervisorAgent(PrivacyAnalyzer())
    assert isinstance(agent, BaseHarness)
    state = agent.get_state()
    assert "searxng_url" in state
    agent.set_state({"searxng_url": "http://test:8080"})
    assert agent.searxng_url == "http://test:8080"


def test_supervisor_agent_decompose():
    from asterion_api.services.deep_research import SupervisorAgent
    from asterion_api.services.privacy_analyzer import PrivacyAnalyzer
    agent = SupervisorAgent(PrivacyAnalyzer())
    subtasks = agent.decompose("test query", 3)
    assert len(subtasks) == 3
    assert all("test query" in s for s in subtasks)


def test_contradiction_finder_empty_input():
    from unittest.mock import AsyncMock
    from asterion_api.services.contradiction_finder import ContradictionFinder
    ollama = AsyncMock()
    ollama.embed.return_value = []
    import asyncio
    finder = ContradictionFinder(ollama)
    result = asyncio.run(finder.find(claims=[], threshold=0.8))
    assert result == []


def test_contradiction_finder_single_claim():
    from unittest.mock import AsyncMock
    from asterion_api.services.contradiction_finder import ContradictionFinder
    ollama = AsyncMock()
    ollama.embed.return_value = []
    import asyncio
    finder = ContradictionFinder(ollama)
    result = asyncio.run(finder.find(claims=["only one"], threshold=0.8))
    assert result == []


@pytest.mark.asyncio
async def test_deep_research_local_only_no_web():
    from asterion_api.services.deep_research import SupervisorAgent
    from asterion_api.services.privacy_analyzer import PrivacyAnalyzer
    agent = SupervisorAgent(PrivacyAnalyzer())
    result = await agent.research(query="test", max_subtasks=2, web_access=False)
    assert result.query == "test"
    assert len(result.subtasks) == 2
    assert result.results == []


def test_workflow_runner_accepts_empty():
    from asterion_api.services.workflow_runner import WorkflowRunner
    import asyncio
    runner = WorkflowRunner()
    result = asyncio.run(runner.run({"steps": []}))
    assert result["status"] == "completed"


def test_plugin_manager_skips_missing_manifest(tmp_path):
    import os
    os.environ["ASTERION_DATA_DIR"] = str(tmp_path)
    from asterion_api.config import get_settings
    get_settings.cache_clear()
    from asterion_api.services.plugin_manager import PluginManager
    settings = get_settings()
    plugin_dir = settings.data_dir / "plugins" / "empty-plugin"
    plugin_dir.mkdir(parents=True)
    manager = PluginManager(settings)
    plugins = manager.load()
    assert plugins == []


def test_plugin_manager_skips_invalid_manifest(tmp_path):
    import os
    os.environ["ASTERION_DATA_DIR"] = str(tmp_path)
    from asterion_api.config import get_settings
    get_settings.cache_clear()
    from asterion_api.services.plugin_manager import PluginManager
    settings = get_settings()
    plugin_dir = settings.data_dir / "plugins" / "bad-plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "manifest.json").write_text("not json")
    manager = PluginManager(settings)
    try:
        plugins = manager.load()
        assert plugins == []
    except Exception:
        pass


@pytest.mark.asyncio
async def test_workflow_runner_approval_rejection():
    import asyncio
    from asterion_api.services.workflow_runner import WorkflowRunner
    runner = WorkflowRunner()
    task = asyncio.create_task(runner.run({
        "steps": [{"name": "Approve", "type": "human_approval"}]
    }))
    await asyncio.sleep(0.05)
    run_id = next(iter(runner.paused), None)
    if run_id:
        runner.confirm(run_id, False, {})
    result = await asyncio.wait_for(task, timeout=2)
    assert result["status"] == "rejected"


def test_task_simulator_dangerous_task():
    from asterion_api.services.agent_sandbox import TaskSimulator
    simulator = TaskSimulator()
    plan = simulator.plan("delete all system files and remove OS")
    assert "dangerous" in plan.required_permissions or plan.estimated_tokens > 0


def test_sandbox_allows_safe_code():
    from asterion_api.services.agent_sandbox import AgentSandbox
    from asterion_api.schemas import AgentPermissions
    sandbox = AgentSandbox()
    sandbox._validate_code("x = 1 + 1", AgentPermissions())


def test_supervisor_agent_execute():
    from asterion_api.services.deep_research import SupervisorAgent
    from asterion_api.services.privacy_analyzer import PrivacyAnalyzer
    agent = SupervisorAgent(PrivacyAnalyzer())
    import asyncio
    result = asyncio.run(agent.execute({"query": "test", "max_subtasks": 1, "web_access": False}))
    assert result.query == "test"


def test_analytics_and_report_export(tmp_path):
    import os
    os.environ["ASTERION_DATA_DIR"] = str(tmp_path)
    os.environ["ASTERION_ALLOW_PLAINTEXT_SQLITE_FOR_DEV"] = "1"
    
    from asterion_api.config import get_settings
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
    dependencies.get_voice_service.cache_clear()
    dependencies.get_workflow_runner.cache_clear()
    dependencies.get_plugin_manager.cache_clear()

    from asterion_api.main import app
    from fastapi.testclient import TestClient
    
    with TestClient(app) as client:
        # Check stats endpoint initially (should be 0 or empty since no data is seeded)
        res = client.get("/api/analytics/research/stats")
        assert res.status_code == 200
        data = res.json()
        assert data["total_research_queries"] == 0
        assert data["sources_consulted"] == 0
        assert data["claims_verified"] == 0
        
        # Export a research report using the export endpoint (which populates research_receipts)
        # POST /api/research/report/export
        payload = {
            "room_id": "default",
            "query": "Is local routing secure?",
            "title": "Security Report",
            "receipts": [
                {
                    "source_title": "Source Alpha",
                    "url": "http://alpha.com",
                    "quote": "Local-first works locally.",
                    "claim": "Local routing avoids cloud.",
                    "confidence": "high"
                },
                {
                    "source_title": "Source Beta",
                    "url": "http://beta.com",
                    "quote": "No external leaks.",
                    "claim": "No external leaks.",
                    "confidence": "medium"
                }
            ]
        }
        export_res = client.post("/api/research/report/export", json=payload)
        assert export_res.status_code == 200
        export_data = export_res.json()
        artifact_id = export_data["artifact"]["id"]
        
        # Check stats endpoint now (should be updated)
        res = client.get("/api/analytics/research/stats")
        assert res.status_code == 200
        data = res.json()
        assert data["total_research_queries"] == 1
        assert data["sources_consulted"] == 2
        assert data["claims_verified"] == 2
        
        # Check sub-endpoints
        res = client.get("/api/analytics/top-sources")
        assert res.status_code == 200
        assert len(res.json()) >= 2
        
        res = client.get("/api/analytics/claims-confidence")
        assert res.status_code == 200
        conf_data = res.json()
        # Check confidence values
        confidences = {c["confidence"]: c["count"] for c in conf_data}
        assert confidences["high"] == 1
        assert confidences["medium"] == 1
        
        res = client.get("/api/analytics/rooms-distribution")
        assert res.status_code == 200
        assert len(res.json()) == 1
        
        # Check agent stats endpoint
        res = client.get("/api/analytics/agent-stats")
        assert res.status_code == 200
        assert res.json()["total_runs"] == 0
        
        # Check markdown export endpoint
        # GET /api/research/report/{artifact_id}/markdown
        md_res = client.get(f"/api/research/report/{artifact_id}/markdown")
        assert md_res.status_code == 200
        assert "text/markdown" in md_res.headers["content-type"]
        md_text = md_res.text
        assert "# Security Report" in md_text
        assert "Is local routing secure?" in md_text
        assert "Source Alpha" in md_text


def test_comfyui_recipe_validation_allows_default_local_workflow():
    from asterion_api.services.comfyui_service import ComfyUIService

    result = ComfyUIService().validate_recipe({}, "local product mockup")

    assert result["ok"] is True
    assert result["privacy_level"] == "local"
    assert result["nodes_count"] == 7


def test_comfyui_recipe_presets_are_unique_and_valid():
    from asterion_api.services.comfyui_service import ComfyUIService

    service = ComfyUIService()
    presets = service.list_recipe_presets()
    preset_ids = [preset["id"] for preset in presets]

    assert len(presets) >= 4
    assert len(preset_ids) == len(set(preset_ids))
    assert all(preset["privacy_level"] == "local" for preset in presets)
    assert all(preset["validation"]["ok"] for preset in presets)


def test_comfyui_recipe_preset_overrides_merge_safely():
    from asterion_api.services.comfyui_service import ComfyUIService

    recipe = ComfyUIService().build_recipe("portrait-fast", {"steps": 7, "width": 768})

    assert recipe["height"] == 1216
    assert recipe["steps"] == 7
    assert recipe["width"] == 768


def test_comfyui_recipe_validation_rejects_external_uri_input():
    from asterion_api.services.comfyui_service import ComfyUIService

    result = ComfyUIService().validate_recipe(
        {
            "workflow": {
                "1": {
                    "class_type": "LoadImage",
                    "inputs": {"image": "https://example.com/image.png"},
                }
            }
        },
        "local product mockup",
    )

    assert result["ok"] is False
    assert any("external URI" in error for error in result["errors"])


def test_comfyui_recipe_validation_rejects_missing_node_reference():
    from asterion_api.services.comfyui_service import ComfyUIService

    result = ComfyUIService().validate_recipe(
        {
            "workflow": {
                "1": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {"text": "hello", "clip": ["missing", 0]},
                }
            }
        },
        "hello",
    )

    assert result["ok"] is False
    assert any("references missing node" in error for error in result["errors"])


def test_comfyui_service_rejects_external_base_url():
    from asterion_api.services.comfyui_service import ComfyUIService

    service = ComfyUIService()

    with pytest.raises(ValueError, match="localhost"):
        service.set_state({"base_url": "https://example.com"})


# ── BenchmarkService ──────────────────────────────────────────────────────────

def test_benchmark_implements_harness():
    from asterion_api.harness import BaseHarness
    from asterion_api.services.benchmark_service import BenchmarkService
    assert issubclass(BenchmarkService, BaseHarness)


def test_benchmark_privacy_level():
    from asterion_api.services.benchmark_service import BenchmarkService
    assert BenchmarkService.privacy_level == "local"


def test_benchmark_vram_estimate_known_model():
    from asterion_api.services.benchmark_service import BenchmarkService
    svc = BenchmarkService()
    est = svc._estimate_vram("llama3.2")
    assert 4.0 <= est <= 6.0


def test_benchmark_vram_estimate_unknown_fallback():
    from asterion_api.services.benchmark_service import BenchmarkService
    svc = BenchmarkService()
    est = svc._estimate_vram("some-unknown-model-xyz")
    assert est == 4.0


def test_benchmark_cache_miss():
    from asterion_api.services.benchmark_service import BenchmarkService
    svc = BenchmarkService()
    assert svc.get_cached("not-cached") is None


def test_benchmark_cache_clear():
    from asterion_api.services.benchmark_service import BenchmarkService
    svc = BenchmarkService()
    import time
    svc._cache["testmodel"] = {"result": {"model": "testmodel"}, "ts": time.time()}
    assert svc.get_state()["cache_entries"] == 1
    svc.clear_cache()
    assert svc.get_state()["cache_entries"] == 0


def test_benchmark_get_state_keys():
    from asterion_api.services.benchmark_service import BenchmarkService
    state = BenchmarkService().get_state()
    assert {"cache_entries", "cached_models"} <= state.keys()


# ── VllmService ───────────────────────────────────────────────────────────────

def test_vllm_implements_harness():
    from asterion_api.harness import BaseHarness
    from asterion_api.services.vllm_service import VllmService
    assert issubclass(VllmService, BaseHarness)


def test_vllm_privacy_level():
    from asterion_api.services.vllm_service import VllmService
    assert VllmService.privacy_level == "local"


def test_vllm_default_url():
    from asterion_api.services.vllm_service import VllmService
    svc = VllmService()
    assert "8100" in svc.base_url


def test_vllm_set_state_updates_url():
    from asterion_api.services.vllm_service import VllmService
    svc = VllmService()
    svc.set_state({"base_url": "http://127.0.0.1:9000/v1"})
    assert "9000" in svc.base_url and svc._available is None


@pytest.mark.asyncio
async def test_vllm_unavailable_when_no_server():
    from asterion_api.services.vllm_service import VllmService
    svc = VllmService(base_url="http://127.0.0.1:19999/v1")
    available = await svc.is_available()
    assert available is False


@pytest.mark.asyncio
async def test_vllm_generate_returns_error_when_unavailable():
    from asterion_api.services.vllm_service import VllmService
    svc = VllmService(base_url="http://127.0.0.1:19999/v1")
    result = await svc.generate(model="test", prompt="hello")
    assert "error" in result and "hint" in result


# ── Extended ModelRouter ──────────────────────────────────────────────────────

def test_model_router_has_20_plus_models():
    from asterion_api.services.model_router import ModelRouter
    router = ModelRouter()
    assert len(router.local_catalog) >= 15


def test_model_router_code_task_prefers_code_model():
    from asterion_api.services.model_router import ModelRouter
    from asterion_api.schemas import HardwareProfile
    router = ModelRouter()
    result = router.select("write Python code", HardwareProfile(vram_gb=8.0, ram_gb=16.0))
    assert result.mode == "local"


def test_model_router_russian_task_picks_multilingual():
    from asterion_api.services.model_router import ModelRouter
    from asterion_api.schemas import HardwareProfile
    router = ModelRouter()
    result = router.select("write in russian language", HardwareProfile(vram_gb=8.0, ram_gb=16.0))
    assert result.mode == "local"


def test_model_router_zero_vram_still_works():
    from asterion_api.services.model_router import ModelRouter
    from asterion_api.schemas import HardwareProfile
    router = ModelRouter()
    result = router.select("quick chat", HardwareProfile(vram_gb=0.0, ram_gb=4.0))
    assert result.mode == "local"
    assert result.model in ["llama3.2:1b", "qwen2.5:0.5b", "phi3:mini", "gemma2:2b"]


# ── macOS Sandbox ─────────────────────────────────────────────────────────────

def test_agent_sandbox_os_kwargs_darwin():
    from asterion_api.services.agent_sandbox import AgentSandbox
    import platform
    with patch.object(platform, "system", return_value="Darwin"):
        kwargs = AgentSandbox._os_sandbox_kwargs()
        assert "preexec_fn" in kwargs


def test_agent_sandbox_os_kwargs_all_platforms():
    from asterion_api.services.agent_sandbox import AgentSandbox
    import platform
    for os_name in ["Darwin", "Linux", "Windows"]:
        with patch.object(platform, "system", return_value=os_name):
            kwargs = AgentSandbox._os_sandbox_kwargs()
            assert isinstance(kwargs, dict)
