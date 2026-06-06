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
- Runtime skill catalog: 16 skills.
- `AgentRegistry.validate_catalog()` and `GET /api/agents/catalog/validate`.

## Phase 3 - Desktop Product Integration

Status: in progress.

- Svelte/Vite app shell connected to FastAPI routes.
- Tauri config now points to `frontend/dist` and runs Vite through `beforeDevCommand`/`beforeBuildCommand`.
- Frontend desktop bridge can start, health-check, and stop the FastAPI sidecar through Tauri IPC.
- Agent Catalog UI with validation status and manifest detail.
- Privacy Radar UI visible before elevated operations.
- Model Router UI with hardware profile controls.
- Memory Ledger UI with source and delete controls.
- RAG search UI over the local index.
- Task Simulator UI for AgentPlan generation.
- Agent Lab UI for plan approval and sandbox runs.
- RAG file picker with explicit approval and indexed-source list.
- Workflow approval gate UI over WebSocket.
- ComfyUI recipe picker and local generation queue.
- Tauri sidecar binary packaging with bundled Python backend.

## Phase 4 - Production Hardening

Status: planned.

- Durable workflow state across app restarts.
- Stronger OS-level sandbox isolation on Windows, macOS, and Linux.
- Plugin signature verification.
- SearXNG deployment helper.
- ComfyUI recipe library and validation.
- RAG file watcher with opt-in folder scopes.
- Secrets scanner in CI.
- Full frontend E2E tests.
- Tauri `cargo check` and packaging in CI after Windows C++ toolchain is available.

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
