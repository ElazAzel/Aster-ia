# Meta-Harness Onboarding: Asterion AI

This file adapts the Meta-Harness onboarding flow to Asterion AI.

Source context loaded:

- `stanford-iris-lab/meta-harness` README: Meta-Harness searches over harness code around a fixed base model and recommends starting from `ONBOARDING.md`.
- `ONBOARDING.md` from that repository: produce `domain_spec.md` only after required fields are filled or explicitly marked unknown.
- arXiv 2603.28052: Meta-Harness optimizes the code that decides what to store, retrieve, and present to a fixed model.

## Running Summary

Task: improve the Asterion AI local-first desktop assistant harness for startup, chat routing, storage, and future retrieval/tool scaffolding.

Harness: every candidate service must implement `BaseHarness.execute()`, `get_state()`, and `set_state()`. The initial services are local-only and use Ollama, SQLCipher, keyring, and structured logs.

Evaluation: Phase 1 evaluates startup-to-first-chat-response latency. The hard target is less than 5 seconds.

Baselines: the current baseline is the static prototype plus `harness/meta_harness.py` mock latency loop. The new baseline is a real FastAPI sidecar contract with source-level checks.

Offline experience: existing artifacts include `BUILD_GUIDE.md`, `asterion_report.html`, Stitch UI prototypes, prior harness scores, and this domain spec.

Online experience: candidate runs should preserve scores in `harness/candidates/<candidate_id>/scores.json` and aggregate results in `eval/results.json`.

Budget: initial requested run is phase 1, 3 iterations. Broader candidate count and held-out sets are unknown.

## Focused Open Question

What should count as a successful held-out evaluation after Phase 1: a real Ollama-backed chat transcript, a scripted multi-step research task, or a full desktop-sidecar boot episode?
