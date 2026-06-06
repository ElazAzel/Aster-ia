# Asterion AI

[![CI](https://github.com/ElazAzel/Aster-ia/actions/workflows/ci.yml/badge.svg)](https://github.com/ElazAzel/Aster-ia/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-violet.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![Svelte 5](https://img.shields.io/badge/svelte-5.0-orange.svg)](https://svelte.dev)
[![Tauri v2](https://img.shields.io/badge/tauri-v2-24C8D8.svg)](https://tauri.app)

Asterion AI is a local-first desktop AI workspace.

The current scaffold contains:

- Tauri v2 desktop shell.
- FastAPI sidecar backend.
- Ollama chat and embeddings.
- SQLCipher-encrypted SQLite storage with keys in the OS keychain.
- LanceDB RAG pipeline.
- DuckDB-backed research aggregation.
- Runtime Agent Registry with 10 agents and 20 skills.
- Agent catalog validation through `/api/agents/catalog/validate`.
- Workflow, plugin, sandbox, and privacy contracts.
- Svelte/Vite frontend shell wired to the FastAPI sidecar.
- Context Rooms, Adaptive Artifacts, Research Receipts, and AgentRun Flight Recorder APIs.
- Static HTML/Stitch UI prototypes.

## Quick Start

### 1. Предварительные требования

```bash
# Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3.2
ollama pull nomic-embed-text

# Python
curl -LsSf https://astral.sh/uv/install.sh | sh

# Node.js 22+
# Скачай с https://nodejs.org
```

### 2. Backend (FastAPI sidecar)

```bash
cd backend
uv sync
uv run python -m asterion_api --host 127.0.0.1 --port 8000

# Проверка
curl http://127.0.0.1:8000/api/health
```

### 3. Frontend (dev mode)

```bash
cd frontend
npm install
npm run dev
# Открой http://127.0.0.1:5173
```

### 4. Запуск тестов

```bash
cd backend
ASTERION_ALLOW_PLAINTEXT_SQLITE_FOR_DEV=1 uv run pytest tests/ -v
```

### 5. Desktop (Tauri) — требует Rust + MSVC

```bash
npm run tauri dev
```

Recommended local models:

```powershell
ollama pull llama3.2
ollama pull nomic-embed-text
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Default frontend URL:

```text
http://127.0.0.1:5173
```

Desktop shell:

```powershell
cd src-tauri
cargo check
```

`cargo check` on Windows requires Visual Studio Build Tools with the C++ workload so `link.exe` is available.

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

## Verification

```powershell
uv run python -m compileall backend\asterion_api harness\meta_harness.py
uv run python harness/meta_harness.py --phase 1 --iterations 3
cd frontend
npm run build
cd ..\src-tauri
cargo check
```

Tauri check currently requires a complete Windows C++ build toolchain with `link.exe`.
