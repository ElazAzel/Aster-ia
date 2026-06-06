# Updates

## 2026-06-06

### Полная верификация: все компоненты запущены и работают

- **Backend (FastAPI)**: Запущен на `127.0.0.1:8000`. Health endpoint — `status: ok`, база SQLCipher — `encrypted: true`. Все 47 роутов зарегистрированы.
- **Ollama**: `llama3.2` (2.0 GB) и `nomic-embed-text` (274 MB) загружены. Chat endpoint работает (33s latency при первой загрузке, ответ осмысленный).
- **Privacy Radar**: `POST /api/privacy/analyze` корректно возвращает `red` для API-модели, `green` для локальной.
- **Agent Registry**: 10 агентов, 20 скиллов, 0 ошибок, 0 предупреждений.
- **Frontend**: `npm run build` — чистая сборка (0 ошибок, 0 warnings). Dev-сервер Vite на `5173`.
- **Tauri**: Rust 1.96.0, cargo check требует MSVC linker (`link.exe`). Добавлен `x86_64-pc-windows-gnu` target как fallback.
- **Meta-Harness**: 100% прохождение (60/60 контрактов, 40.4ms avg latency).
- **Dependencies**: DuckDB 1.5.3, LanceDB 0.33.0, httpx 0.28.1, sqlcipher3 — все импортируются без ошибок.

### UX/UI Редизайн: Трехколоночный Workbench + Умный ввод

- **Трехколоночный интерфейс Workbench**: Левая панель (контекстные комнаты + Memory Ledger), центр (чат), правая панель Workbench с вкладками (План, Логи, Артефакты). Все три колонки можно сворачивать через кнопки в шапке.
- **Умные команды `/` и контекст `@`**: В поле ввода чата интегрирован выпадающий список автозаполнения. `/` открывает команды (`/simulate`, `/search`, `/privacy`, `/clear`), `@` — выбор комнаты или модели. Навигация стрелками, выбор Enter/Tab, закрытие Escape.
- **Workbench**: Правая панель с тремя вкладками. Вкладка «План» содержит Agent Lab. Вкладка «Логи» показывает Flight Recorder. Вкладка «Артефакты» отображает экспортированные Research Receipts и AgentPlan. Автоматическое переключение при генерации артефактов.
- **Source Cards (Perplexity-style)**: Микро-карточки источников с иконками и ссылками, рендерятся в сообщениях ассистента через `[source:title](url)`.
- **Стиль "Wow"**: Фоновые светящиеся градиентные сферы (mesh gradients), `backdrop-filter` для плавающих элементов, анимированные индикаторы стриминга (три пульсирующие точки), плавные анимации появления сообщений.
- **Левая панель контекста**: Список комнат с цветовыми индикаторами, быстрый выбор модели, Memory Ledger с добавлением/удалением записей.
- Created interactive autocomplete (slasher/mention) popover in the chat composer with keyboard navigation.
- Refactored sliding drawer into the right-aligned Workbench panel with three tabs (Plan, Logs, Artifacts).
- Verified: `npm run build` clean, Meta-Harness 100% pass (40.4ms avg latency).

- Проведен полный UX/UI аудит и редизайн интерфейса: монолитный дашборд переработан во фреймворк с вкладками (Чат, Агенты, База знаний, Исследования, Настройки системы).
- Стилизован «Умный чат» по аналогии с Claude: сообщения выровнены по центру, добавлена плавающая строка ввода с автовысотой, кнопки управления генерацией и встроенный markdown-парсер с кнопками быстрого копирования кода.
- Реализована интерактивная выдвижная панель «Артефакты» (artifacts-drawer) для отображения симуляций задач и логов Flight Recorder во время выполнения агентов.
- Встроен интерактивный всплывающий попап радара приватности (Privacy Radar) прямо в панель управления чатом.
- Структурирован раздел «База знаний» на удобные подвкладки для управления комнатами контекста, Ledger-памятью и Vault RAG-документами.
- Обновлена цветовая схема в `app.css` — внедрена премиальная темная тема с использованием шрифтов Outfit и JetBrains Mono, эффектами глассморфизма и плавными анимациями переходов.
- Успешно пройдена верификация мета-тестов (Meta-Harness) со 100% успехом проверок.
- Added Chat History API with `GET /api/chat/conversations` and `GET /api/chat/conversations/{conversation_id}/messages`.
- Linked assistant messages to Adaptive Artifacts through `messages.artifact_id`; chat responses now create block artifacts before final SSE `done`.
- Updated the Svelte streaming chat component with conversation reload, conversation continuity, new-chat reset, and visible artifact receipts.
- Added MVP backend contracts for Context Rooms, Adaptive Artifacts, Research Receipts, AgentRun persistence, and Flight Recorder logs.
- Added `GET/POST/PATCH/DELETE /api/rooms`, `POST/GET /api/artifacts`, `GET/DELETE /api/rag/documents`, `POST /api/research/report/export`, and AgentRun log/event endpoints.
- Added Svelte UI controls for Context Rooms, Vault document metadata, Research Receipt export, and AgentRun/Flight Recorder preview.
- Added runtime skill manifests for `context-rooms`, `adaptive-artifacts`, `research-receipts`, and `flight-recorder`.
- Added `docs/product-mvp-plan.md` and `docs/launch-kit.md` for product design and creative-production launch planning.
- Expanded runtime agent catalog from 6 to 10 agents with `chat-orchestrator`, `model-curator`, `memory-curator`, and `plugin-auditor`.
- Expanded runtime skill catalog from 12 to 16 skills with `conversation-orchestration`, `ollama-operations`, `sqlcipher-storage`, and `agent-catalog-governance`.
- Added manifest lifecycle metadata: `triggers`, `lifecycle`, `outputs`, `handoff_targets`, `acceptance_checks`, `requires_consent`, and `failure_modes`.
- Added `AgentRegistry.validate_catalog()` to detect malformed manifests, duplicate ids, unknown skill references, and unknown handoff targets.
- Added `GET /api/agents/catalog/validate` for UI and release checks.
- Reworked docs for architecture, API, local development, privacy/security, roadmap, and agents/skills to match the current runtime catalog.
- Verified catalog locally with `ok=true`, 10 agents, 16 skills, and no warnings.
- Added a runnable Svelte/Vite frontend shell in `frontend/` with live SSE chat, Privacy Radar, Model Router, Agent Catalog, Memory Ledger, RAG search, and Task Simulator panels.
- Connected Tauri configuration to `frontend/dist` and added a Svelte Tauri IPC bridge for starting, health-checking, and stopping the FastAPI sidecar.

## 2026-06-05

- Added Phase 1 Asterion AI FastAPI sidecar scaffold with `/api/health`, `/api/models`, `/api/chat`, and `/api/chat/stream`.
- Added async `OllamaService` with `list_models()`, `generate()`, and `stream_generate()`.
- Added SQLCipher-oriented encrypted SQLite store using `sqlcipher3`/`sqlcipher3-binary` and OS keychain secrets through `keyring`.
- Added Windows-compatible SQLCipher dependency resolution through `sqlcipher3-wheels`, while preserving the `sqlcipher3` import path.
- Added `BaseHarness` contract and implemented it in storage, Ollama, and chat services.
- Added Tauri v2 sidecar lifecycle commands: `start_fastapi_sidecar`, `fastapi_health_check`, and `shutdown_fastapi_sidecar`.
- Added local Meta-Harness onboarding notes and `domain_spec.md` for Asterion AI.
- Verified `uv run python harness/meta_harness.py --phase 1 --iterations 3` with 100% source/UI contracts and average mock chat latency below 5 seconds.
- Added real SSE streaming chat endpoint for browser `EventSource` and a Svelte `StreamingChat` component.
- Added `PrivacyAnalyzer`, `ModelRouter`, Memory Ledger CRUD API, LanceDB RAG indexing/search, Deep Research via local SearXNG, contradiction detection, agent sandbox/task simulation, ComfyUI bridge, workflow runner, and plugin manifest loader.
- Pulled local Ollama models `llama3.2` and `nomic-embed-text` for chat and embeddings smoke checks.
- Added root `README.md`, repository `AGENTS.md`, architecture/API/local-dev/privacy/roadmap docs, runtime agent manifests, runtime skill manifests, and `AgentRegistry` catalog API.
