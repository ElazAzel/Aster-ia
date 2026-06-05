# Asterion AI

Asterion AI is a local-first desktop AI workspace.

The current scaffold contains:

- Tauri v2 desktop shell.
- FastAPI sidecar backend.
- Ollama chat and embeddings.
- SQLCipher-encrypted SQLite storage with keys in the OS keychain.
- LanceDB RAG pipeline.
- DuckDB-backed research aggregation.
- Agent, skill, workflow, plugin, and privacy contracts.
- Static HTML/Stitch UI prototypes.

## Quick Start

```powershell
cd backend
uv run python -m asterion_api --host 127.0.0.1 --port 8000
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

Recommended local models:

```powershell
ollama pull llama3.2
ollama pull nomic-embed-text
```

## Key Documentation

- [Build Guide](BUILD_GUIDE.md)
- [Architecture](docs/architecture.md)
- [API Reference](docs/api.md)
- [Agents and Skills](docs/agents-and-skills.md)
- [Local Development](docs/local-dev.md)
- [Privacy and Security](docs/privacy-security.md)
- [Updates](docs/updates.md)

## Repository Layout

```text
backend/       FastAPI sidecar
frontend/      Svelte components and future app shell
src-tauri/     Tauri v2 Rust shell
agents/        Runtime agent manifests
skills/        Runtime skill manifests
harness/       Meta-Harness checks and candidate scores
docs/          Product and engineering docs
stitch/        UI prototype exports
```

## Verification

```powershell
uv run python -m compileall backend\asterion_api harness\meta_harness.py
uv run python harness/meta_harness.py --phase 1 --iterations 3
```

Tauri check currently requires a complete Windows C++ build toolchain with `link.exe`.
