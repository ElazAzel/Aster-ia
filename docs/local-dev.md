# Local Development

## Required Tools

- `uv`
- Git
- Ollama
- Python through `uv`
- Rust and Cargo for Tauri work
- Windows C++ Build Tools for MSVC Tauri builds

## Backend Setup

```powershell
cd backend
uv run python -m asterion_api --host 127.0.0.1 --port 8000
```

The backend creates encrypted local data under:

```text
%USERPROFILE%\.asterion
```

SQLCipher key material is stored in the OS keychain through `keyring`.

## Ollama Models

```powershell
ollama pull llama3.2
ollama pull nomic-embed-text
```

`llama3.2` is the default chat model.

`nomic-embed-text` is the RAG and contradiction embedding model.

## Smoke Checks

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:8000/api/models
```

Streaming chat:

```powershell
curl.exe -N "http://127.0.0.1:8000/api/chat/stream?message=ping&room_id=smoke&model=llama3.2"
```

## Verification

```powershell
uv run python -m compileall backend\asterion_api harness\meta_harness.py
uv run python harness/meta_harness.py --phase 1 --iterations 3
```

## Tauri

```powershell
cd src-tauri
cargo check
```

On Windows, `cargo check` for the default MSVC target requires `link.exe` from Visual Studio Build Tools with the C++ workload.

## Local Services

Optional services:

- SearXNG: `http://127.0.0.1:8080`
- ComfyUI: `http://127.0.0.1:8188`

The backend should fail with clear local-service errors if those services are not running.
