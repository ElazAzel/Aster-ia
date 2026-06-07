# Roadmap

## Phase 1 - Local Sidecar Foundation

Status: implemented.

- FastAPI sidecar.
- Async Ollama service.
- `/api/health`, `/api/models`, `/api/chat`, `/api/chat/stream`.
- SQLCipher SQLite storage with OS keychain secret source.
- Tauri v2 sidecar lifecycle commands.
- BaseHarness interface.
- Meta-Harness Phase 1 latency check: first successful chat response target `< 5s`.

## Phase 2 - Agentic Workspace Core

Status: implemented as backend/runtime foundation.

- Streaming chat via FastAPI `StreamingResponse` and SSE.
- Privacy Radar with green/yellow/red JSON risk reports.
- ModelRouter with local-first VRAM routing.
- Memory Ledger CRUD with privacy checks.
- LanceDB RAG indexing and hybrid dense plus BM25 search.
- Deep Research supervisor with local SearXNG and DuckDB aggregation.
- Contradiction Finder with embeddings and opposing sentiment.
- TaskSimulator and AgentPlan generation.
- AgentSandbox subprocess execution with network/shell permission gates.
- ComfyUI localhost bridge.
- WorkflowRunner with human approval gates and WebSocket events.
- PluginManager for local MCP plugin manifests.
- Runtime agent catalog: 10 agents.
- Runtime skill catalog: 20 skills.
- `AgentRegistry.validate_catalog()` and `GET /api/agents/catalog/validate`.

## Phase 3 - Desktop Product Integration

Status: implemented.

- Svelte/Vite app shell connected to FastAPI routes.
- Chat history reload and conversation continuity.
- Tauri config now points to `frontend/dist` and runs Vite through `beforeDevCommand`/`beforeBuildCommand`.
- Frontend desktop bridge can start, health-check, and stop the FastAPI sidecar through Tauri IPC.
- Agent Catalog UI with validation status and manifest detail.
- Privacy Radar UI visible before elevated operations.
- Model Router UI with hardware profile controls.
- Memory Ledger UI with source and delete controls.
- RAG search UI over the local index.
- Task Simulator UI for AgentPlan generation.
- Context Rooms API and UI selector.
- Adaptive Artifacts API for block-level outputs and chat assistant response persistence.
- Research Receipt export API and UI surface.
- AgentRun and Flight Recorder API with UI log preview.
- Agent Lab UI for plan approval and sandbox runs.
- RAG file picker with explicit approval and indexed-source list.
- Workflow approval gate UI over WebSocket.
- ComfyUI recipe picker and local generation queue.
- Tauri sidecar binary packaging with bundled Python backend.
- Voice Mode backend and Svelte UI with local `faster-whisper` optional extra.
- Model Cookbook with Ollama pull progress.
- Research Canvas and Flight Recorder components.
- Docker dev profile and release/community docs.

## Phase 4 - Production Hardening

Status: partially implemented; hardening continues.

- Durable workflow state across app restarts.
- Stronger OS-level sandbox isolation on Windows, macOS, and Linux. Windows and Linux foundations are implemented; macOS isolation still needs a release-grade profile.
- Plugin signature verification. Ed25519 manifest verification is implemented; key distribution policy still needs a documented release process.
- SearXNG deployment helper. Docker dev profile includes SearXNG; native desktop helper remains open.
- ComfyUI recipe library and validation are implemented with local preset catalog, preflight validation, and generation-time blocking.
- RAG file watcher with opt-in folder scopes. Backend watcher exists; user-facing folder scope management needs hardening.
- Secrets scanner in CI is implemented through `scripts/scan_secrets.py` and the `security` workflow job.
- Full frontend E2E tests. Basic Playwright smoke exists; more production journeys are needed.
- Tauri `cargo check` is green in CI; release packaging remains covered by the tag-triggered release workflow.

## Phase 5 - Power User Runtime

Status: planned.

- vLLM runtime profile.
- GPU hardware detection.
- Model benchmark cache.
- Larger local model catalog.
- Multi-room memory controls.
- Research Studio report exports through DuckDB.
- Advanced workflow templates.

## Current Release Gate

Before publishing:

```powershell
uv run python -m compileall backend\asterion_api harness\meta_harness.py
uv run python harness/meta_harness.py --phase 1 --iterations 3
```

Required API checks:

- `GET /api/health`
- `GET /api/models`
- `GET /api/agents/catalog/validate`
- `POST /api/privacy/analyze`
- `GET /api/chat/stream`
- `GET /api/rooms`
- `POST /api/artifacts`
- `POST /api/agents/runs`
- `GET /api/voice/status`
