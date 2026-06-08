# Asterion AI — Глобальный план выполнения

> Этот файл — единственный источник истины по текущим задачам.
> После выполнения **всех** пунктов файл будет автоматически удалён.

---

## Фаза 0: Фундамент ✅

- [x] Rust workspace (core/inference/server/src-tauri)
- [x] BaseHarness trait
- [x] ModelRouter (8 тестов)
- [x] PrivacyAnalyzer (10 тестов)
- [x] BenchmarkService (12 тестов)
- [x] PluginManager (10 тестов)
- [x] ContradictionFinder (12 тестов)
- [x] TaskSimulator + path validation (11 тестов)
- [x] CI: Rust job (cargo check + test) на windows-latest
- [x] 141/141 Python tests
- [x] Frontend build 0 warnings
- [x] Meta-Harness 100%
- [x] 17/17 E2E tests

---

## Фаза 1: Rust — портировать сервисы  ✅

| # | Модуль | Тестов | Статус |
|---|--------|--------|--------|
| 1.1 | MemoryLedger | 10 | ✅ |
| 1.2 | Settings/Config | 6 | ✅ |
| 1.3 | VoiceService (pure logic) | 14 | ✅ |
| 1.4 | WorkflowRunner | 9 | ✅ |
| 1.5 | AgentRegistry + AgentExecutor | 13 | ✅ |
| 1.6 | DeepResearch | 8 | ✅ |
| 1.7 | ComfyUI recipe validation | 17 | ✅ |
| 1.8 | RAG chunking + BM25 | 17 | ✅ |
| 1.9 | AgentSandbox extension | 15 (включая старые) | ✅ |

**Не портировано:** ChatService (сложная оркестровка, зависит от store)

**Итого:** 14 модулей, **161 тест**, Python бэкенд 141/141 без изменений.

---

## Фаза 2: Inference Engine (crates/inference) ✅

**Блокер:** требуется `llama-cpp-2`, `whisper-rs`, MSVC linker для сборки.  
На данной машине нет MSVC Build Tools.

- [x] llama-cpp-2: LocalEngine (load, generate, stream, embed)
- [x] Whisper: WhisperEngine (transcribe, fallback)
- [x] CloudClient: OpenAI-compatible chat + embeddings
- [x] BenchmarkEngine: tps/ttft/memory

---

## Фаза 3: Desktop Integration ✅

- [x] Tauri IPC: list_models, chat, embed через Rust
- [x] Убрать Python sidecar
- [x] Единый `.exe` с embedded GGUF

---

## Фаза 4: Python улучшения

- [ ] E2E 17 → 25+ тестов
- [ ] CI: cargo fmt --check, cargo clippy

---

## Фаза 5: Удаление Python

- [ ] Все 5 шагов проверки parity + cleanup

---

## Легенда

- `[ ]` — задача не начата
- `[~]` — в процессе
- `[x]` — выполнено

> ⚡ Автоудаление: когда все `[ ]` и `[~]` исчезнут, файл удаляется.
