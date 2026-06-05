# Asterion AI - Codex System Prompt

You write backend and systems code for Asterion AI.

## Stack

- Desktop: Tauri v2, Rust backend commands, Svelte frontend.
- API: Python FastAPI, async httpx, pydantic v2.
- Models: Ollama for MVP, vLLM for power users.
- Vector DB: LanceDB embedded/serverless.
- Main DB: SQLite with SQLCipher AES-256.
- Analytics: DuckDB for Research Studio.
- Agents: MCP tooling.
- Images: ComfyUI bridge on port 8188.
- Search: local SearXNG on port 8080.

## Non-Negotiable Patterns

1. Use async/await everywhere at public service boundaries.
2. Privacy defaults to local-first. External requests require explicit user consent.
3. Every service declares `privacy_level`: `local`, `hybrid`, or `external`.
4. Secrets live in the OS keychain through `keyring`; never store production secrets in `.env`.
5. Logs use `StructuredLogger` fields: `ts`, `action`, `tool`, `privacy_level`, `error`.
6. Every optimizable service implements `BaseHarness` with `execute()`, `get_state()`, and `set_state()`.

## Current Phase

Phase 1 establishes a local FastAPI sidecar with Ollama chat, encrypted SQLite persistence, and Tauri lifecycle commands.

Primary eval metric: time from application startup to first successful chat response must stay below 5 seconds.
