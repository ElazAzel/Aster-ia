# Asterion AI

[![CI](https://github.com/ElazAzel/Aster-ia/actions/workflows/ci.yml/badge.svg)](https://github.com/ElazAzel/Aster-ia/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-violet.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![Svelte 5](https://img.shields.io/badge/svelte-5.0-orange.svg)](https://svelte.dev)
[![Tauri v2](https://img.shields.io/badge/tauri-v2-24C8D8.svg)](https://tauri.app)

Asterion AI is a local-first desktop AI workspace: a control room for models, documents, research, voice notes, workflows, and transparent agents.

Core principle: prompts, files, memories, embeddings, generated artifacts, and agent logs stay on the user's machine unless the user explicitly approves a hybrid or external action.

## What Works

- Tauri v2 desktop shell with FastAPI sidecar lifecycle commands.
- FastAPI backend with async services and `BaseHarness` contracts.
- Ollama local chat, streaming SSE, model pull, and embedding flows.
- SQLCipher-oriented SQLite storage with OS keychain key material.
- LanceDB RAG indexing and hybrid dense plus BM25 search.
- Context Rooms, Memory Ledger, Adaptive Artifacts, Research Receipts, and Flight Recorder persistence.
- Deep Research via local SearXNG and DuckDB aggregation.
- Agent catalog with 10 runtime agents and 20 runtime skills.
- Agent sandbox, TaskSimulator, workflow approval gates, plugin manifest loading, ComfyUI bridge, and Voice Mode.
- Svelte/Vite workspace with Smart Chat, Knowledge Vault, Research Studio, Agent Lab, Image Studio, Automation, Plugins, System Console, Model Cookbook, Voice Mode, **Benchmark**, and **Analytics**.
- Model benchmark cache (`BenchmarkService`) with VRAM estimates for 20 models, sortable results, and vLLM status panel.
- Analytics dashboard with 6 metrics (queries, sources, claims, conversations, agents, reports) and chart panels.
- Export router (`POST /api/export`) with JSON / Markdown / CSV output across artifacts, memories, conversations, research receipts, and audit logs.
- vLLM runtime profile (`VllmService`) with OpenAI-compatible client, graceful fallback, and SSE streaming generation.
- macOS sandbox profile with RLIMIT_AS/CPU/NOFILE isolation.
- Docker dev profile for backend/frontend/SearXNG.
- Release workflow that builds the Python sidecar and Tauri bundles on tags.

## Quick Start

Install local dependencies:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
ollama pull llama3.2
ollama pull nomic-embed-text
```

Run the backend:

```bash
cd backend
uv sync --extra dev
uv run python -m asterion_api --host 127.0.0.1 --port 8000
```

Run the frontend:

```bash
cd frontend
npm ci
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

Optional Docker dev loop:

```bash
docker compose up --build
```

Docker mode is for local development and uses `ASTERION_ALLOW_PLAINTEXT_SQLITE_FOR_DEV=1` because generic containers do not have reliable OS keychain access. Normal desktop/local runs keep SQLCipher + keyring as the default path.

## Voice Mode

Voice Mode never falls back to an external speech API. Real transcription uses local `faster-whisper` when installed:

```bash
cd backend
uv sync --extra dev --extra voice
```

Without the optional extra, `/api/voice/transcribe` returns a local setup hint.

## Desktop

```bash
cd src-tauri
cargo check
cargo tauri dev
```

On Windows, `cargo check` requires Visual Studio Build Tools with the C++ workload so `link.exe` is available.

## Verification

```powershell
uv run python -m compileall backend\asterion_api harness\meta_harness.py
uv run python harness/meta_harness.py --phase 1 --iterations 3
uv run python scripts\scan_secrets.py .
cd backend
uv run ruff check .
uv run pytest
cd ..\frontend
npm run build
npx tsc --noEmit
```

## Key Documentation

- [Build Guide](BUILD_GUIDE.md)
- [Architecture](docs/architecture.md)
- [API Reference](docs/api.md)
- [Agents and Skills](docs/agents-and-skills.md)
- [Local Development](docs/local-dev.md)
- [Privacy and Security](docs/privacy-security.md)
- [Power-user MVP Product Plan](docs/product-mvp-plan.md)
- [Launch Kit](docs/launch-kit.md)
- [Updates](docs/updates.md)

## Repository Layout

```text
backend/       FastAPI sidecar
frontend/      Svelte/Vite app shell
src-tauri/     Tauri v2 Rust shell
agents/        Runtime agent manifests
skills/        Runtime skill manifests
harness/       Meta-Harness checks and candidate scores
docs/          Product and engineering docs
stitch/        UI prototype exports
```
