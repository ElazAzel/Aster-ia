# Privacy and Security

Asterion AI is local-first by default.

User prompts, local files, memories, embeddings, generated artifacts, and chat history must stay on the user's machine unless the user explicitly approves an elevated route.

## Default Posture

Allowed local operations:

- Ollama chat and embeddings
- SQLCipher conversation storage
- LanceDB indexing and search
- DuckDB aggregation
- localhost ComfyUI generation
- local plugin manifest discovery

Gated operations:

- memory writes
- file indexing
- SearXNG web research
- API model fallback
- plugin execution
- sandbox network/shell/file-write permissions
- external model/search/image services

## Privacy Radar

`PrivacyAnalyzer` returns:

```json
{
  "level": "green",
  "items": [
    {
      "what": "model",
      "destination": "local_ollama",
      "risk": "green"
    }
  ]
}
```

Levels:

- `green`: local-only, low risk.
- `yellow`: local persistence, attached local data, memory write, or user-awareness gate.
- `red`: external API destination, public web access, elevated plugin, shell/network sandbox capability, or unknown trust.

Every item must include:

- `what`
- `destination`
- `risk`

## Consent Gates

| Operation | Default | Required gate |
| --- | --- | --- |
| Local Ollama chat | allow | none |
| Local embedding | allow | none |
| SQLCipher message storage | allow | none |
| Memory creation | gate | Privacy Radar, user intent |
| Attached file indexing | gate | file approval |
| Broad folder indexing | block | explicit folder approval |
| SearXNG search | gate | web access approval |
| API model fallback | block | external model approval |
| Plugin `verified` | gate if it writes/runs | operation approval |
| Plugin `network` | block | network plugin approval |
| Plugin `file` | block | file plugin approval |
| Plugin `shell` | block | shell plugin approval |
| Plugin `danger` or unknown | block | explicit danger approval |
| Sandbox network | block | network approval |
| Sandbox shell | block | shell approval |
| External image generation | block | external image approval |

## Local Image Generation Guardrails

ComfyUI remains a local-only surface. The image API exposes `POST /api/images/validate` and runs the same validator before `POST /api/images/generate`.

The validator blocks:

- non-local ComfyUI base URLs;
- external URI inputs such as `http://`, `https://`, `ftp://`, `s3://`, and `file://`;
- absolute local paths and path traversal in workflow strings;
- download/network-oriented node class names;
- missing node references and oversized workflows;
- `SaveImage.filename_prefix` values that attempt to write into subdirectories.

## Secrets

Production secrets must not be stored in:

- `.env`
- source code
- docs
- manifests
- logs
- fixtures
- UI prototypes

SQLCipher keys:

- generated locally
- stored through OS keychain with `keyring`
- never logged
- never committed

Repository checks:

- CI runs `python scripts/scan_secrets.py .` on every push and pull request.
- Local release verification runs the same scanner through `make security-scan` and `make verify`.
- The scanner flags high-confidence provider keys and suspicious secret assignments while allowing explicit placeholder/test values.

## Storage

Main storage:

- SQLite with SQLCipher
- schema managed by `EncryptedSQLiteStore`
- key material from OS keychain

Tables:

```text
conversations(id, room_id, created_at)
messages(id, conv_id, role, content, model, ts)
memories(id, room_id, content, source, created_at, expires_at)
```

Memory rules:

- Create requires privacy analysis.
- Red risk blocks create.
- Source must be recorded.
- Expired memories are not returned as active room memory.
- Memory records are room-scoped.

## Agent Permissions

Every agent manifest declares:

```json
{
  "permissions": {
    "allowed_folders": [],
    "network": false,
    "shell": false
  }
}
```

Rules:

- `network=false` means sandbox code must reject network libraries.
- `shell=false` means sandbox code must reject shell/process execution.
- Empty `allowed_folders` means no broad file access.
- Local agents cannot silently enable network or shell.
- Handoff targets must be declared in manifests.

## Plugin Trust Levels

Supported trust levels:

- `verified`
- `local-only`
- `network`
- `file`
- `shell`
- `danger`

Unknown trust levels are treated as `danger`.

Plugin manifests are loaded from:

```text
~/.asterion/plugins/
```

Execution policy:

- discovery is local
- execution is gated by trust level
- network/file/shell/danger require explicit approval
- secrets in plugin manifests are forbidden

## Structured Logs

Structured logs must include:

- `ts`
- `action`
- `tool`
- `privacy_level`
- `error`

Do not log:

- raw prompts unless the user has enabled debug export
- memory contents
- SQLCipher keys
- API keys
- plugin secrets
- full local file contents

## Security Acceptance Checks

Before release:

```powershell
uv run python -m compileall backend\asterion_api harness\meta_harness.py
uv run python harness/meta_harness.py --phase 1 --iterations 3
uv run python scripts\scan_secrets.py .
```

Also verify:

- `GET /api/agents/catalog/validate` returns `ok=true`.
- `POST /api/privacy/analyze` returns red for API model usage.
- Memory creation runs privacy analysis first.
- Sandbox rejects network imports when `network=false`.
- Sandbox rejects shell execution when `shell=false`.
- Unknown plugin trust levels are classified as `danger`.
- `scripts/scan_secrets.py` reports no likely production secrets.
