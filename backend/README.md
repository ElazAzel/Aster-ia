# Asterion API Sidecar

FastAPI backend for the Asterion AI desktop app.

## Run Locally

```powershell
cd backend
uv run python -m asterion_api
```

The API binds to `127.0.0.1:8000` by default.

## Routes

- `GET /api/health`
- `GET /api/models`
- `POST /api/chat`
- `POST /api/chat/stream`

## Privacy Contract

The sidecar is local-first. The initial chat service only talks to the local Ollama runtime at `127.0.0.1:11434`. Database encryption keys are created and read through the OS keychain using `keyring`.

On Windows, the backend depends on `sqlcipher3-wheels` because the official `sqlcipher3-binary` package does not publish Windows wheels. The imported Python module remains `sqlcipher3`.
