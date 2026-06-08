# Platform Snapshot

Asterion AI is a local-first desktop AI workspace designed for developers, researchers, and privacy-conscious power users. It functions as a secure control room for local LLMs, document vectorization (RAG), deep search, voice notes, automation workflows, and sandboxed execution of agents.

---

## 1. What It Is and Who It Serves

- **Target Audience**: Privacy-conscious developers, researchers, and technical power users.
- **Value Proposition**: A feature-rich AI interface (similar to Claude or Perplexity) that operates 100% locally on user hardware, with clear and visible privacy guardrails (Privacy Radar) and granular consent gates for any action that could leak data.

---

## 2. Current Architecture & Components

The application has transitioned to a unified Rust-based desktop architecture.

```mermaid
flowchart LR
    UI["Svelte 5 UI (Vite)"] -->|"Tauri IPC commands"| Tauri["Tauri v2 Core (Rust)"]
    UI -->|"HTTP / SSE requests (Port 8000)"| Axum["In-Process Axum Server (Rust)"]
    Tauri -->|"Direct call"| Inference["asterion-inference Crate"]
    Axum -->|"Direct call"| Core["asterion-core Crate"]
    Axum -->|"Direct call"| Inference
    Inference -->|"Local Inference"| Ollama["Ollama (llama3.2 & nomic-embed-text)"]
    Core --> SQLCipher["SQLite + SQLCipher (keyring)"]
    Core --> LanceDB["LanceDB (Vector RAG)"]
    Core --> DuckDB["DuckDB (Analytics)"]
    Core --> SearXNG["SearXNG (127.0.0.1:8080)"]
    Core --> ComfyUI["ComfyUI (127.0.0.1:8188)"]
```

### Components Summary

- **Frontend (`/frontend`)**: Svelte 5 / Vite single-page application. Features a three-column Workbench layout (Context panel, Chat composer, right-aligned tabs for plans, logs, and artifacts), Ctrl+K Command Palette, and custom Markdown rendering.
- **Desktop Shell (`/src-tauri`)**: Tauri v2 application written in Rust. Hosts the in-process Axum HTTP server on port 8000, handles native system tray, hardware GPU detection, native file picker dialogs, keyboard hotkeys, and exposes direct model/chat Tauri commands.
- **Backend (`/backend`)**: Legacy FastAPI Python 3.12 application. Houses the original orchestrators, now deprecated/removed from desktop packaging and runtime in Phase 3. Left for testing and parity validation.
- **Core Rust Library (`/crates/core`)**: Implements ported business logic (ModelRouter, PrivacyAnalyzer, BenchmarkService, PluginManager, ContradictionFinder, TaskSimulator).
- **Agent Sandbox**: Subprocess execution isolation. Uses Windows native `ctypes` Job Objects and macOS/Linux `RLIMIT` parameters.

---

## 3. Core Flows

### A. Smart Chat Flow
1. User enters message and hits submit.
2. Svelte UI requests `POST /api/chat/stream` or invokes `chat` Tauri IPC command.
3. `PrivacyAnalyzer` scans content for PII and checks dependencies.
4. `ModelRouter` scores model compatibility based on VRAM/RAM constraints.
5. Axum server / Tauri command orchestrates streams from local Ollama (or vLLM fallback if active) to the UI via Server-Sent Events (SSE) or direct Rust channel.
6. Message is persisted to SQLCipher SQLite; responses generate Adaptive Artifact blocks.

### B. RAG indexing and Search Flow
1. Documents are dragged-and-dropped into Svelte UI or selected via native file dialog.
2. File paths are verified against Approved Folder Scopes.
3. In-process Axum/Rust server reads, chunks, embeds (via Ollama `nomic-embed-text`), and registers vectors in LanceDB.
4. Searches run hybrid dense cosine plus BM25 search.

### C. Deep Research Flow
1. Query received -> decomposed into subtasks by `SupervisorAgent`.
2. Agent searches via local SearXNG instance (`127.0.0.1:8080`).
3. Results are aggregated, structured, and stored in DuckDB.
4. Receipts (quotes, claims, sources) are stored in SQLCipher; contradiction checks are run by `ContradictionFinder`.

---

## 4. Environments & Deployment Flow

- **Local Development**:
  - Frontend: `npm run dev` (Vite, default port 5173)
  - Tauri: `cargo tauri dev` (starts the in-process Axum server and dev console)
  - Docker Profile: `docker compose up --build` (runs backend, frontend, and SearXNG)
- **CI/CD Pipeline** (`.github/workflows/ci.yml`):
  - Automatically runs Python pytest/ruff validation, Rust workspace checks/tests, and frontend build validation on push/PR.
- **Release Pipeline** (`.github/workflows/release.yml`):
  - Compiles the unified Rust Tauri app without PyInstaller python sidecar packaging.

---

## 5. Blast Radius & Risks

| Zone | Potential Impact | Mitigations |
| --- | --- | --- |
| **Data Storage / SQLite** | Loss of chat history, memories, and room configuration. | Key material isolated in OS Keyring; PBKDF2-Fernet encrypted backup and import/export utility. |
| **Agent Sandbox Execution** | Arbitrary code execution leaking files or network packets. | Native Job Objects/RLIMIT caps; AST validation of imports to block `socket`, `subprocess`, and unauthorized path traversals. |
| **Plugin Ecosystem** | Malicious third-party plugins executing high-privilege APIs. | Ed25519 signature checks; automatic trust downgrade to `danger` for unsigned or corrupted manifests. |
| **Web Search & API Models** | Data leaking to external indexers or LLM providers. | Strict Consent Gates; default `web_access=false`; `PrivacyAnalyzer` classifying external routing as red risk. |

---

## 6. Known Issues & Tech Debt

1. **Compilation Toolchain**: Tauri Cargo compilation on Windows requires Visual Studio MSVC Build Tools. If `link.exe` is missing, Cargo builds fail.
2. **LanceDB deletion**: LanceDB vector data deletion needs to be hardened (currently, document references are deleted from SQLite metadata, but raw LanceDB vector blobs are scheduled for future cleanup optimization).
3. **Rust Port Completeness**: Phase 3 is complete. The Python FastAPI sidecar has been completely eliminated from the Tauri runtime in favor of an in-process Rust Axum server and Tauri IPC commands (`list_models`, `chat`, `embed`).
