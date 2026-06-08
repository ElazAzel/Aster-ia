# Updates

## 2026-06-08 (afternoon)

- Fixed CORS middleware to allow `PUT`, `PATCH`, and `DELETE` methods (memory endpoints were blocked in cross-origin contexts).
- Replaced all `print()` calls in RAG file watcher with `StructuredLogger` for consistent structured JSON logging.
- Moved hardcoded ComfyUI URL (`127.0.0.1:8188`) and SearXNG URL (`127.0.0.1:8080`) to `Settings` config (`ASTERION_COMFYUI_URL`, `ASTERION_SEARXNG_URL`).
- Updated `ComfyUIService` and `SupervisorAgent` to accept `Settings` and use configurable URLs.
- Added `.env.example` with all environment variables documented.
- Rewrote `backend/README.md` with complete API reference (20+ endpoints across 11 routers) and configuration table.
- Added 34 pytest tests across 6 test files: `test_privacy_analyzer`, `test_model_router`, `test_rag`, `test_agent_sandbox`, `test_config`, `test_schemas`.
- Initialized Svelte frontend project structure: `package.json`, `vite.config.ts`, `svelte.config.js`, `tsconfig.json`, `index.html`, `src/main.ts`.
- Created Svelte app shell (`App.svelte`) with sidebar navigation and 7 view components: `ChatView`, `ModelSettings`, `PrivacyPanel`, `KnowledgeVault`, `AgentLab`, `WorkflowViewer`, `SystemStatus`.
- Updated `tauri.conf.json` to point `frontendDist` to `frontend/dist`.
- Added `backend/temp_db/`, `node_modules/`, `frontend/dist/` to `.gitignore`.
- Removed unused imports (`PrivacyReport` in `deep_research.py`, `Path` in `encrypted_sqlite.py`). Fixed ruff lint errors.

## 2026-06-08

- Implemented durable workflow state in `EncryptedSQLiteStore` schema and methods.
- Modified `WorkflowRunner` to persist workflow run status and step progress across application restarts.
- Added `WorkflowRunStatus` Pydantic model to API schemas.
- Exposed new API endpoints `GET /api/workflows/runs` (list active runs) and `GET /api/workflows/runs/{run_id}` (get details of a run).
- Implemented cryptographic plugin signature verification in `PluginManager` using a built-in trusted RSA-2048 public key.
- Added support for loading and validating companion `manifest.json.sig` signature files.
- Automatically downgrade unsigned or tampered plugins to `"local-only"` to prevent permission escalation.
- Implemented **RAG File Watcher** background service in `DocumentIndexer` using lightweight polling to automatically parse, chunk, embed, and index new/modified files from room directories.
- Added state-tracking using `watcher_state.json` to handle application restarts, self-heal directory-to-database state, and prevent redundant re-indexing of already-indexed files.
- Added automatic cleanup of LanceDB database records when monitored files are deleted from the watched folders.

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
