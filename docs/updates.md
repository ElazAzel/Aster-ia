# Updates

## 2026-06-07

### CI Hermeticity and Public Docs Refresh

- Added local ComfyUI recipe validation with `/api/images/validate`, generation-time `422` rejection for unsafe recipes, default 7-node ComfyUI workflow construction, and tests for external URI, broken node reference, and non-loopback base URL blocking.
- Added a local-first CI secret scanner (`scripts/scan_secrets.py`) with pytest coverage, `make security-scan`, and a dedicated GitHub Actions `security` job to prevent committed provider keys or high-entropy secret assignments.
- Fixed the current `main` CI backend failure by making `test_rag_crud` hermetic: the integration test now mocks `DocumentIndexer.hybrid_search()` instead of reaching real local Ollama embeddings.
- Fixed the `tauri-check` CI blocker by creating a temporary Windows sidecar placeholder before `cargo check`; release builds still use the real PyInstaller sidecar from `.github/workflows/release.yml`.
- Added the missing Tauri desktop icon assets (`icon.ico`, `icon.icns`, and PNG sizes) required by Windows/macOS/Linux bundle metadata.
- Fixed Tauri v2.11 Rust compile errors by enabling the `tray-icon` feature, using `set_focus()`, cloning owned backend process state for spawned tasks, dropping process locks before async health checks, and removing the invalid tray fallback icon constructor.
- Replaced stale README scaffold wording and mojibake-heavy quick start text with the current Power-user MVP feature set, verification commands, Docker dev loop, and Voice Mode notes.
- Updated `docs/roadmap.md` to mark Phase 3 as implemented and split Phase 4 into implemented hardening foundations versus remaining release-grade work.
- Verified locally: `uv run pytest` (76 passed), `uv run ruff check .`, `npm run build`, `npx tsc --noEmit`, and compileall.

## 2026-06-06

### Phase 3 Completion: Voice, Cookbook, Docker, Release Docs

- Added local-first Voice Mode backend: `VoiceService`, `/api/voice/status`, `/api/voice/transcribe`, `/api/voice/meeting`, and `/api/voice/transcribe/text`. The service implements `BaseHarness` and returns a local fallback setup hint when `faster-whisper` is not installed.
- Added Svelte Voice Mode UI with browser microphone recording, local audio upload, transcript display, meeting summary, action items, decisions, and questions.
- Added `ModelCookbook.svelte` with eight Ollama recipes and streaming model pull progress via existing `/api/models/pull`.
- Added `ResearchCanvas.svelte` and `FlightRecorder.svelte` for clearer research artifact and agent log surfaces.
- Added local development infrastructure: `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile.dev`, `Makefile`, `.github/dependabot.yml`, `SECURITY.md`, and `CONTRIBUTING.md`.
- Extended Meta-Harness source contracts to cover Voice Mode, frontend Phase 3 components, and devops/community files.
- Updated API, architecture, and local development docs for Voice Mode and Docker.

## 2026-06-06

### Phase 5: UX/UI Polish and E2E Testing (Block 7)

- **Release Entry Point Repair**: Added `backend/main.py` as a PyInstaller-compatible sidecar entrypoint that delegates to `asterion_api.__main__.main`, fixing the release workflow path expected by `.github/workflows/release.yml`.
- **Reactive Conversation History Sidebar**: Refactored the chat history list from `StreamingChat.svelte` to a dedicated section in the Left Context Panel (`ContextPanel.svelte`) with a reactive full-text search input (filtering by title and localized date). Added conversation renaming (`PATCH`) and cascading deletion (`DELETE`) with toast alerts. Shared state variables (`conversationId`, `conversations`, `conversationSearchQuery`) are synced in a central Svelte store.
- **Drag-and-Drop RAG Vault Indexing**: Integrated a responsive, glassmorphic drag-and-drop zone inside `VaultTab.svelte` that accepts `.pdf`, `.docx`, `.txt`, and `.md` files. Immediately triggers file parsing and vectorization via `uploadVaultFile()` on drop. For desktop Tauri runs, includes a native filesystem path selection input executing `indexLocalVaultFile()`.
- **Toast Alerts & Theme State Synced**: Configured light mode override tokens in `frontend/src/app.css` using CSS custom properties, syncing the theme preference to `localStorage`. Created `ToastContainer.svelte` supplying non-blocking floating alerts for success, warning, and error events.
- **Onboarding Wizard**: Built a step-by-step onboarding walkthrough (`OnboardingWizard.svelte`) checking FastAPI sidecar and local Ollama status, guiding first room creation, and demonstrating keyboard shortcuts, saved to `localStorage` on completion.
- **Command Palette (Ctrl+K / Cmd+K)**: Centered modal supporting command queries (navigating between tabs, selecting agents, switching room contexts, toggling light/dark theme, and triggering database backup/wipe).
- **Custom Markdown Renderers**: Custom regex-based parser with syntax-highlighting for Python, Rust, JavaScript, and shell commands in chat messages without heavy dependencies.
- **Playwright E2E Tests**: Implemented local mocked integration tests covering app shell navigation, theme switches, command palette searches, room context creations, memory inserts, and the onboarding walkthrough. All 4 Playwright E2E tests pass cleanly.
- **Verification**: Clean backend compilation, 65/65 pytest checks pass, 100% Meta-Harness success (40.4ms avg response latency), and Vite build compiles with 0 warnings/errors.

## 2026-06-06

### Phase 4: Security and Privacy Hardening (Block 6)

- **OS-level Process Sandboxing**: Implemented secure subprocess sandboxing. Windows uses native `ctypes` Job Objects restricting memory to 512 MB and process spawning (ActiveProcessLimit = 2). Linux utilizes the `resource` module inside `preexec_fn` (`RLIMIT_AS`, `RLIMIT_CPU`, `RLIMIT_NPROC`).
- **Ed25519 Plugin Signature Verification**: Integrates the `cryptography` library. Validates `manifest.json` against `signature.sig` and `public_key.pem` in plugin directories. Automatically downgrades unsigned elevated plugins to `"danger"` trust level and blocks loading of corrupted plugins.
- **FastAPI CSP & Rate Limiting Middlewares**:
  - Configured strict Content Security Policy allowing connections only to loopback loop (connect-src / img-src for local Ollama, ComfyUI, websockets).
  - Implemented in-memory per-IP rate limiting (120 req/min) returning HTTP 429 when exceeded.
- **Audit Consent Logs**: Implemented database migration `migration_003` to track user consent decisions (approve/deny) on elevated operations.
- **Encrypted Data Backups & Wipe**:
  - Added export/import of all user data encrypted with PBKDF2 (100,000 iterations of SHA-256) and a Fernet (AES-128) cipher.
  - Added a complete system wipe operation removing database files, keyring entries, LanceDB vector collections, and Vault documents.
- **Memory TTL background loop**: Automatic enforcer deleting expired memories in the background every 10 minutes.
- **PII Regex Prompt Scanning**: Scans prompt content for email, international/local phone numbers, and street address keywords. Displays warning badges in Svelte's Privacy Radar.
- **Svelte UI Integration**:
  - Implemented a glassmorphic Privacy Consent Modal overlay in `App.svelte` displaying operation risks and log approvals.
  - Implemented backup export/import panels, OS wipe confirmations, and an Audit Logs table in `SystemTab.svelte`.
- **Verification**: Wrote comprehensive unit and integration tests in `backend/tests/test_security.py`. All 7 test cases passed successfully. Vite production build completes cleanly.

## 2026-06-06

### Phase 2E: API Tests (Block 4) & Phase 3: Desktop Shell Integration (Block 5)

- **API Integration Tests**: Wrote comprehensive integration test suites using `httpx.AsyncClient` + `TestClient` for every major router (Chat, RAG, Memory, Rooms, Workflows, Plugins, Images, Analytics) with mock Ollama setups.
- **DB Migration Tests**: Added test cases verifying database schema upgrades from `v0` (clean) up to current schema version `v2`.
- **Degraded Health Checks**: Tested degraded health-check states when Ollama services are offline, verifying response handling.
- **Coverage**: Exceeded the minimum required coverage threshold by reaching **81%** statement coverage.
- **Tauri Multi-Window Splashscreen**: Implemented a frameless centered splashscreen window loading `index.html?splash=true` while starting the sidecar in the background. Close the splashscreen and focus the main window automatically when the FastAPI server is healthy.
- **Native System Tray**: Built a tray icon in Rust with options to show workspace, restart sidecar, or exit, including a transparent icon fallback.
- **GPU and Hardware Auto-Detection**: Implemented a Rust command to query system video controllers via PowerShell, allowing Svelte to auto-fill optimal model routing parameters.
- **Native File Dialog Picker**: Integrated the `rfd` crate in Rust for local file selection, linking it to the RAG Vault upload panel.
- **Global Hotkeys and Deep Links**: Configured `Ctrl+Shift+Space` global hotkey to toggle workspace visibility, and handled `asterion://` deep links on launch.
- **Ollama Installer helper**: Spawns official Ollama setup downloader from `ollama.com` directly from the Svelte interface.
- **Verification**: Clean backend compilation, 58/58 pytest suites passed, 100% Meta-Harness success, and Svelte production Vite compilation success.

### Phase 2D: Research & Analytics (Block 3)

- **SQLCipher Data Connection**: Added database methods to `EncryptedSQLiteStore` (`get_all_research_receipts()`, `get_all_agent_runs()`, and `get_all_agent_logs()`) to pull raw data with full room and metadata context.
- **DuckDB Real Data Analytics**: Replaced mock endpoints with DuckDB SQL queries over registered Pandas DataFrames loaded from SQLite:
  - `GET /api/analytics/research/stats`: Computes total research queries, sources, and claims.
  - `GET /api/analytics/top-sources`: Lists top 10 consulted sources.
  - `GET /api/analytics/claims-confidence`: Counts claims by confidence level.
  - `GET /api/analytics/rooms-distribution`: Tallies research reports by room.
  - `GET /api/analytics/agent-stats`: Analyzes runs, steps, privacy-levels, and error states.
- **Markdown Export**: Created `GET /api/research/report/{artifact_id}/markdown` supporting download of formatted report artifacts as standard Markdown attachments.
- **Verification**: Clean backend compilation, 39/39 tests passed (including the new integration test suite), Meta-Harness 100% Success.

## 2026-06-06

### Рефакторинг Frontend (Phase 1)

- **Компонентная архитектура**: Монолитный файл `App.svelte` (~1700 строк) разделен на 14 независимых Svelte компонентов (SideRail, TopBar, PrivacyRadar, ContextPanel, Workbench, и 9 компонентов вкладок).
- **Централизованный Стор**: Создан файл `frontend/src/lib/stores.ts`, инкапсулирующий все глобальные реактивные состояния и методы взаимодействия с API / Tauri IPC.
- **Верификация**: Vite build clean (built in 5.72s), pytest clean (38/38 passed), Meta-Harness 100% Success.

## 2026-06-06

### Реализация рекомендаций аудита платформы

- **CI/CD Windows-матрица**: Backend и Harness джобы теперь запускаются на `ubuntu-latest` и `windows-latest`. Добавлен отдельный `tauri-check` джоб с `cargo check` на Windows, Rust-кэшированием.
- **Расширенный Health-check**: `GET /api/health` теперь проверяет доступность Ollama (`is_available`), показывает `schema_version` и количество моделей. Статус `degraded` если Ollama недоступен.
- **Система миграций БД**: Создан `storage/migrations.py` — лёгкая встроенная система миграций с таблицей `schema_migrations`. DDL вынесен из `_ensure_schema_sync` в декларативные миграции. Migration 001 содержит полную текущую схему.
- **Автоуправление моделями Ollama**: Добавлены `OllamaService.ensure_models()`, `pull_model()`, `is_available()`. В `lifespan` добавлен auto-pull обязательных моделей. Новые API-эндпоинты: `POST /api/models/pull` (SSE прогресс), `POST /api/models/ensure`.
- **DuckDB лимиты ресурсов**: Добавлены `Settings.duckdb_memory_limit` (512MB) и `duckdb_threads` (2). Лимиты применяются при каждом подключении в analytics роутере.
- **Обновлён Meta-Harness**: Контракты DDL-схем перенаправлены на `storage/migrations.py`.
- **Верификация**: compileall clean, 38/38 tests pass, Meta-Harness 100% (40.3ms avg latency).

## 2026-06-06

### Phase 4: Chat History, Analytics, Plugin Watcher, Real-time Logs

- **Chat history persistence**: `StreamingChat.svelte` now imports real `listChatConversations`/`listChatMessages` from `api.ts`, with conversation selector (`<select>` + «+ Новый»), `loadHistory()`/`loadMessages()`/`newChat()` functions, and `onMount` auto-load.
- **Analytics router**: Added `GET /api/analytics/research/stats` DuckDB-powered endpoint in `backend/asterion_api/routers/analytics.py`. Registered in `main.py` and `__init__.py`.
- **Analytics Dashboard UI**: Three-metric grid (Исследований, Источников, Утверждений) in System tab with «Обновить» button.
- **Plugin hot-reload watcher**: `PluginManager.start_watcher()`/`stop_watcher()` with background thread polling `plugins_dir` for manifest changes. Added `get_plugin_names()` convenience.
- **Real-time agent log streaming**: `createPlannedAgentRun()` now calls `startAgentRunEvents(runId)` which opens `EventSource` on `GET /api/agents/runs/{run_id}/events` and appends events to `flightLogs`.
- **SSE event source cleanup**: `agentRunEventSource` state variable for proper lifecycle.
- **Verification**: compileall clean, 38/38 tests pass, tsc 0 errors, npm build clean (131.62 kB), meta-harness 100%.

## 2026-06-06

### Phase 3: E2E Integration, UX Polish, Testing & Hardening, New Features

- **SSE streaming for Deep Research**: Added `POST /api/research/deep/stream` endpoint with `subtask_start`, `result_found`, and `done` events. Frontend `streamDeepResearch()` async generator in `api.ts` for progressive UI updates.
- **Keyboard shortcuts**: `Ctrl+1-0` to switch tabs, `Ctrl+K` for next tab, `Esc` to close Privacy Radar. Added shortcuts help panel in System tab.
- **Desktop notifications**: `Notification.requestPermission()` on mount, `notifyUser()` helper for future use.
- **Workflow templates**: 3 presets (Проверка файлов, Ревью кода, Исследование) with dropdown selector in Automation tab.
- **Permission presets**: 4 presets (Минимальные, Чтение файлов, Веб-доступ, Полный доступ) in Agent Lab dropdown.
- **Image rendering**: ComfyUI response now renders `<img>` tag if response contains `images[0]` or `image` field.
- **Error dismissal**: Error banner has a close button (`✕`).
- **Empty states**: Contradiction Finder shows "Противоречия не найдены" when no matches; models selector shows proper fallback.
- **System Prompt Editor**: New localStorage-based textarea in System tab, saved across sessions.
- **CSS cleanup**: Removed orphaned classes (`.artifacts-drawer`, `.chat-history-bar`, `.api-field`, `.primary-grid`, `.right-stack`, `.inline-controls`, `.source-card-grid`, `.glass-panel`, `.chat-layout`). Removed dead `drawerOpen` state.
- **Integration tests**: Expanded from 26 → 38 tests. Added tests for SupervisorAgent (harness, decompose, execute), ContradictionFinder (empty/single claim), WorkflowRunner (empty steps, approval rejection), PluginManager (missing/invalid manifest), AgentSandbox (safe code), TaskSimulator (dangerous task).
- **Removed unused imports**: `getAgentRun`, `PrivacyReport`, `Path`, `AsyncMock`/`MagicMock`/`patch`, `DocumentIndexer` (now properly included in harness check).

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
