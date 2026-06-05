# API Reference

Base URL:

```text
http://127.0.0.1:8000
```

## Health

`GET /api/health`

Returns backend status, uptime, database health, and privacy defaults.

## Chat

`POST /api/chat`

```json
{
  "message": "Hello",
  "room_id": "default",
  "model": "llama3.2"
}
```

`POST /api/chat/stream`

Streams Server-Sent Events from a JSON request body.

`GET /api/chat/stream?message=Hello&room_id=default&model=llama3.2`

Browser `EventSource` endpoint.

SSE token event:

```json
{
  "type": "token",
  "conversation_id": "...",
  "model": "llama3.2",
  "response": "token",
  "done": false,
  "privacy_level": "local"
}
```

## Models

`GET /api/models`

Lists Ollama models.

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
    {"what": "model", "destination": "external_api", "risk": "red"}
  ]
}
```

## Memory

`POST /api/memory`

Creates a memory after privacy analysis.

`GET /api/memory/{room_id}`

Lists active memories for a room.

`PATCH /api/memory/{memory_id}`

Updates content, source, or expiration.

`DELETE /api/memory/{memory_id}`

Deletes a memory.

## RAG

`POST /api/rag/index`

```json
{
  "file_path": "C:\\path\\to\\document.md",
  "room_id": "default"
}
```

`POST /api/rag/search`

```json
{
  "query": "architecture",
  "room_id": "default",
  "limit": 8
}
```

## Research

`POST /api/research/deep`

Runs 3-5 research subtasks. With `web_access=false`, returns decomposition without public web search.

`POST /api/research/contradictions`

Compares claims and returns contradiction flags.

## Agents

`GET /api/agents/catalog`

Returns all runtime agents and skills.

`POST /api/agents/simulate`

Returns an `AgentPlan`.

`POST /api/agents/run-code`

Runs Python code in the local sandbox.

## Images

`POST /api/images/generate`

Sends a prompt and recipe to local ComfyUI.

## Workflows

`POST /api/workflows/run`

Executes workflow JSON.

`POST /api/workflows/confirm`

Resumes a paused workflow.

`WS /api/workflows/events`

Streams human approval gate events.

## Plugins

`GET /api/plugins`

Loads plugin manifests from `~/.asterion/plugins`.
