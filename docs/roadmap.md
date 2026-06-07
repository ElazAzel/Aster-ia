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

Status: substantially implemented; remaining polish items.

- Durable workflow state across app restarts — implemented.
- OS-level sandbox: Windows (Job Objects), Linux (`resource`), **macOS** (RLIMIT_AS/CPU/NOFILE via `resource` in `preexec_fn`) — all three platforms implemented.
- Plugin signature verification — Ed25519 implemented; key distribution policy still needs documented release process.
- SearXNG deployment helper — Docker dev profile includes SearXNG; native desktop helper remains open.
- ComfyUI recipe library and validation — implemented with local preset catalog, preflight validation, generation-time blocking.
- RAG file watcher with opt-in folder scopes — backend watcher, room-scoped folder approvals, Vault scope management implemented; automatic watcher binding to approved scopes remains open.
- Secrets scanner in CI — implemented (`scripts/scan_secrets.py` + `security` workflow job).
- Full frontend E2E tests — 12 Playwright tests passing; more unmocked/integration journeys desirable.
- Tauri `cargo check` — green in CI; release packaging via tag-triggered workflow.

## Phase 5 - Power User Runtime

Status: implemented.

- **vLLM runtime profile**: `VllmService` (`BaseHarness`) with OpenAI-compatible client, graceful fallback, SSE `stream_generate()`, `GET /api/models/vllm/status`, `POST /api/models/vllm/generate`. Not yet integrated into the main chat model selector.
- **GPU hardware detection**: Rust PowerShell command in `src-tauri` for querying video controllers.
- **Model benchmark cache**: `BenchmarkService` (`BaseHarness`) with VRAM estimates for 20 models, 1h TTL cache, `POST /api/benchmark/run`, `BenchmarkTab.svelte` UI.
- **Larger local model catalog**: 3→17 models with task-based tag routing and `None`-safe RAM comparison.
- **Multi-room memory controls**: Memory Ledger scoped per room via existing room/memory APIs.
- **Research / analytics exports**: `POST /api/export` with JSON/MD/CSV, scope-based data collection. `AnalyticsTab.svelte` with 6 metrics and 4 chart panels.
- **macOS sandbox profile**: RLIMIT_AS/CPU/NOFILE via `resource` module in `agent_sandbox.py` Darwin branch.
- **Verification**: 136/136 backend tests, 12/12 Playwright E2E, frontend build clean, tsc 0 errors, ruff pass, secret scan clean.

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
