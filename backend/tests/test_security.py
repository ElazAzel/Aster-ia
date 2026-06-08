from __future__ import annotations

import os
import json
import pytest
import httpx
from httpx import AsyncClient, ASGITransport

from asterion_api.config import get_settings
from asterion_api.main import app
from asterion_api.dependencies import get_store, get_plugin_manager
from asterion_api.services.privacy_analyzer import PrivacyAnalyzer

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


@pytest.fixture
async def test_app(tmp_path):
    os.environ["ASTERION_DATA_DIR"] = str(tmp_path)
    os.environ["ASTERION_ALLOW_PLAINTEXT_SQLITE_FOR_DEV"] = "1"
    
    get_settings.cache_clear()
    from asterion_api import dependencies
    dependencies.get_store.cache_clear()
    dependencies.get_plugin_manager.cache_clear()
    dependencies.get_privacy_analyzer.cache_clear()
    dependencies.get_agent_sandbox.cache_clear()
    
    # Reset rate limit request history between tests
    from asterion_api import main
    main.request_history.clear()
    
    store = get_store()
    await store.ensure_schema()
    
    yield app


@pytest.mark.asyncio
async def test_csp_and_security_headers(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        res = await ac.get("/api/health")
        assert res.status_code == 200
        assert "Content-Security-Policy" in res.headers
        assert "X-Frame-Options" in res.headers
        assert "X-Content-Type-Options" in res.headers
        assert "X-XSS-Protection" in res.headers
        
        csp = res.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert res.headers["X-Frame-Options"] == "DENY"


@pytest.mark.asyncio
async def test_rate_limiting(test_app, monkeypatch):
    from asterion_api.services.ollama_service import OllamaService
    async def mock_is_available(self):
        return True
    monkeypatch.setattr(OllamaService, "is_available", mock_is_available)

    from asterion_api import main
    main.RATE_LIMIT_REQUESTS = 5
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        # Send 5 successful requests
        for _ in range(5):
            res = await ac.get("/api/health")
            assert res.status_code == 200
            
        # The 6th request should be rate-limited
        res = await ac.get("/api/health")
        assert res.status_code == 429
        assert "Rate limit exceeded" in res.json()["detail"]


@pytest.mark.asyncio
async def test_pii_privacy_analyzer(test_app):
    analyzer = PrivacyAnalyzer()
    
    # 1. Test clean prompt
    report = analyzer.analyze(model_type="local", files_attached=False, memory_enabled=False, web_access=False, prompt="Привет, как дела?")
    assert report.level == "green"
    assert len(report.items) == 1  # model info only
    
    # 2. Test email prompt
    report = analyzer.analyze(model_type="local", files_attached=False, memory_enabled=False, web_access=False, prompt="Мой email: test@example.com")
    assert report.level == "yellow"
    assert any(item.what == "pii_email" and item.risk == "yellow" for item in report.items)
    
    # 3. Test email prompt with external API model
    report = analyzer.analyze(model_type="api", files_attached=False, memory_enabled=False, web_access=False, prompt="Мой email: test@example.com")
    assert report.level == "red"
    assert any(item.what == "pii_email" and item.risk == "red" for item in report.items)

    # 4. Test phone and address prompt
    report = analyzer.analyze(model_type="local", files_attached=False, memory_enabled=False, web_access=False, prompt="Живу на ул. Ленина, тел +7 (999) 123-45-67")
    assert report.level == "yellow"
    assert any(item.what == "pii_phone" for item in report.items)
    assert any(item.what == "pii_address" for item in report.items)


@pytest.mark.asyncio
async def test_audit_logs_endpoints(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        # List initially empty
        res = await ac.get("/api/audit/logs")
        assert res.status_code == 200
        assert len(res.json()) == 0
        
        # Record a consent log
        payload = {
            "action": "approve",
            "resource": "agent:chat-orchestrator",
            "details": "User approved shell and network permissions for orchestrator agent run."
        }
        res = await ac.post("/api/audit/logs", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["action"] == "approve"
        assert data["resource"] == "agent:chat-orchestrator"
        assert "ts" in data
        
        # Check list again
        res = await ac.get("/api/audit/logs")
        assert res.status_code == 200
        logs = res.json()
        assert len(logs) == 1
        assert logs[0]["action"] == "approve"


@pytest.mark.asyncio
async def test_plugin_signature_verification(test_app, tmp_path):
    pm = get_plugin_manager()
    plugin_dir = tmp_path / "plugins"
    pm.plugins_dir = plugin_dir
    
    # 1. Unsigned plugin seeking verified status -> gets downgraded to danger
    p1_dir = plugin_dir / "plugin_one"
    p1_dir.mkdir(parents=True)
    manifest = {
        "name": "Unsigned Elevate",
        "trust_level": "verified",
        "description": "Wants to be verified"
    }
    (p1_dir / "manifest.json").write_text(json.dumps(manifest))
    
    plugins = pm.load()
    assert len(plugins) == 1
    assert plugins[0].trust_level == "local-only"
    
    # 2. Signed plugin with valid signature
    p2_dir = plugin_dir / "plugin_two"
    p2_dir.mkdir(parents=True)
    
    # Generate Ed25519 key pair
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    p2_manifest = {
        "name": "Signed Verified",
        "trust_level": "verified",
        "description": "Properly signed plugin"
    }
    manifest_bytes = json.dumps(p2_manifest).encode("utf-8")
    (p2_dir / "manifest.json").write_bytes(manifest_bytes)
    
    # Write public key as PEM
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    (p2_dir / "public_key.pem").write_bytes(pub_pem)
    
    # Sign and write signature
    sig = private_key.sign(manifest_bytes)
    (p2_dir / "signature.sig").write_bytes(sig)
    
    plugins = pm.load()
    # Now we have 2 plugins loaded: plugin_one (danger) and plugin_two (verified)
    assert len(plugins) == 2
    p2_loaded = next(p for p in plugins if p.name == "Signed Verified")
    assert p2_loaded.trust_level == "verified"
    
    # 3. Signed plugin with corrupted signature -> skipped entirely
    p3_dir = plugin_dir / "plugin_three"
    p3_dir.mkdir(parents=True)
    p3_manifest = {
        "name": "Corrupted Signature",
        "trust_level": "verified"
    }
    (p3_dir / "manifest.json").write_bytes(json.dumps(p3_manifest).encode("utf-8"))
    (p3_dir / "public_key.pem").write_bytes(pub_pem)
    (p3_dir / "signature.sig").write_text("invalid-sig-hex-or-bytes-here")
    
    plugins = pm.load()
    # plugin_three should not be in the list because it signature check failed
    assert len(plugins) == 2
    assert not any(p.name == "Corrupted Signature" for p in plugins)


@pytest.mark.asyncio
async def test_system_backup_restore_and_wipe(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        store = get_store()
        
        # Add some initial test data (create room)
        await store.create_room(room_id="room_sec", name="Security Room", color="#ff00ff", allowed_models=[], memory_policy="session", retention_days=30)
        await store.create_memory(room_id="room_sec", content="Sensitive Memory", source="test", expires_at=None)
        
        # 1. Export backup
        res = await ac.post("/api/system/export", json={"passphrase": "supersecretpassword"})
        assert res.status_code == 200
        backup_str = res.json()["backup"]
        assert len(backup_str) > 0
        
        # 2. Wipe data
        with store._conns_lock:
            for conn in store._open_conns:
                try:
                    conn.close()
                except Exception:
                    pass
            store._open_conns.clear()

        if hasattr(store._local, "conn"):
            try:
                store._local.conn.close()
            except Exception:
                pass
            delattr(store._local, "conn")

        import asyncio
        loop = asyncio.get_running_loop()
        if getattr(loop, "_default_executor", None) is not None:
            loop._default_executor.shutdown(wait=True)
            loop._default_executor = None

        # Clear dependency caches and garbage collect to release references holding file locks
        from asterion_api import dependencies
        dependencies.get_store.cache_clear()
        dependencies.get_chat_service.cache_clear()
        dependencies.get_memory_ledger.cache_clear()
        dependencies.get_agent_executor.cache_clear()
        import gc
        gc.collect()

        res = await ac.post("/api/system/wipe")
        assert res.status_code == 200
        assert res.json()["ok"] is True
        
        # Check files/keys deleted. Re-ensure schema will create a fresh blank DB
        store = get_store()
        await store.ensure_schema()
        rooms = await store.list_rooms()
        # Fresh DB only has 'default' room, no 'room_sec'
        assert len(rooms) == 1
        assert rooms[0]["id"] == "default"
        
        # 3. Restore with wrong password -> should get bad request
        res = await ac.post("/api/system/import", json={"backup": backup_str, "passphrase": "wrongpassword"})
        assert res.status_code == 400
        
        # 4. Restore with correct password -> should succeed
        res = await ac.post("/api/system/import", json={"backup": backup_str, "passphrase": "supersecretpassword"})
        assert res.status_code == 200
        assert res.json()["ok"] is True
        
        # Check that room_sec was restored
        rooms = await store.list_rooms()
        assert any(r["id"] == "room_sec" for r in rooms)
        
        memories = await store.list_memories("room_sec")
        assert len(memories) == 1
        assert memories[0]["content"] == "Sensitive Memory"


@pytest.mark.asyncio
async def test_agent_sandbox_constraints(test_app):
    from asterion_api.services.agent_sandbox import AgentSandbox
    from asterion_api.schemas import AgentPermissions
    
    sandbox = AgentSandbox()
    
    # 1. Try running basic clean code
    code = "print('Hello Sandbox')"
    res = await sandbox.run_code(code=code, permissions=AgentPermissions())
    assert res["exit_code"] == 0
    assert "Hello Sandbox" in res["stdout"]
    
    # 2. Block code from shell if permission disabled
    code = "import os; os.system('echo hi')"
    with pytest.raises(PermissionError) as exc_info:
        await sandbox.run_code(code=code, permissions=AgentPermissions(shell=False))
    assert "shell" in str(exc_info.value).lower()
    
    # 3. Block code from network if permission disabled
    code = "import socket"
    with pytest.raises(PermissionError) as exc_info:
        await sandbox.run_code(code=code, permissions=AgentPermissions(network=False))
    assert "network" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_telemetry_endpoint(test_app, monkeypatch):
    posted_data = []

    original_post = httpx.AsyncClient.post

    async def mock_post(self, url, *args, **kwargs):
        if "telemetry.asterion.ai" in str(url):
            posted_data.append((str(url), kwargs.get("json")))
            return httpx.Response(200, json={"status": "success"})
        return await original_post(self, url, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        # 1. Test when opt_in is False -> should skip
        payload_opt_out = {
            "opt_in": False,
            "event_type": "app_start",
            "details": {}
        }
        res = await ac.post("/api/telemetry/report", json=payload_opt_out)
        assert res.status_code == 200
        assert res.json() == {"status": "skipped", "reason": "opt_out"}
        assert len(posted_data) == 0

        # 2. Test when opt_in is True -> should post to external url
        payload_opt_in = {
            "opt_in": True,
            "event_type": "app_start",
            "details": {"some": "info"},
            "vram_gb": 8.0,
            "ram_gb": 16.0,
            "os_platform": "win32"
        }
        res = await ac.post("/api/telemetry/report", json=payload_opt_in)
        assert res.status_code == 200
        assert res.json() == {"status": "success"}
        assert len(posted_data) == 1
        url, json_data = posted_data[0]
        assert url == "https://telemetry.asterion.ai/api/report"
        assert json_data["event_type"] == "app_start"
        assert json_data["vram_gb"] == 8.0
        assert json_data["ram_gb"] == 16.0
