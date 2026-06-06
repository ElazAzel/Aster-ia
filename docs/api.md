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
  "artifact_id": "uuid",
  "privacy_level": "local",
  "ts": "2026-06-06T00:00:00Z"
}
```

Assistant responses are persisted twice:

- as plain chat messages in SQLCipher for history reload;
- as `chat` artifacts with block-level `text` and `code` records.

### Chat History

`GET /api/chat/conversations`

`GET /api/chat/conversations?room_id=default`

Returns conversation metadata:

```json
[
  {
    "id": "uuid",
    "room_id": "default",
    "created_at": "2026-06-06T00:00:00Z",
    "message_count": 2,
    "latest_ts": "2026-06-06T00:00:02Z"
  }
]
```

`GET /api/chat/conversations/{conversation_id}/messages`

Returns ordered messages. Assistant messages include `artifact_id` when an Adaptive Artifact was created from the response.

### Streaming Chat

`POST /api/chat/stream`

Streams `text/event-stream` from a JSON body.

`GET /api/chat/stream?message=Привет&room_id=default&model=llama3.2`

Browser-friendly `EventSource` endpoint.

Optional `conversation_id` keeps subsequent messages inside the same conversation:

```text
GET /api/chat/stream?message=Next&room_id=default&conversation_id=uuid&model=llama3.2
```

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

Final event payload includes `artifact_id` after the assistant response has been saved.

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

## Voice

`GET /api/voice/status`

Returns the local voice engine state:

```json
{
  "ok": true,
  "privacy_level": "local",
  "engine": "faster-whisper",
  "whisper_available": true,
  "model_name": "base",
  "device": "cpu",
  "supported_formats": [".flac", ".m4a", ".mp3", ".ogg", ".wav", ".webm"],
  "note": "Transcription runs locally when faster-whisper is installed."
}
```

`POST /api/voice/transcribe`

Multipart form fields:

- `file`: `.mp3`, `.wav`, `.m4a`, `.webm`, `.ogg`, or `.flac`
- `mode`: `note` or `meeting`
- `language`: optional language hint such as `ru` or `en`
- `diarize`: optional boolean; diarization is currently reported as unavailable

Response:

```json
{
  "text": "transcript",
  "segments": [
    {
      "start": 0.0,
      "end": 2.4,
      "text": "transcript segment"
    }
  ],
  "language": "ru",
  "duration": 12.5,
  "privacy_level": "local",
  "engine": "faster-whisper"
}
```

When `faster-whisper` is not installed, the endpoint remains local and returns
`engine=fallback` plus a setup hint instead of calling an external transcription API.

`POST /api/voice/transcribe/text`

Multipart form fields:

- `text`: transcript or voice note text
- `mode`: `notes` or `meeting`

Returns structured `summary`, `action_items`, `decisions`, `questions`, and markdown.

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

## Context Rooms

`GET /api/rooms`

Lists room-scoped context policies.

`POST /api/rooms`

```json
{
  "name": "Research Room",
  "color": "#2f80ed",
  "allowed_models": ["llama3.2"],
  "memory_policy": "session",
  "retention_days": 30
}
```

`GET /api/rooms/{room_id}`

`PATCH /api/rooms/{room_id}`

`DELETE /api/rooms/{room_id}`

The default room cannot be deleted.

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

Vault document metadata:

- `GET /api/rag/documents`
- `GET /api/rag/documents?room_id=default`
- `DELETE /api/rag/documents/{document_id}`

Deleting a document record removes metadata from SQLCipher. LanceDB vector deletion is a later hardening step.

## Artifacts

`POST /api/artifacts`

```json
{
  "room_id": "default",
  "kind": "chat",
  "title": "Answer",
  "source": "chat",
  "blocks": [
    {
      "type": "text",
      "title": "Summary",
      "content": "Local-first response"
    }
  ]
}
```

`GET /api/artifacts/{artifact_id}`

Artifacts support block types: `text`, `code`, `table`, `source`, and `action`.

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

`POST /api/research/report/export`

Creates a `research_report` artifact and stores Research Receipts.

```json
{
  "room_id": "default",
  "query": "Compare local and API routing",
  "title": "Research Receipt",
  "receipts": [
    {
      "source_title": "Local note",
      "url": null,
      "quote": "Local routing reduces exposure.",
      "claim": "Local routing reduces external data exposure.",
      "confidence": "medium"
    }
  ]
}
```

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
  "skills_count": 20,
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

Agent runs and Flight Recorder:

- `POST /api/agents/runs`
- `GET /api/agents/runs/{run_id}`
- `GET /api/agents/runs/{run_id}/logs`
- `GET /api/agents/runs/{run_id}/events`

`POST /api/agents/runs` creates a planned run and writes the initial `plan.created` Flight Recorder event.

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
