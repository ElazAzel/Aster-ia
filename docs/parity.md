# Python ↔ Rust Parity Status

> Фаза 5 — документирование паритета между Python (production runtime) и Rust (pure logic core).

## Легенда

| Статус | Значение |
|--------|----------|
| ✅ FULL | Rust покрывает 100% public API, та же логика, те же результаты |
| 🟡 PARTIAL | Rust покрывает вычислительное ядро, но нет IO/DB/async |
| ❌ NONE | Rust не имеет реализации |

## Общие пробелы Rust (cross-cutting)

Все Rust-сервисы разделяют эти ограничения — они будут закрыты в Фазах 2-3:

1. **Sync vs async** — Rust синхронный, Python асинхронный (IO, HTTP, subprocess)
2. **Нет DB persistence** — Rust in-memory, Python использует `EncryptedSQLiteStore`
3. **Нет HTTP-вызовов** — Rust не вызывает Ollama, SearXNG, ComfyUI
4. **`set_state()` no-op** — Rust не мутирует состояние
5. **`execute()` частичный** — возвращает `Value::Null` для IO-действий
6. **Нет StructuredLogger** — Rust без структурированного логирования

## Детальный паритет

### PrivacyAnalyzer ✅ FULL

| Аспект | Python | Rust |
|--------|--------|------|
| `analyze(model_type, files, memory, web, prompt)` | ✅ | ✅ идентичная логика |
| PII-сканеры (email, phone, address) | ✅ | ✅ те же regex |
| Уровни риска (green/yellow/red) | ✅ | ✅ |
| `execute()` через harness | ✅ | ✅ |
| `get_state()` / `set_state()` | ✅ | ✅ |
| **Тесты** | 5 | 7 |

### ModelRouter ✅ FULL

| Аспект | Python | Rust |
|--------|--------|------|
| 17 моделей в каталоге | ✅ | ✅ |
| `select(task, hw)` — алгоритм | ✅ | ✅ идентичная скоринг-функция |
| Task routing (code/russian/research/...) | ✅ | ✅ |
| API fallback при нехватке VRAM | ✅ | ✅ |
| `execute()` / `get_state()` / `set_state()` | ✅ | ✅ |
| **Тесты** | 3 | 8 |

### ChatService 🟡 PARTIAL

| Аспект | Python | Rust |
|--------|--------|------|
| `generate()` — создание conv + ответ | ✅ | ✅ (через closure `model_fn`) |
| CRUD conversation | ✅ | ✅ in-memory |
| `response_blocks()` — code fence parsing | ✅ | ✅ |
| `build_history()` | ✅ | ✅ |
| Streaming (SSE) | ✅ async | ❌ нет |
| `_provider_for()` routing Ollama/vLLM | ✅ | ❌ нет |
| `_persist_response_artifact()` | ✅ | ❌ нет |
| DB-backed storage | ✅ SQLite | ❌ in-memory only |
| **Тесты** | 4 | 22 |

### VoiceService 🟡 PARTIAL

| Аспект | Python | Rust |
|--------|--------|------|
| `transcribe()` — аудио → текст | ✅ async | ❌ отсутствует |
| `analyze_meeting()` | ✅ dict + str | 🟡 только str |
| `to_markdown()` | ✅ | 🟡 баг в заголовке |
| `status()` — engine detection | ✅ динамический | ❌ hardcoded fallback |
| Sentence splitting | ✅ regex | 🟡 посимвольно, менее точный |
| `execute()` / `get_state()` | ✅ | 🟡 `set_state()` no-op |
| **Тесты** | 7 | 14 |

### MemoryLedger 🟡 PARTIAL

| Аспект | Python | Rust |
|--------|--------|------|
| `create()` + privacy check | ✅ SQLite | ✅ in-memory |
| `list_by_room()` | ✅ | ✅ newest-first |
| `delete()` | ✅ | ✅ |
| `search()` | ✅ | ✅ basic contains |
| `expire()` | ✅ | ✅ |
| `get()` / `update()` | ✅ SQLite | ❌ нет |
| **Тесты** | 3 | 9 |

### AgentRegistry 🟡 PARTIAL

| Аспект | Python | Rust |
|--------|--------|------|
| `list_agents()` / `list_skills()` | ✅ filesystem scan | ❌ только pre-loaded |
| `validate_catalog()` | ✅ | ✅ идентичная логика |
| TTL caching (30s) | ✅ | ❌ нет |
| `get_state()` | ✅ dirs | 🟡 counts |
| `set_state()` | ✅ | ❌ no-op |
| **Тесты** | 0 | 8 |

### AgentSandbox 🟡 PARTIAL

| Аспект | Python | Rust |
|--------|--------|------|
| `validate_code()` | ✅ AST-based | ❌ contains() — легко обходится |
| OS-level sandboxing | ✅ Job Objects / RLIMIT | ❌ нет |
| `file_read()` / `file_write()` | ✅ | ❌ нет |
| Syntax validation | ✅ | ❌ нет |
| Dangerous builtins (exec/eval) | ✅ blocked | ❌ не проверяются |
| **Тесты** | 17 | 6 |

### RAG (DocumentIndexer) 🟡 PARTIAL

| Аспект | Python | Rust |
|--------|--------|------|
| `chunk()` — алгоритм | ✅ 1200/160 | ✅ идентичный |
| BM25 / cosine / hybrid | ✅ | ✅ идентичный |
| File parsing (PDF, DOCX) | ✅ | ❌ нет |
| LanceDB persistence | ✅ | ❌ in-memory |
| File watching | ✅ | ❌ нет |
| Embedding | ✅ async /api/embed | 🟡 legacy /api/embeddings |
| `index` action | ✅ | ❌ только search |
| **Тесты** | 7 | 12 |

### ContradictionFinder 🟡 PARTIAL

| Аспект | Python | Rust |
|--------|--------|------|
| `cosine()` | ✅ | ✅ идентичный |
| `sentiment()` | ✅ negation+stem+RU+score | ❌ упрощённый: last-match-wins |
| Ollama embed integration | ✅ | ❌ нет |
| Word lists | ✅ 15+8 pos/neg RU+EN | 🟡 8+8 только EN |
| **Тесты** | 5 | 12 |

### BenchmarkService 🟡 PARTIAL

| Аспект | Python | Rust |
|--------|--------|------|
| `estimate_vram()` | ✅ | ✅ идентичный |
| `stddev()` | ✅ | ✅ Bessel correction |
| Caching with TTL | ✅ | ✅ |
| `run()` — HTTP to Ollama | ✅ async | ❌ нет |
| **Тесты** | 3 | 11 |

### PluginManager 🟡 PARTIAL

| Аспект | Python | Rust |
|--------|--------|------|
| Trust levels | ✅ | ✅ |
| `compute_trust_level()` | ✅ | 🟡 семантические отличия |
| Filesystem scanning | ✅ | ❌ нет |
| Crypto verification (Ed25519/RSA) | ✅ | ❌ нет |
| **Тесты** | 4 | 9 |

### WorkflowRunner 🟡 PARTIAL

| Аспект | Python | Rust |
|--------|--------|------|
| Human approval step | ✅ async Future | ✅ sync Mutex |
| `tool_call` / `code_exec` / `condition` | ✅ | ❌ нет |
| DB persistence | ✅ | ❌ in-memory |
| Structured logging | ✅ | ❌ нет |
| **Тесты** | 4 | 9 |

### DeepResearch 🟡 PARTIAL

| Аспект | Python | Rust |
|--------|--------|------|
| `decompose()` — 5 aspects | ✅ | ✅ идентичный |
| `research()` — SearXNG calls | ✅ parallel async | 🟡 sequential sync |
| Privacy analyzer integration | ✅ | ❌ `privacy=None` |
| DuckDB aggregation | ✅ | ❌ нет |
| **Тесты** | 4 | 8 |

### ComfyUIService 🟡 PARTIAL

| Аспект | Python | Rust |
|--------|--------|------|
| `validate_recipe()` | ✅ | ✅ идентичный |
| `build_recipe()` | ✅ | ✅ |
| `default_workflow()` | ✅ 7-node SDXL | ✅ идентичный |
| `normalize_base_url()` | ✅ | ✅ |
| `generate()` — HTTP to ComfyUI | ✅ async | ❌ нет |
| Preset metadata (description, tags) | ✅ | ❌ нет |
| **Тесты** | 6 | 16 |

## Итого

| Метрика | Значение |
|---------|----------|
| FULL parity | 2 / 14 (PrivacyAnalyzer, ModelRouter) |
| PARTIAL parity | 12 / 14 |
| Python тестов (портированная логика) | ~60 из 141 |
| Rust тестов | 184 |
| Python тестов для непортированного | ~81 (Store, Ollama, vLLM, endpoints) |
| Зависимостей Python для удаления | `pylance` (опечатка/мёртвый пакет) |
