# Asterion API Sidecar

FastAPI backend for the Asterion AI desktop app.

## Run Locally

```powershell
cd backend
cp .env.example .env   # optional: edit as needed
uv run python -m asterion_api
```

The API binds to `127.0.0.1:8000` by default.

Interactive docs at `http://127.0.0.1:8000/api/docs`.

## Routes

### Health

- `GET /api/health` — liveness probe

### Chat

- `POST /api/chat` — generate a single response
- `POST /api/chat/stream` — SSE streaming response (POST body)
- `GET /api/chat/stream` — SSE streaming response (query params)

### Models

- `GET /api/models` — list available Ollama models
- `POST /api/models/select` — set the active model

### Privacy

- `POST /api/privacy/analyze` — classify a prompt's risk level (green/yellow/red)

### Memory

- `POST /api/memory` — create a memory entry
- `GET /api/memory/{room_id}` — list memories for a room
- `PATCH /api/memory/{memory_id}` — update a memory entry
- `DELETE /api/memory/{memory_id}` — delete a memory entry

### RAG (Retrieval-Augmented Generation)

- `POST /api/rag/index` — index a file into LanceDB
- `POST /api/rag/search` — hybrid search (dense + BM25)

### Research

- `POST /api/research/deep` — deep research with query decomposition
- `POST /api/research/contradictions` — find contradictions in text

### Agents

- `GET /api/agents/catalog` — full agent + skill catalog
- `GET /api/agents/catalog/agents` — list agent manifests
- `GET /api/agents/catalog/skills` — list skill manifests
- `GET /api/agents/catalog/agents/{agent_id}` — get a specific agent
- `POST /api/agents/simulate` — plan a task (heuristic planner)
- `POST /api/agents/run-code` — execute code in sandboxed subprocess

### Images

- `POST /api/images/generate` — generate an image via ComfyUI

### Workflows

- `POST /api/workflows/run` — start a workflow run
- `POST /api/workflows/confirm` — approve a gated step
- `GET /api/workflows/runs` — list active workflow runs
- `GET /api/workflows/runs/{run_id}` — get details of a run
- `WS /api/workflows/events` — WebSocket for workflow events

### Plugins

- `GET /api/plugins` — list installed MCP plugins

## Configuration

All settings are read from environment variables. See `.env.example` for the full list.

| Variable | Default | Description |
|----------|---------|-------------|
| `ASTERION_API_HOST` | `127.0.0.1` | Bind address |
| `ASTERION_API_PORT` | `8000` | Bind port |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama runtime URL |
| `ASTERION_DEFAULT_MODEL` | `llama3.2` | Default chat model |
| `ASTERION_COMFYUI_URL` | `http://127.0.0.1:8188` | ComfyUI server URL |
| `ASTERION_SEARXNG_URL` | `http://127.0.0.1:8080` | SearXNG search URL |
| `ASTERION_DATA_DIR` | `~/.asterion` | Data storage directory |
| `ASTERION_KEYRING_SERVICE` | `asterion-ai` | OS keychain service name |

## Privacy Contract

The sidecar is local-first. All chat, embeddings, and RAG processing run against the local Ollama runtime. Database encryption keys are created and read through the OS keychain using `keyring`.

On Windows, the backend depends on `sqlcipher3-wheels` because the official `sqlcipher3-binary` package does not publish Windows wheels. The imported Python module remains `sqlcipher3`.

## Tests

```powershell
cd backend
uv run pytest -v
```
