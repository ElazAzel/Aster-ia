# API Reference

Base URL:

```text
http://127.0.0.1:8000
```

All backend IO boundaries are async. External destinations are disabled by default unless the user explicitly approves them.

## Health

`GET /api/health`

Returns sidecar status, uptime, encrypted database health, and privacy defaults.

Important fields:

- `status`: `ok` or `degraded`
- `database.encrypted`: expected `true` when SQLCipher is active
- `privacy.local_first`: expected `true`

## Chat

`POST /api/chat`

```json
{
  "message": "Привет",
  "room_id": "default",
  "conversation_id": null,
  "model": "llama3.2",
  "files_attached": false,
  "memory_enabled": false,
  "web_access": false
}
```

Response:

```json
{
  "conversation_id": "uuid",
  "room_id": "default",
  "model": "llama3.2",
  "response": "...",
  "latency_ms": 1200.0,
  "privacy_level": "local",
  "ts": "2026-06-06T00:00:00Z"
}
```

### Streaming Chat

`POST /api/chat/stream`

Streams `text/event-stream` from a JSON body.

`GET /api/chat/stream?message=Привет&room_id=default&model=llama3.2`

Browser-friendly `EventSource` endpoint.

Token event payload:

```json
{
  "type": "token",
  "conversation_id": "uuid",
  "model": "llama3.2",
  "response": "token",
  "done": false,
  "privacy_level": "local"
}
```

Final event has `done=true`.

## Models

`GET /api/models`

Lists models available in local Ollama.

`POST /api/models/select`

```json
{
  "task_description": "coding assistant",
  "hw_profile": {
    "vram_gb": 8,
    "ram_gb": 32,
    "gpu_name": "RTX"
  }
}
```

Response:

```json
{
  "model": "llama3.2",
  "mode": "local",
  "reason": "VRAM satisfies local model requirement."
}
```

If `mode=api`, Privacy Radar must treat the route as red until approved.

## Privacy

`POST /api/privacy/analyze`

```json
{
  "model_type": "api",
  "files_attached": true,
  "memory_enabled": true,
  "web_access": true
}
```

Response:

```json
{
  "level": "red",
  "items": [
    {
      "what": "model",
      "destination": "external_api",
      "risk": "red"
    }
  ]
}
```

Risk levels:

- `green`: local-only.
- `yellow`: local persistence or user-awareness gate.
- `red`: external destination or elevated capability.

## Memory

`POST /api/memory`

Creates a memory only after privacy analysis.

```json
{
  "room_id": "default",
  "content": "User prefers local models.",
  "source": "manual",
  "expires_at": null,
  "privacy": {
    "model_type": "local",
    "files_attached": false,
    "memory_enabled": true,
    "web_access": false
  }
}
```

`GET /api/memory/{room_id}` lists active, non-expired memories.

`PATCH /api/memory/{memory_id}` updates content, source, or expiration.

`DELETE /api/memory/{memory_id}` deletes a memory.

## RAG

`POST /api/rag/index`

```json
{
  "file_path": "C:\\Users\\user\\Documents\\note.md",
  "room_id": "default"
}
```

The indexer parses local files, chunks text, embeds with `nomic-embed-text` through Ollama, and upserts to LanceDB.

`POST /api/rag/search`

```json
{
  "query": "architecture",
  "room_id": "default",
  "limit": 8
}
```

Search combines dense cosine scoring with BM25.

## Research

`POST /api/research/deep`

```json
{
  "query": "Compare local-first AI workspace risks",
  "max_subtasks": 5,
  "web_access": true
}
```

Runs 3-5 subtasks through local SearXNG on `127.0.0.1:8080` and aggregates results in DuckDB.

With `web_access=false`, the agent returns decomposition and privacy state without public search calls.

`POST /api/research/contradictions`

```json
{
  "claims": [
    "Local memory storage is safe",
    "Local memory storage is unsafe"
  ],
  "threshold": 0.85
}
```

Returns pairs that are semantically similar and have opposing sentiment.

## Agents

`GET /api/agents/catalog`

Returns:

```json
{
  "agents": [],
  "skills": []
}
```

`GET /api/agents/catalog/validate`

Returns:

```json
{
  "ok": true,
  "agents_count": 10,
  "skills_count": 16,
  "errors": [],
  "warnings": []
}
```

Other catalog endpoints:

- `GET /api/agents/catalog/agents`
- `GET /api/agents/catalog/skills`
- `GET /api/agents/catalog/agents/{agent_id}`

Task simulation:

`POST /api/agents/simulate`

```json
{
  "task": "Index the selected PDF and summarize contradictions"
}
```

Sandboxed code:

`POST /api/agents/run-code`

```json
{
  "code": "print('ok')",
  "permissions": {
    "allowed_folders": [],
    "network": false,
    "shell": false
  }
}
```

## Images

`POST /api/images/generate`

```json
{
  "prompt": "local product mockup",
  "recipe": {
    "width": 1024,
    "height": 1024
  }
}
```

Uses local ComfyUI on `127.0.0.1:8188`.

## Workflows

`POST /api/workflows/run`

Executes workflow JSON sequentially.

`POST /api/workflows/confirm`

Resumes a paused approval gate.

`WS /api/workflows/events`

Streams human approval gate events to the UI.

## Plugins

`GET /api/plugins`

Loads plugin manifests from `~/.asterion/plugins`.

Supported trust levels:

- `verified`
- `local-only`
- `network`
- `file`
- `shell`
- `danger`

Unknown trust levels are treated as `danger`.
