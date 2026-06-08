# Privacy & Security Architecture

Asterion AI is built on a **local-first, privacy-by-design** principle.
Privacy is a UI feature -- not a setting buried in docs.

## Privacy Levels

Every API response includes a `privacy_level` field:

| Level    | Color  | Meaning |
|----------|--------|---------|
| `local`  | Green  | All data stays on your device |
| `hybrid` | Amber  | Metadata or aggregated queries may reach local services (SearXNG) |
| `external` | Red | Data is sent to an external API provider |

## Data Storage

| Store | Encryption | Location |
|-------|-----------|----------|
| SQLite (conversations, memories, artifacts) | AES-256 via SQLCipher, key in OS keychain | `~/.asterion/db/` |
| LanceDB (RAG vector index) | Filesystem-level; no network access | `~/.asterion/lancedb/` |
| Plugin manifests | Ed25519 signature verified before load | `~/.asterion/plugins/` |
| Secrets & API keys | OS keychain only (Keychain/Credential Manager) | Never on disk |

## What Leaves Your Device

**Never (with default settings):**
- Chat messages
- Documents you upload
- Memory entries
- Voice recordings or transcripts
- Agent logs

**Only with explicit user consent (Privacy Consent Modal):**
- Prompts sent to external models (Claude API, OpenAI, etc.)
- Search queries routed through SearXNG (local by default)

## Agent Sandbox

Every agent runs in an isolated subprocess:
- **Windows**: `ctypes` Job Objects -- 512MB memory cap, process limit 2
- **Linux**: `RLIMIT_AS` (512MB), `RLIMIT_CPU` (30s), `RLIMIT_NPROC` (10)
- **macOS**: `RLIMIT_AS`, `RLIMIT_CPU`, `RLIMIT_NOFILE` (64)

File access: agents can only read/write folders you explicitly approve via **RAG Folder Scopes**.

## Plugin Security

1. Plugin directory scanned at startup
2. `manifest.json` validated against `signature.sig` + `public_key.pem`
3. Unsigned plugins with elevated permissions downgraded to `danger` trust level
4. Network/shell plugins shown in UI with warning badge

## PII Detection

Before each prompt, Asterion scans for:
- Email addresses
- Phone numbers (international + local formats)
- Street address keywords

Warnings shown in Privacy Radar -- you decide whether to proceed.

## Audit Trail

All consent decisions and elevated operations are logged to encrypted SQLite.
Export your audit log: **System > Export > scope: audit_logs**.

## Data Wipe

System > Data Management > **Wipe All Data**:
- Deletes SQLite database
- Removes LanceDB collections
- Clears OS keychain entries
- Removes plugin manifests

This is irreversible. Export a backup first.

## Memory TTL

Memories with an expiry date are purged automatically every 10 minutes.
Set retention per Context Room in **Vault > Context Rooms > Settings**.
