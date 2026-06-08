# Local Development

## Required Tools

- Git
- `uv`
- Ollama
- Python through `uv`
- Rust and Cargo for Tauri work
- Windows C++ Build Tools for MSVC Tauri builds

Optional local services:

- SearXNG on `http://127.0.0.1:8080`
- ComfyUI on `http://127.0.0.1:8188`

## Backend Setup

From the repository root:

```powershell
cd backend
uv run python -m asterion_api --host 127.0.0.1 --port 8000
```

If a sandbox blocks the default `uv` cache under AppData, keep cache inside the repo:

```powershell
cd backend
uv --cache-dir ..\.uv-cache run python -m asterion_api --host 127.0.0.1 --port 8000
```

The backend stores local encrypted data under:

```text
%USERPROFILE%\.asterion
```

SQLCipher key material is generated and loaded through OS keychain via `keyring`.

## Ollama Models

```powershell
ollama pull llama3.2
ollama pull nomic-embed-text
```

Defaults:

- chat: `llama3.2`
- embeddings: `nomic-embed-text`

## Smoke Checks

Health:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

Models:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/models
```

Streaming chat:

```powershell
curl.exe -N "http://127.0.0.1:8000/api/chat/stream?message=ping&room_id=smoke&model=llama3.2"
```

Agent catalog:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/agents/catalog/validate
```

Expected catalog state:

```json
{
  "ok": true,
  "agents_count": 10,
  "skills_count": 20,
  "errors": [],
  "warnings": []
}
```

## Frontend Setup

The working Svelte/Vite shell lives in `frontend/`.

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

The UI reads the FastAPI base URL from:

```text
VITE_ASTERION_API_BASE
```

If the variable is absent, it defaults to:

```text
http://127.0.0.1:8000
```

Frontend build:

```powershell
cd frontend
npm run build
```

## Docker Dev Loop

The repository includes a local development Docker profile:

```powershell
docker compose up --build
```

Services:

- FastAPI backend on `http://127.0.0.1:8000`
- Svelte/Vite frontend on `http://127.0.0.1:5173`
- SearXNG on `http://127.0.0.1:8080`

The backend container reads Ollama from the host at:

```text
http://host.docker.internal:11434
```

Docker mode sets `ASTERION_ALLOW_PLAINTEXT_SQLITE_FOR_DEV=1` because generic Linux
containers do not have reliable OS keychain access. Desktop and normal local runs still
use SQLCipher + `keyring` by default.

## Voice Mode

Voice Mode works without external services. For real local transcription, install the
optional backend extra:

```powershell
cd backend
uv sync --extra dev --extra voice
```

Without the extra, `/api/voice/transcribe` stays local and returns a fallback setup hint.

## Offline Manifest Check

Run without starting FastAPI:

```powershell
cd backend
uv run python -c "from asterion_api.services.agent_registry import AgentRegistry; print(AgentRegistry().validate_catalog())"
```

Sandbox-safe variant:

```powershell
cd backend
uv --cache-dir ..\.uv-cache run python -c "from asterion_api.services.agent_registry import AgentRegistry; print(AgentRegistry().validate_catalog())"
```

## Verification

From the repository root:

```powershell
uv run python -m compileall backend\asterion_api harness\meta_harness.py
uv run python harness/meta_harness.py --phase 1 --iterations 3
cd frontend
npm run build
```

Sandbox-safe variant:

```powershell
uv --cache-dir .uv-cache run python -m compileall backend\asterion_api harness\meta_harness.py
uv --cache-dir .uv-cache run python harness/meta_harness.py --phase 1 --iterations 3
```

## Tauri

The Tauri shell now uses the Svelte/Vite app in `frontend/`.

Development:

```powershell
cd src-tauri
cargo tauri dev
```

The Tauri config runs:

```powershell
npm --prefix ../frontend run dev
```

Build:

```powershell
cd src-tauri
cargo tauri build
```

Rust check:

```powershell
cd src-tauri
cargo check
```

On Windows, the default MSVC target requires `link.exe` from Visual Studio Build Tools with the C++ workload.

Known environment issue: if `link.exe` or `dlltool.exe` is missing, Rust/Tauri checks fail before application code is compiled. Install the full C++ build tools, then rerun `cargo check`.

## Local Services Behavior

If optional services are not running:

- SearXNG-dependent research returns clear local-service errors or no public results when `web_access=false`.
- ComfyUI image generation returns a local-service failure instead of falling back to external image providers.
- Ollama-dependent routes should report the missing local service rather than silently using API models.
