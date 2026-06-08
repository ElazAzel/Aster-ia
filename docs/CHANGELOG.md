# Changelog

All notable changes to Asterion AI will be documented in this file.

---

## [0.6.0] - 2026-06-07

### Added
- Completed Rust Migration Phase 3: Integrated direct Tauri IPC commands `list_models`, `chat`, and `embed` into the desktop shell.
- Implemented a lightweight in-process Axum HTTP server in Rust (port 8000) inside the Tauri runtime to emulate all FastAPI REST and SSE endpoints for Svelte compatibility.
- Created `docs/ADR/0001-in-process-rust-axum-server.md` detailing the in-process server architecture decision.

### Changed
- Eliminated Python FastAPI sidecar binary packaging and runtime execution from Tauri configuration.
- Removed unused `tauri-plugin-shell` dependency and related capability permissions.
- Streamlined GitHub Actions release (`release.yml`) and integration (`ci.yml`) workflows to eliminate obsolete PyInstaller backend packaging and placeholder copying.

## [0.5.0] - 2026-06-07

### Added
- Completed Rust Migration Phase 1: Ported `ModelRouter`, `PrivacyAnalyzer`, `BenchmarkService`, `PluginManager`, `ContradictionFinder`, and `TaskSimulator` to Rust.
- Wrote 63 Rust unit tests covering all ported services.
- Created `docs/PLATFORM_SNAPSHOT.md` tracking the system architecture, component dependencies, environments, and blast radius.

### Changed
- Configured CI workflow to run merged workspace checks for Rust crates on `windows-latest`.
