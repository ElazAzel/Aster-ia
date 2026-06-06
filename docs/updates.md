# Updates

## 2026-06-06

- Added MVP backend contracts for Context Rooms, Adaptive Artifacts, Research Receipts, AgentRun persistence, and Flight Recorder logs.
- Added `GET/POST/PATCH/DELETE /api/rooms`, `POST/GET /api/artifacts`, `GET/DELETE /api/rag/documents`, `POST /api/research/report/export`, and AgentRun log/event endpoints.
- Added Svelte UI controls for Context Rooms, Vault document metadata, Research Receipt export, and AgentRun/Flight Recorder preview.
- Added runtime skill manifests for `context-rooms`, `adaptive-artifacts`, `research-receipts`, and `flight-recorder`.
- Added `docs/product-mvp-plan.md` and `docs/launch-kit.md` for product design and creative-production launch planning.
- Expanded runtime agent catalog from 6 to 10 agents with `chat-orchestrator`, `model-curator`, `memory-curator`, and `plugin-auditor`.
- Expanded runtime skill catalog from 12 to 16 skills with `conversation-orchestration`, `ollama-operations`, `sqlcipher-storage`, and `agent-catalog-governance`.
- Added manifest lifecycle metadata: `triggers`, `lifecycle`, `outputs`, `handoff_targets`, `acceptance_checks`, `requires_consent`, and `failure_modes`.
- Added `AgentRegistry.validate_catalog()` to detect malformed manifests, duplicate ids, unknown skill references, and unknown handoff targets.
- Added `GET /api/agents/catalog/validate` for UI and release checks.
- Reworked docs for architecture, API, local development, privacy/security, roadmap, and agents/skills to match the current runtime catalog.
- Verified catalog locally with `ok=true`, 10 agents, 16 skills, and no warnings.
- Added a runnable Svelte/Vite frontend shell in `frontend/` with live SSE chat, Privacy Radar, Model Router, Agent Catalog, Memory Ledger, RAG search, and Task Simulator panels.
- Connected Tauri configuration to `frontend/dist` and added a Svelte Tauri IPC bridge for starting, health-checking, and stopping the FastAPI sidecar.

## 2026-06-05

- Added Phase 1 Asterion AI FastAPI sidecar scaffold with `/api/health`, `/api/models`, `/api/chat`, and `/api/chat/stream`.
- Added async `OllamaService` with `list_models()`, `generate()`, and `stream_generate()`.
- Added SQLCipher-oriented encrypted SQLite store using `sqlcipher3`/`sqlcipher3-binary` and OS keychain secrets through `keyring`.
- Added Windows-compatible SQLCipher dependency resolution through `sqlcipher3-wheels`, while preserving the `sqlcipher3` import path.
- Added `BaseHarness` contract and implemented it in storage, Ollama, and chat services.
- Added Tauri v2 sidecar lifecycle commands: `start_fastapi_sidecar`, `fastapi_health_check`, and `shutdown_fastapi_sidecar`.
- Added local Meta-Harness onboarding notes and `domain_spec.md` for Asterion AI.
- Verified `uv run python harness/meta_harness.py --phase 1 --iterations 3` with 100% source/UI contracts and average mock chat latency below 5 seconds.
- Added real SSE streaming chat endpoint for browser `EventSource` and a Svelte `StreamingChat` component.
- Added `PrivacyAnalyzer`, `ModelRouter`, Memory Ledger CRUD API, LanceDB RAG indexing/search, Deep Research via local SearXNG, contradiction detection, agent sandbox/task simulation, ComfyUI bridge, workflow runner, and plugin manifest loader.
- Pulled local Ollama models `llama3.2` and `nomic-embed-text` for chat and embeddings smoke checks.
- Added root `README.md`, repository `AGENTS.md`, architecture/API/local-dev/privacy/roadmap docs, runtime agent manifests, runtime skill manifests, and `AgentRegistry` catalog API.
