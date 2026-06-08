# ADR 0001: In-Process Rust Axum Server for Desktop Integration

## Status
Approved

## Context
As part of Phase 3 (Desktop Integration), we aim to compile Asterion AI into a unified desktop binary without packaging a heavy external Python FastAPI sidecar. 

However, the Svelte frontend contains over 22 distinct REST/SSE fetch endpoints interacting with rooms, memory ledger, catalog validation, RAG scopes, image generation, and chat token streaming. Completely rewriting all of these Svelte endpoints to use Tauri IPC commands would:
1. Increase code churn and introducted regression risks in the UI.
2. Break compatibility with standard web-based deployment configurations (like Docker).
3. Require rewriting the client-side server-sent event (SSE) listeners to custom Tauri event channels.

## Decision
We decided to initialize a lightweight, in-process Axum HTTP server running in a background Tokio thread within the Tauri app shell on `127.0.0.1:8000`. 

This in-process server mocks and implements the key REST and SSE endpoints needed by the frontend, routing them directly to the compiled Rust crates `crates/core` and `crates/inference`.

Additionally, we exposed direct `list_models`, `chat`, and `embed` Tauri IPC commands as alternative entrypoints for direct desktop bindings.

## Consequences
- **Zero Frontend Code Churn**: Svelte app communicates with the in-process server exactly as it did with the Python backend.
- **Improved Performance**: Eliminates sidecar process startup latency and inter-process communication overhead.
- **Enhanced Security**: Eliminates Tauri shell spawning capabilities, aligning with least-privilege desktop security principles.
- **Simplified Releases**: Tauri release builds no longer require a PyInstaller environment to package external binaries.
