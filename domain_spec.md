# Domain Spec: Asterion AI Meta-Harness

## Domain Summary

Asterion AI is a local-first desktop AI workspace. The first optimization target is the backend harness around a fixed local model runtime: startup, model discovery, chat generation, encrypted persistence, and sidecar lifecycle.

Unit of evaluation: one application boot episode ending with the first successful chat response.

Fixed components:

- Tauri v2 desktop shell.
- FastAPI sidecar API.
- Ollama as the MVP model runtime.
- SQLite with SQLCipher for encrypted local storage.
- OS keychain for encryption key material.

Allowed changes:

- Harness/service code that controls context construction, routing, storage, logging, and tool orchestration.
- Meta-Harness evaluation scripts and candidate metadata.

Out of scope for the first pass:

- Changing base model weights.
- Adding external API calls without explicit user consent.
- Replacing SQLCipher/keyring with plaintext production storage.

Frozen base model: unknown exact Ollama model. Proposed default: `llama3.2`.

Optimization budget: initial requested loop is 3 phase-1 iterations. Longer candidate count, wall-clock budget, and held-out set size are unknown.

## Harness and Search Plan

Every candidate service implements:

```python
class BaseHarness:
    privacy_level: Literal["local", "hybrid", "external"]

    async def execute(self, payload: Mapping[str, Any] | None = None) -> Any: ...
    def get_state(self) -> dict[str, Any]: ...
    def set_state(self, state: Mapping[str, Any]) -> None: ...
```

Initial reusable helpers:

- `StructuredLogger` for JSON event logging.
- `OllamaService` for async model discovery and generation.
- `EncryptedSQLiteStore` for SQLCipher-backed conversation persistence.
- `ChatService` for end-to-end user/assistant message orchestration.

Initial baselines:

- Mock harness latency loop in `harness/meta_harness.py`.
- Source-contract checks for FastAPI routes, Ollama methods, SQLCipher/keyring usage, and Tauri commands.

## Evaluation Plan

Search-set evaluation:

- Run `uv run python harness/meta_harness.py --phase 1 --iterations 3`.
- Verify required UI prototype patterns still exist in `index.html`.
- Verify backend and Tauri source contracts exist.
- Measure mock startup-to-first-chat latency for 3 iterations.

Held-out evaluation: unknown. Proposed default is a separate scripted boot episode that launches the FastAPI sidecar, verifies `/api/health`, sends one `/api/chat` prompt to a known local Ollama model, and asserts success within 5 seconds on warm hardware.

Primary metric:

- Time from startup to first successful chat response must be less than 5 seconds.

Secondary metrics:

- Privacy score.
- Contract completeness.
- Timeout/error rate.
- DB encryption availability.
- Candidate reproducibility.

Noise and leakage:

- Current phase uses a mock latency loop and source checks, so it is low noise but not a full runtime benchmark.
- Future held-out chat episodes must not reuse exact prompts from search candidates.

## Experience and Logging

Store per-candidate artifacts under:

- `harness/candidates/candidate_<id>/scores.json`
- `harness/candidates/candidate_<id>/trace.jsonl` for future real traces

Aggregate runs under:

- `eval/results.json`

High-signal debug artifacts:

- FastAPI structured logs.
- Sidecar stdout/stderr events emitted by Tauri.
- Health-check response payloads.
- Chat request/response timings.
- SQLCipher/keyring initialization errors without secret values.

## Open Questions and Unknowns

- Exact default Ollama model: unknown, proposed `llama3.2`.
- Held-out benchmark size: unknown.
- Candidate count after the initial 3-iteration phase: unknown.
- Whether vLLM should be part of the first harness search surface: unknown, proposed no.
- Whether future evaluations should include RAG/LanceDB: unknown, proposed no for Phase 1.
