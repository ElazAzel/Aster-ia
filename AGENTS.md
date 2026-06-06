# Asterion AI Agent Instructions

These instructions apply to agents working in this repository.

## Product Contract

Asterion AI is a local-first desktop AI workspace. Default behavior must keep user prompts, files, memories, and generated artifacts on the local machine.

External API calls, public web access, network plugins, shell access, and broad file writes require explicit user approval.

## Technical Stack

- Desktop: Tauri v2 with Rust commands.
- Frontend: Svelte components.
- Backend: Python FastAPI, async `httpx`, pydantic v2.
- Models: Ollama for local chat and embeddings.
- Main DB: SQLite with SQLCipher. Key material must come from OS keychain via `keyring`.
- RAG: LanceDB plus Ollama `nomic-embed-text`.
- Analytics/research aggregation: DuckDB.
- Search: local SearXNG on `127.0.0.1:8080`.
- Image generation: local ComfyUI on `127.0.0.1:8188`.
- Voice: local `faster-whisper` extra when installed; fallback must stay local and never call external speech APIs.

## Hard Rules

- Use `async` service boundaries for backend IO.
- Every service that can be optimized by Meta-Harness must implement `BaseHarness.execute()`, `get_state()`, and `set_state()`.
- Every service must expose a `privacy_level`: `local`, `hybrid`, or `external`.
- Never store production secrets in `.env`, code, docs, fixtures, or logs.
- Structured logs must include `ts`, `action`, `tool`, `privacy_level`, and `error`.
- Run privacy checks before memory writes, model routing to API, web access, plugin execution, and file indexing.
- Voice transcription is `privacy_level=local`; missing local Whisper support must return a setup hint, not an external fallback.
- Keep generated code and docs Russian-friendly when they are user-facing.

## Agent and Skill Manifests

Runtime agent manifests live in `agents/*.json`.

Runtime skill manifests live in `skills/*.json`.

Keep manifests compact and declarative. The backend validates them through `AgentRegistry` and exposes them through:

- `GET /api/agents/catalog`
- `GET /api/agents/catalog/agents`
- `GET /api/agents/catalog/skills`
- `GET /api/agents/catalog/agents/{agent_id}`

## Verification

Before publishing changes:

```powershell
uv run python -m compileall backend\asterion_api harness\meta_harness.py
uv run python harness/meta_harness.py --phase 1 --iterations 3
npm --prefix frontend run build
```

If touching Tauri, also run `cargo check` in `src-tauri` after the Windows C++ build tools are available.

## Documentation

Update `docs/updates.md` after user-visible, architectural, or API changes.

Update `docs/agents-and-skills.md` when adding, removing, or changing manifests.
