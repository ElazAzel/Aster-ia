# Rust Migration Plan — Asterion AI

## Why Rust?

| Проблема | Сейчас (Python + Ollama) | Цель (Rust native) |
|---|---|---|
| **One-click install** | Нужен Python 3.12, uv, Ollama, Docker SearXNG | Единый `.exe` / `.dmg` / `.AppImage` |
| **Зависимости** | 5+ внешних процессов | Один процесс, zero external deps |
| **Производительность** | IPC через HTTP localhost | In-process вызовы через FFI |
| **Масштабирование** | Только desktop | Desktop + Cloud + Enterprise Self-hosted |
| **Инвестпривлекательность** | "Сборка open-source запчастей" | "Собственный inference engine + платформа" |

## Архитектура

```
asterion/
├── Cargo.toml                       # workspace root
├── crates/
│   ├── core/                        # ✅ Phase 1 — бизнес-логика
│   │   ├── ModelRouter (ported)
│   │   ├── Schemas (HardwareProfile, ModelSelection)
│   │   └── BaseHarness trait
│   ├── inference/                   # ⏳ Phase 2 — LLM движок
│   │   ├── LocalEngine (llama-cpp-2)
│   │   ├── CloudClient (OpenAI-compatible)
│   │   └── WhisperEngine (whisper-rs)
│   ├── rag/                         # 🔲 Phase 3 — RAG + embeddings
│   │   ├── lancedb-rs wrapper
│   │   └── nomic-embed-text FFI
│   ├── server/                      # 🔲 Phase 4 — облачный сервер
│   │   ├── axum routes (22 endpoints)
│   │   ├── JWT auth
│   │   ├── Multi-tenant rate limiting
│   │   └── Stripe billing
│   └── desktop/                     # 🔲 Phase 5 — Tauri desktop (replace src-tauri)
│       └── Tauri v2 app with embedded core
├── src-tauri/                       # Текущий Tauri (работает до Phase 5)
└── backend/                         # Текущий Python-бэкенд (работает до Phase 3)
```

## Phases

### Phase 1 — Core (Текущая) ✅

**Что сделано:**
- Workspace structure с `Cargo.toml` root + 3 crates
- `crates/core` — ModelRouter (16 моделей, tag routing, score-based selection)
- `BaseHarness` trait mirroring Python interface
- `Schemas` (HardwareProfile, ModelSelection, BenchmarkResult)
- 7 unit tests (select, fallback, multi-lingual, zero-VRAM, harness execute, privacy)
- Компилируется (`cargo check -p asterion-core`)

**Что даёт бизнесу (инвесторам):**
> "Мы уже не зависим от Python для core-логики. ModelRouter работает на Rust — это первый шаг к полному отказу от Python-бэкенда."

### Phase 2 — Inference Engine (2-3 недели)

**Замена:** `OllamaService` + `VllmService` + `VoiceService`

```
crates/inference/
├── engine.rs          # InferenceEngine trait
├── local.rs           # llama-cpp-2 (CUDA/Metal/Vulkan/CPU)
├── cloud.rs           # OpenAI-compatible client (для cloud tier)
├── embedding.rs       # nomic-embed-text / custom embedding model
└── whisper.rs         # whisper-rs STT
```

**Ключевое решение:** Используем `llama-cpp-2` crate — Rust-обёртку над llama.cpp. Это:
- Поддержка GGUF (все модели Ollama совместимы)
- GPU inference (CUDA, Metal, Vulkan)
- CPU fallback с mmap
- **Zero external dependencies — один `.exe` покрывает чат, RAG, агентов**

**Результат для инвестора:**
> "Мы владеем собственным LLM-движком. Никакого Ollama. Модели под капотом."

### Phase 3 — RAG + Embeddings (2-3 недели)

**Замена:** `DocumentIndexer` + LanceDB Python SDK

```
crates/rag/
├── indexer.rs         # LanceDB native client
├── chunker.rs         # Text chunking (Python reimplementation)
├── embedding.rs       # nomic-embed-text via llama-cpp-2
└── bm25.rs            # BM25 scoring
```

**Результат:**
> "Векторный поиск, индексация, BM25 — всё в одном процессе. Pinecone не нужен."

### Phase 4 — Cloud Server (3-4 недели)

**Новое:** `crates/server` — axum-based HTTP сервер

```
crates/server/
├── main.rs            # axum app
├── routes/            # Все 22 эндпоинта (из Python)
│   ├── chat.rs
│   ├── models.rs
│   ├── benchmark.rs
│   └── ...
├── auth/
│   ├── jwt.rs
│   └── tier.rs
├── billing/
│   ├── stripe.rs
│   └── metering.rs
└── middleware/
    ├── rate_limit.rs
    └── privacy.rs
```

**Масштабирование:**
- `axum` stateless — горизонтальное масштабирование через load balancer
- Redis queue для GPU-задач
- K8s + NVIDIA GPU Operator для кластера
- Stripe metered billing по токенам

**Результат для инвестора:**
> "Desktop и Cloud — один код. Клиент платит $0 за local, $20/мес за cloud, Enterprise — self-hosted."

### Phase 5 — Desktop Replacement (1-2 недели)

**Замена:** `src-tauri` (Python sidecar)

```
crates/desktop/
├── main.rs            # Tauri v2 entry
└── commands/          # IPC команды (вместо Python sidecar)
    ├── chat.rs
    ├── models.rs
    └── system.rs
```

- Вместо запуска Python sidecar — direct in-process вызовы `asterion-core`
- `llama-cpp-2` грузит модель в том же процессе
- Никаких HTTP-прокси, zero latency overhead

## Бизнес-модель

| Продукт | Технология | Цена | Маржа |
|---|---|---|---|
| **Desktop (Free)** | `asterion-core` + `inference` (3B-8B) | $0 | ∞ |
| **Desktop Pro** | + Cloud models, + Code RAG, + Priority support | $20/мес | 70%+ |
| **Enterprise** | Self-hosted `asterion-server` + SLA | $1000/мес | 90%+ |
| **GPU Marketplace** | Pay-per-token for 70B+ models | $0.50/1M токенов | 50%+ |

## График

```
Месяц 1  ████████████████░░░░░░░░░░░░  Phase 1 (core) + Phase 2 (inference)
Месяц 2  ░░░░░░░░░██▓███████████████  Phase 3 (RAG) + Phase 4 (server start)
Месяц 3  ░░░░░░░░░░░░░░░░████████████  Phase 4 (server billing) + Phase 5 (desktop)
Месяц 4  ░░░░░░░░░░░░░░░░░░░░░░░█████  MVP cloud + beta
```

## Что делаем прямо сейчас

**Phase 1 готова.** Следующий шаг — Phase 2:

1. Добавить `llama-cpp-2` в `crates/inference/Cargo.toml` и реализовать `LocalEngine`
2. Создать единый `InferenceRequest`/`InferenceResponse` формат
3. Написать интеграционные тесты с реальной моделью (3B)
4. Встроить `LocalEngine` в Tauri через `crates/desktop` IPC

## Конкурентное преимущество после миграции

| | Asterion AI (после) | Cursor | ChatGPT Pro | LM Studio |
|---|---|---|---|---|
| **Local-first** | ✅ Встроенный движок | ❌ | ❌ | ✅ llama.cpp |
| **Свой engine** | ✅ Rust + llama-cpp-2 | ❌ OpenAI | ❌ OpenAI | ✅ |
| **Cloud опционально** | ✅ $0 → $20/мес | ✅ $20/мес | ✅ $20/мес | ❌ |
| **Enterprise self-hosted** | ✅ | ❌ | ❌ | ❌ |
| **Privacy** | ✅ Полный контроль | ❌ Код уходит | ❌ Данные уходят | ✅ |
| **Один бинарник** | ✅ (через 4 месяца) | ✅ | ❌ | ✅ |
