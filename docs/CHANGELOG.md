# Changelog

All notable changes to Asterion AI will be documented in this file.

---

## [0.5.0] - 2026-06-07

### Added
- Completed Rust Migration Phase 1: Ported `ModelRouter`, `PrivacyAnalyzer`, `BenchmarkService`, `PluginManager`, `ContradictionFinder`, and `TaskSimulator` to Rust.
- Wrote 63 Rust unit tests covering all ported services.
- Created `docs/PLATFORM_SNAPSHOT.md` tracking the system architecture, component dependencies, environments, and blast radius.

### Changed
- Configured CI workflow to run merged workspace checks for Rust crates on `windows-latest`.
