# Privacy and Security

## Default Posture

Asterion AI is local-first.

Local execution is preferred for:

- chat
- embeddings
- file indexing
- memory
- workflows
- image generation
- plugin discovery

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

Risk levels:

- `green`: local-only, low risk.
- `yellow`: local persistence, web search through local gateway, or sensitive operation needing user awareness.
- `red`: external API destination or high-risk network path.

## Secrets

Production secrets must not be stored in:

- `.env`
- source code
- docs
- manifests
- logs
- fixtures

SQLCipher keys are generated and retrieved through `keyring`.

## Storage

Main storage:

- SQLCipher SQLite
- schema managed by `EncryptedSQLiteStore`
- key material in OS keychain

Memory records:

```text
memories(id, room_id, content, source, created_at, expires_at)
```

## Agent Permissions

Agents must declare:

- allowed folders
- network access
- shell access

The sandbox rejects network libraries when `network=false` and shell calls when `shell=false`.

## Plugin Trust Levels

Allowed trust levels:

- `verified`
- `local-only`
- `network`
- `file`
- `shell`
- `danger`

Unknown trust levels are treated as `danger`.

## External Access

External model APIs, public web search, network plugins, and external image services require explicit user approval before execution.
