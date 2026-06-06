<script lang="ts">
  import { onMount } from 'svelte';
  import {
    DEFAULT_API_BASE,
    analyzePrivacy,
    createAgentRun,
    createMemory,
    createRoom,
    deleteMemory,
    deleteRagDocument,
    exportResearchReport,
    getAgentCatalog,
    getHealth,
    getModels,
    listAgentRunLogs,
    listMemories,
    listRagDocuments,
    listRooms,
    searchRag,
    selectModel,
    simulateAgentTask,
    validateAgentCatalog,
    type AgentCatalog,
    type AgentManifest,
    type AgentPlan,
    type AgentRun,
    type CatalogValidation,
    type ContextRoom,
    type FlightRecorderEvent,
    type HealthResponse,
    type MemoryRecord,
    type ModelInfo,
    type ModelSelection,
    type PrivacyReport,
    type RagChunk,
    type RagDocumentRecord,
    type ResearchReportExportResponse,
    type RiskLevel
  } from './lib/api';
  import StreamingChat from './lib/StreamingChat.svelte';
  import {
    fastapiHealthCheck,
    isTauriRuntime,
    shutdownFastapiSidecar,
    startFastapiSidecar,
    type BackendStatus
  } from './lib/tauri';

  let apiBase = DEFAULT_API_BASE;
  let roomId = 'default';
  let selectedModel = 'llama3.2';
  let taskDescription = 'local coding assistant';
  let vramGb = 8;
  let ramGb = 32;

  let health: HealthResponse | null = null;
  let models: ModelInfo[] = [];
  let privacyReport: PrivacyReport | null = null;
  let modelSelection: ModelSelection | null = null;
  let catalog: AgentCatalog | null = null;
  let catalogValidation: CatalogValidation | null = null;
  let selectedAgentId = 'chat-orchestrator';
  let rooms: ContextRoom[] = [];
  let roomDraft = '';
  let memories: MemoryRecord[] = [];
  let memoryDraft = '';
  let ragDocuments: RagDocumentRecord[] = [];
  let ragQuery = '';
  let ragResults: RagChunk[] = [];
  let researchQuery = 'Сравнить приватность локального и API маршрута';
  let researchSourceTitle = 'Manual source';
  let researchClaim = 'Local-first routing reduces external data exposure.';
  let exportedReport: ResearchReportExportResponse | null = null;
  let agentTask = 'Проверить локальный документ и найти противоречия';
  let agentPlan: AgentPlan | null = null;
  let agentRun: AgentRun | null = null;
  let flightLogs: FlightRecorderEvent[] = [];
  let desktopStatus: BackendStatus | null = null;
  let desktopAvailable = false;
  let statusText = 'Ожидание проверки';
  let busy = false;
  let errorText = '';

  // Tab routing states
  let activeTab = 'chat'; // 'chat' | 'agents' | 'vault' | 'research' | 'system'
  let activeVaultTab = 'memory'; // 'memory' | 'rag' | 'rooms'
  let privacyPopoverOpen = false;
  let drawerOpen = false;

  // Three-column workbench state
  let showLeftPanel = true;
  let showRightPanel = true;
  let activeWorkbenchTab: 'logs' | 'plan' | 'artifacts' = 'plan';

  $: workbenchLayoutClass = showLeftPanel && showRightPanel
    ? 'layout-default'
    : showLeftPanel && !showRightPanel
      ? 'layout-left-only'
      : !showLeftPanel && showRightPanel
        ? 'layout-right-only'
        : 'layout-full-chat';

  let privacyInput = {
    model_type: 'local' as 'local' | 'api',
    files_attached: false,
    memory_enabled: false,
    web_access: false
  };

  $: selectedAgent = catalog?.agents.find((agent) => agent.id === selectedAgentId) ?? catalog?.agents[0] ?? null;
  $: localAgents = catalog?.agents.filter((agent) => agent.privacy_level === 'local') ?? [];
  $: hybridAgents = catalog?.agents.filter((agent) => agent.privacy_level === 'hybrid') ?? [];
  $: externalAgents = catalog?.agents.filter((agent) => agent.privacy_level === 'external') ?? [];

  function riskLabel(level: RiskLevel | undefined) {
    if (level === 'green') return 'Локально (Безопасно)';
    if (level === 'yellow') return 'Внимание (Гибридный)';
    if (level === 'red') return 'Предупреждение (Внешний)';
    return 'Нет данных';
  }

  function formatUptime(seconds: number | undefined) {
    if (seconds === undefined) return 'нет данных';
    if (seconds < 60) return `${seconds.toFixed(0)} сек`;
    return `${(seconds / 60).toFixed(1)} мин`;
  }

  async function runStep<T>(label: string, action: () => Promise<T>): Promise<T | null> {
    try {
      statusText = label;
      errorText = '';
      return await action();
    } catch (error) {
      errorText = error instanceof Error ? error.message : String(error);
      return null;
    }
  }

  async function refreshHealth() {
    const result = await runStep('Проверяю sidecar', () => getHealth(apiBase));
    if (result) health = result;
  }

  async function startDesktopBackend() {
    const result = await runStep('Запускаю FastAPI sidecar через Tauri', () => startFastapiSidecar());
    if (result) {
      desktopStatus = result;
      apiBase = `http://${result.host}:${result.port}`;
      if (result.health && typeof result.health === 'object') {
        health = result.health as HealthResponse;
      }
    }
  }

  async function checkDesktopBackend() {
    const result = await runStep('Проверяю sidecar через Tauri IPC', () => fastapiHealthCheck());
    if (result) {
      desktopStatus = result;
      apiBase = `http://${result.host}:${result.port}`;
      if (result.health && typeof result.health === 'object') {
        health = result.health as HealthResponse;
      }
    }
  }

  async function stopDesktopBackend() {
    const result = await runStep('Останавливаю FastAPI sidecar', () => shutdownFastapiSidecar());
    if (result) desktopStatus = result;
  }

  async function refreshModels() {
    const result = await runStep('Читаю модели Ollama', () => getModels(apiBase));
    if (result) {
      models = result.models;
      if (!models.some((model) => model.name === selectedModel) && models[0]) {
        selectedModel = models[0].name;
      }
    }
  }

  async function refreshCatalog() {
    const [catalogResult, validationResult] = await Promise.all([
      runStep('Загружаю каталог агентов', () => getAgentCatalog(apiBase)),
      runStep('Проверяю каталог', () => validateAgentCatalog(apiBase))
    ]);
    if (catalogResult) catalog = catalogResult;
    if (validationResult) catalogValidation = validationResult;
  }

  async function refreshRooms() {
    const result = await runStep('Читаю Context Rooms', () => listRooms(apiBase));
    if (result) {
      rooms = result;
      if (!rooms.some((room) => room.id === roomId) && rooms[0]) {
        roomId = rooms[0].id;
      }
    }
  }

  async function refreshMemories() {
    const result = await runStep('Читаю память комнаты', () => listMemories(apiBase, roomId));
    if (result) memories = result;
  }

  async function refreshRagDocuments() {
    const result = await runStep('Читаю Vault документы', () => listRagDocuments(apiBase, roomId));
    if (result) ragDocuments = result;
  }

  async function refreshAll() {
    busy = true;
    await Promise.allSettled([
      refreshHealth(),
      refreshModels(),
      refreshCatalog(),
      refreshRooms(),
      refreshMemories(),
      refreshRagDocuments(),
      analyzeCurrentPrivacy()
    ]);
    statusText = 'Готово';
    busy = false;
  }

  async function analyzeCurrentPrivacy() {
    const result = await runStep('Считаю Privacy Radar', () => analyzePrivacy(apiBase, privacyInput));
    if (result) privacyReport = result;
  }

  async function routeModel() {
    const result = await runStep('Выбираю модель', () => selectModel(apiBase, taskDescription, vramGb, ramGb));
    if (result) {
      modelSelection = result;
      selectedModel = result.model;
      privacyInput.model_type = result.mode === 'api' ? 'api' : 'local';
      await analyzeCurrentPrivacy();
    }
  }

  async function addMemory() {
    const content = memoryDraft.trim();
    if (!content) return;
    const result = await runStep('Добавляю память', () => createMemory(apiBase, roomId, content));
    if (result) {
      memoryDraft = '';
      await refreshMemories();
      privacyInput.memory_enabled = true;
      await analyzeCurrentPrivacy();
    }
  }

  async function addRoom() {
    const name = roomDraft.trim();
    if (!name) return;
    const result = await runStep('Создаю Context Room', () => createRoom(apiBase, name));
    if (result) {
      roomDraft = '';
      roomId = result.id;
      await refreshRooms();
      await refreshMemories();
      await refreshRagDocuments();
    }
  }

  async function removeMemory(memoryId: string) {
    const result = await runStep('Удаляю память', () => deleteMemory(apiBase, memoryId));
    if (result) await refreshMemories();
  }

  async function runRagSearch() {
    const query = ragQuery.trim();
    if (!query) return;
    const result = await runStep('Ищу в RAG', () => searchRag(apiBase, roomId, query));
    if (result) ragResults = result;
  }

  async function removeRagDocument(documentId: string) {
    const result = await runStep('Удаляю запись Vault', () => deleteRagDocument(apiBase, documentId));
    if (result) await refreshRagDocuments();
  }

  async function exportResearchArtifact() {
    const query = researchQuery.trim();
    const claim = researchClaim.trim();
    if (!query || !claim) return;
    const result = await runStep('Экспортирую Research Receipt', () =>
      exportResearchReport(apiBase, {
        room_id: roomId,
        query,
        title: 'Research Receipt',
        receipts: [
          {
            source_title: researchSourceTitle.trim() || 'Manual source',
            claim,
            quote: claim,
            confidence: 'medium'
          }
        ]
      })
    );
    if (result) {
      exportedReport = result;
      activeWorkbenchTab = 'artifacts';
      showRightPanel = true;
    }
  }

  async function simulatePlan() {
    const task = agentTask.trim();
    if (!task) return;
    const result = await runStep('Генерирую AgentPlan', () => simulateAgentTask(apiBase, task));
    if (result) {
      agentPlan = result;
      activeWorkbenchTab = 'plan';
      showRightPanel = true;
    }
  }

  async function createPlannedAgentRun() {
    const task = agentTask.trim();
    if (!task) return;
    const result = await runStep('Создаю AgentRun', () =>
      createAgentRun(apiBase, {
        agent_id: selectedAgent?.id ?? selectedAgentId,
        room_id: roomId,
        task,
        plan: agentPlan,
        permissions: {
          allowed_folders: [],
          network: false,
          shell: false
        }
      })
    );
    if (result) {
      agentRun = result;
      activeWorkbenchTab = 'logs';
      showRightPanel = true;
      const logs = await runStep('Читаю Flight Recorder', () => listAgentRunLogs(apiBase, result.id));
      if (logs) flightLogs = logs;
    }
  }

  function agentGroupTitle(agent: AgentManifest) {
    if (agent.privacy_level === 'hybrid') return 'hybrid';
    if (agent.privacy_level === 'external') return 'external';
    return 'local';
  }

  onMount(() => {
    desktopAvailable = isTauriRuntime();
    void refreshAll();
  });
</script>

<svelte:head>
  <title>Asterion AI Workspace</title>
</svelte:head>

<div class="app-shell">
  <!-- Background mesh gradient glow spheres -->
  <div class="bg-gradient-glow">
    <div class="glow-sphere-3"></div>
  </div>

  <!-- Left Navigation Rail -->
  <aside class="side-rail" aria-label="Навигация Asterion">
    <div class="brand">
      <span class="brand-mark">A</span>
      <div>
        <strong>Asterion AI</strong>
        <small>Локальный AI Воркспейс</small>
      </div>
    </div>

    <nav>
      <button class:active={activeTab === 'chat'} on:click={() => activeTab = 'chat'}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
        <span>Умный Чат</span>
      </button>
      <button class:active={activeTab === 'agents'} on:click={() => activeTab = 'agents'}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
        <span>Агенты и Навыки</span>
      </button>
      <button class:active={activeTab === 'vault'} on:click={() => activeTab = 'vault'}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"></path><path d="M2 17l10 5 10-5"></path><path d="M2 12l10 5 10-5"></path></svg>
        <span>База Знаний (Vault)</span>
      </button>
      <button class:active={activeTab === 'research'} on:click={() => activeTab = 'research'}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 3a3 3 0 0 0-3 3v12a3 3 0 0 0 3 3 3 3 0 0 0 3-3V6a3 3 0 0 0-3-3z"></path><path d="M9 3a3 3 0 0 0-3 3v12a3 3 0 0 0 3 3 3 3 0 0 0 3-3V6a3 3 0 0 0-3-3z"></path><path d="M9 18H3a3 3 0 0 0-3 3 3 3 0 0 0 3-3V6a3 3 0 0 0 3 3h3"></path></svg>
        <span>Исследования</span>
      </button>
      <button class:active={activeTab === 'system'} on:click={() => activeTab = 'system'}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
        <span>Система</span>
      </button>
    </nav>

    <div class="system-meter">
      <span class:ok={health?.status === 'ok'} class:warn={health?.status !== 'ok'} class="status-dot"></span>
      <div>
        <strong>Sidecar: {health?.status ?? 'offline'}</strong>
        <small>аптайм {formatUptime(health?.uptime_seconds)}</small>
      </div>
    </div>
  </aside>

  <!-- Workspace Canvas -->
  <main class="workspace">
    <!-- Common Header -->
    <header class="topbar">
      <div>
        {#if activeTab === 'chat'}
          <p class="eyebrow">Окружение диалога</p>
          <h1>Интерактивный чат</h1>
        {:else if activeTab === 'agents'}
          <p class="eyebrow">Манифесты процессов</p>
          <h1>Каталог Агентов</h1>
        {:else if activeTab === 'vault'}
          <p class="eyebrow">Органайзер контекста</p>
          <h1>Хранилище знаний</h1>
        {:else if activeTab === 'research'}
          <p class="eyebrow">Верификация источников</p>
          <h1>Журнал исследований</h1>
        {:else if activeTab === 'system'}
          <p class="eyebrow">Аппаратный роутинг</p>
          <h1>Консоль конфигураций</h1>
        {/if}
      </div>

      <div class="top-controls">
        {#if activeTab === 'chat'}
          <!-- Panel toggle buttons -->
          <div class="panel-toggle-group">
            <button
              type="button"
              class="panel-toggle-btn"
              class:active={showLeftPanel}
              on:click={() => showLeftPanel = !showLeftPanel}
              title="Показать/скрыть боковую панель"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="3" x2="9" y2="21"/></svg>
              <span>Контекст</span>
            </button>
            <button
              type="button"
              class="panel-toggle-btn"
              class:active={showRightPanel}
              on:click={() => showRightPanel = !showRightPanel}
              title="Показать/скрыть Workbench"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="15" y1="3" x2="15" y2="21"/></svg>
              <span>Workbench</span>
            </button>
          </div>

          <!-- Privacy Radar Interactive Popover -->
          <div class="privacy-popover-trigger">
            <button
              type="button"
              class="privacy-badge-compact"
              on:click={() => privacyPopoverOpen = !privacyPopoverOpen}
            >
              <span class="status-dot ok"></span>
              <span>Безопасность</span>
            </button>

            <div class="privacy-popover" class:visible={privacyPopoverOpen}>
              <div class="panel-heading compact">
                <h2>Радар конфиденциальности</h2>
                <span class={`risk-pill ${privacyReport?.level ? `risk-${privacyReport.level}` : ''}`}>
                  {riskLabel(privacyReport?.level)}
                </span>
              </div>
              <div class="toggle-grid">
                <label>
                  <span>API модель</span>
                  <input
                    type="checkbox"
                    checked={privacyInput.model_type === 'api'}
                    on:change={(event) => {
                      privacyInput.model_type = event.currentTarget.checked ? 'api' : 'local';
                      void analyzeCurrentPrivacy();
                    }}
                  />
                </label>
                <label>
                  <span>Файлы</span>
                  <input
                    type="checkbox"
                    bind:checked={privacyInput.files_attached}
                    on:change={() => void analyzeCurrentPrivacy()}
                  />
                </label>
                <label>
                  <span>Память</span>
                  <input
                    type="checkbox"
                    bind:checked={privacyInput.memory_enabled}
                    on:change={() => void analyzeCurrentPrivacy()}
                  />
                </label>
                <label>
                  <span>Веб</span>
                  <input
                    type="checkbox"
                    bind:checked={privacyInput.web_access}
                    on:change={() => void analyzeCurrentPrivacy()}
                  />
                </label>
              </div>
              <ul class="risk-list">
                {#each privacyReport?.items ?? [] as item}
                  <li>
                    <span class={`status-dot risk-${item.risk}`}></span>
                    <strong>{item.what}</strong>
                    <small>{item.destination}</small>
                  </li>
                {:else}
                  <p class="empty" style="text-align: center; margin-top: 8px;">Нет активных рисков.</p>
                {/each}
              </ul>
            </div>
          </div>
        {/if}

        <button type="button" class="secondary" style="min-height: 32px; padding: 0 12px; margin-left: 8px;" on:click={refreshAll} disabled={busy}>
          {busy ? 'Проверка...' : 'Обновить'}
        </button>
      </div>
    </header>

    <!-- Error notice -->
    {#if errorText}
      <p class="notice error">{errorText}</p>
    {:else if statusText && statusText !== 'Готово'}
      <p class="notice">{statusText}</p>
    {/if}

    <!-- Tab Contents -->
    {#if activeTab === 'chat'}
      <!-- Three-column Workbench Layout -->
      <div class="workbench-layout {workbenchLayoutClass}">
        <!-- Left Panel — Context Rooms & Memory Ledger -->
        <aside class="left-panel" class:hidden={!showLeftPanel} aria-label="Контекст и память">
          <div class="left-panel-header">
            <h2>Контекст</h2>
          </div>

          <!-- Room Selector -->
          <div class="left-panel-section" style="border-bottom: 1px solid var(--border-color);">
            <h3>Комнаты</h3>
            <div class="room-list">
              {#each rooms as room}
                <button
                  type="button"
                  class="room-item"
                  class:active={roomId === room.id}
                  on:click={() => {
                    roomId = room.id;
                    void refreshMemories();
                    void refreshRagDocuments();
                  }}
                >
                  <span
                    class="room-color-dot"
                    style="background: {room.color ?? '#7c6dfa'};"
                  ></span>
                  <span class="room-name">{room.name}</span>
                </button>
              {:else}
                <p class="empty" style="padding: 8px 10px; font-size: 12px;">Комнаты не найдены</p>
              {/each}
            </div>
            <div class="left-panel-input-row">
              <input
                bind:value={roomDraft}
                placeholder="Название..."
                on:keydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); void addRoom(); } }}
              />
              <button type="button" disabled={!roomDraft.trim()} on:click={addRoom}>+</button>
            </div>
          </div>

          <!-- Model Selector -->
          <div class="left-panel-section" style="border-bottom: 1px solid var(--border-color);">
            <h3>Модель</h3>
            <select style="font-size: 12px; padding: 6px 10px;" bind:value={selectedModel}>
              {#if models.length === 0}
                <option value={selectedModel}>{selectedModel}</option>
              {:else}
                {#each models as model}
                  <option value={model.name}>{model.name}</option>
                {/each}
              {/if}
            </select>
          </div>

          <!-- Memory Ledger -->
          <div class="left-panel-section" style="flex: 1; overflow: hidden; display: flex; flex-direction: column;">
            <h3>Память (Ledger)</h3>
            <div class="left-panel-input-row">
              <input
                bind:value={memoryDraft}
                placeholder="Запомнить..."
                on:keydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); void addMemory(); } }}
              />
              <button type="button" disabled={!memoryDraft.trim()} on:click={addMemory}>+</button>
            </div>
            <div class="memory-ledger">
              {#each memories as memory}
                <div class="memory-card">
                  <p>{memory.content}</p>
                  <div style="display: flex; justify-content: space-between; align-items: center;">
                    <small>Источник: {memory.source}</small>
                    <button type="button" class="text-button" on:click={() => removeMemory(memory.id)} style="font-size: 10px;">×</button>
                  </div>
                </div>
              {:else}
                <p class="empty" style="font-size: 12px; padding: 8px 0;">Нет воспоминаний</p>
              {/each}
            </div>
          </div>
        </aside>

        <!-- Center Panel — Chat -->
        <main class="center-panel" style="display: flex; flex-direction: column; height: 100%; overflow: hidden;">
          <StreamingChat
            {apiBase}
            {roomId}
            model={selectedModel}
            {rooms}
            modelNames={models.map(m => m.name)}
          />
        </main>

        <!-- Right Panel — Workbench (Logs / Plan / Artifacts) -->
        <aside class="right-panel" class:hidden={!showRightPanel} aria-label="Workbench панель">
          <!-- Workbench Tabs -->
          <div class="workbench-tabs">
            <button
              type="button"
              class="workbench-tab"
              class:active={activeWorkbenchTab === 'plan'}
              on:click={() => activeWorkbenchTab = 'plan'}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
              <span>План</span>
            </button>
            <button
              type="button"
              class="workbench-tab"
              class:active={activeWorkbenchTab === 'logs'}
              on:click={() => activeWorkbenchTab = 'logs'}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
              <span>Логи</span>
              {#if flightLogs.length > 0}
                <span class="tab-badge">{flightLogs.length}</span>
              {/if}
            </button>
            <button
              type="button"
              class="workbench-tab"
              class:active={activeWorkbenchTab === 'artifacts'}
              on:click={() => activeWorkbenchTab = 'artifacts'}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
              <span>Артефакты</span>
            </button>
          </div>

          <!-- Workbench Content -->
          <div class="workbench-content">
            {#if activeWorkbenchTab === 'plan'}
              <div class="workbench-plan-section">
                <div style="display: flex; flex-direction: column; gap: 8px;">
                  <p style="font-size: 12px; font-weight: 600; color: var(--text-secondary);">Конструктор задач (Agent Lab)</p>
                  <form on:submit|preventDefault={simulatePlan} class="stack-form" style="gap: 8px;">
                    <textarea bind:value={agentTask} rows="3" placeholder="Опишите задачу для агента..." style="font-size: 12px; padding: 8px 10px;"></textarea>
                    <button type="submit" disabled={!agentTask.trim()} style="min-height: 32px; font-size: 12px; padding: 0 14px;">Собрать AgentPlan</button>
                  </form>
                </div>

                {#if agentPlan}
                  <div class="plan-box" style="padding: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                      <strong style="font-size: 12px;">~{agentPlan.estimated_tokens} токенов</strong>
                      <button type="button" class="text-button" on:click={createPlannedAgentRun}>Запустить</button>
                    </div>
                    <ol style="font-size: 12px; padding-left: 16px; display: flex; flex-direction: column; gap: 4px; color: var(--text-secondary);">
                      {#each agentPlan.steps as step}
                        <li>{step}</li>
                      {/each}
                    </ol>
                    <div class="chip-row">
                      {#each agentPlan.required_permissions as permission}
                        <span style="font-size: 10px;">{permission}</span>
                      {/each}
                    </div>
                  </div>
                {:else}
                  <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
                    <p>Создайте план задачи для агента</p>
                  </div>
                {/if}
              </div>

            {:else if activeWorkbenchTab === 'logs'}
              {#if agentRun}
                <div style="display: flex; flex-direction: column; gap: 4px; padding-bottom: 8px; border-bottom: 1px solid var(--border-color);">
                  <div style="display: flex; align-items: center; justify-content: space-between;">
                    <strong style="font-size: 12px;">{agentRun.agent_id}</strong>
                    <span class="count" style="font-size: 10px;">{agentRun.status}</span>
                  </div>
                  <small style="font-size: 10px; color: var(--text-muted); font-family: var(--font-mono);">Run: {agentRun.id}</small>
                </div>
                <div style="display: flex; flex-direction: column; gap: 6px;">
                  {#each flightLogs as log}
                    <div class="workbench-log-entry">
                      <div class="log-header">
                        <span class="log-action">{log.action}</span>
                        <span class="log-meta">{log.tool} · {log.privacy_level}</span>
                      </div>
                      {#if log.output}
                        <div class="log-output">{log.output}</div>
                      {/if}
                    </div>
                  {:else}
                    <p class="empty" style="font-size: 12px;">Логи выполнения отсутствуют.</p>
                  {/each}
                </div>
              {:else}
                <div class="empty-state">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
                  <p>Запустите задачу агента для просмотра логов</p>
                </div>
              {/if}

            {:else if activeWorkbenchTab === 'artifacts'}
              {#if exportedReport}
                <div class="artifact-card">
                  <div class="artifact-header">
                    <span class="artifact-title">{exportedReport.artifact.title}</span>
                    <span class="artifact-kind">{exportedReport.artifact.kind}</span>
                  </div>
                  <div class="artifact-preview">
                    <span style="font-size: 11px; color: var(--text-muted);">ID: {exportedReport.artifact.id}</span>
                    <br>
                    <span style="font-size: 11px; color: var(--text-muted);">Фактов: {exportedReport.receipts_count}</span>
                  </div>
                  <div style="background: var(--bg-input); padding: 10px; border-radius: 6px; border: 1px solid var(--border-color); font-size: 11px; line-height: 1.5; font-family: var(--font-mono); color: var(--text-secondary); max-height: 200px; overflow-y: auto;">
                    {exportedReport.artifact.source}
                  </div>
                </div>
              {:else}
                <div class="empty-state">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
                  <p>Экспортируйте артефакты из исследований или задач</p>
                </div>
              {/if}

              {#if agentPlan}
                <div class="artifact-card">
                  <div class="artifact-header">
                    <span class="artifact-title">AgentPlan</span>
                    <span class="artifact-kind">task</span>
                  </div>
                  <div class="artifact-preview">
                    <strong style="font-size: 12px;">{agentPlan.estimated_tokens} токенов</strong>
                    <ul style="padding-left: 14px; margin-top: 4px; font-size: 11px;">
                      {#each agentPlan.steps as step}
                        <li>{step}</li>
                      {/each}
                    </ul>
                  </div>
                </div>
              {/if}
            {/if}
          </div>
        </aside>
      </div>

    {:else if activeTab === 'agents'}
      <div class="tab-content">
        <section class="panel" style="flex: 1; overflow: hidden;">
          <div class="panel-heading">
            <div>
              <p class="eyebrow">Библиотека системы</p>
              <h2>Зарегистрированные агенты</h2>
            </div>
            <div class="catalog-state">
              <span class:ok={catalogValidation?.ok} class:warn={!catalogValidation?.ok} class="status-dot"></span>
              <strong style="margin-left: 8px;">{catalogValidation?.agents_count ?? 0} агентов</strong>
              <strong style="margin-left: 8px;">{catalogValidation?.skills_count ?? 0} навыков</strong>
            </div>
          </div>

          <div class="agent-layout">
            <div class="agent-list" aria-label="Список агентов">
              {#each [...localAgents, ...hybridAgents, ...externalAgents] as agent}
                <button
                  type="button"
                  class:active={selectedAgent?.id === agent.id}
                  on:click={() => (selectedAgentId = agent.id)}
                >
                  <strong>{agent.name}</strong>
                  <small>{agentGroupTitle(agent)} · {agent.skills.length} навыков</small>
                </button>
              {/each}
            </div>

            {#if selectedAgent}
              <article class="agent-detail">
                <div>
                  <p class="eyebrow" style="margin: 0;">ID манифеста: {selectedAgent.id}</p>
                  <h3>{selectedAgent.name}</h3>
                  <p>{selectedAgent.description}</p>
                </div>
                <dl>
                  <div>
                    <dt>Приватность</dt>
                    <dd>{selectedAgent.privacy_level}</dd>
                  </div>
                  <div>
                    <dt>Модель по умолчанию</dt>
                    <dd>{selectedAgent.default_model}</dd>
                  </div>
                  <div>
                    <dt>Сеть</dt>
                    <dd>{selectedAgent.permissions.network ? 'Разрешена' : 'Блокирована'}</dd>
                  </div>
                  <div>
                    <dt>Терминал</dt>
                    <dd>{selectedAgent.permissions.shell ? 'Разрешен' : 'Блокирован'}</dd>
                  </div>
                </dl>
                <div>
                  <dt style="margin-bottom: 8px;">Поддерживаемые навыки</dt>
                  <div class="chip-row">
                    {#each selectedAgent.skills as skill}
                      <span>{skill}</span>
                    {/each}
                  </div>
                </div>
                <div>
                  <dt style="margin-bottom: 8px;">Критерии приемки задачи</dt>
                  <ol>
                    {#each selectedAgent.acceptance_checks as check}
                      <li>{check}</li>
                    {/each}
                  </ol>
                </div>
              </article>
            {/if}
          </div>
        </section>
      </div>

    {:else if activeTab === 'vault'}
      <div class="tab-content">
        <!-- Sub navigation tabs within Vault -->
        <div class="knowledge-tabs">
          <button class:active={activeVaultTab === 'memory'} on:click={() => activeVaultTab = 'memory'}>Память контекста (Ledger)</button>
          <button class:active={activeVaultTab === 'rag'} on:click={() => activeVaultTab = 'rag'}>Поиск и файлы RAG (Vault)</button>
          <button class:active={activeVaultTab === 'rooms'} on:click={() => activeVaultTab = 'rooms'}>Комнаты окружения</button>
        </div>

        {#if activeVaultTab === 'memory'}
          <div class="secondary-grid">
            <section class="panel">
              <div class="panel-heading compact">
                <h2>Журнал долгосрочной памяти комнаты</h2>
                <span class="count">{memories.length} записей</span>
              </div>
              <form on:submit|preventDefault={addMemory} class="stack-form">
                <textarea bind:value={memoryDraft} placeholder="Введите новое утверждение для фиксации в памяти комнаты..." rows="3"></textarea>
                <button type="submit" disabled={!memoryDraft.trim()}>Добавить в Ledger</button>
              </form>
            </section>

            <section class="panel">
              <div class="panel-heading compact">
                <h2>Активные воспоминания в памяти</h2>
              </div>
              <div class="memory-list">
                {#each memories as memory}
                  <article>
                    <p>{memory.content}</p>
                    <small>Источник: {memory.source}</small>
                    <button type="button" class="text-button" on:click={() => removeMemory(memory.id)}>Удалить из памяти</button>
                  </article>
                {:else}
                  <p class="empty">У данной комнаты еще нет накопленных воспоминаний.</p>
                {/each}
              </div>
            </section>
          </div>

        {:else if activeVaultTab === 'rag'}
          <div class="secondary-grid">
            <section class="panel">
              <div class="panel-heading compact">
                <h2>Локальный RAG-поиск</h2>
              </div>
              <form on:submit|preventDefault={runRagSearch} class="stack-form">
                <input bind:value={ragQuery} placeholder="Запрос по локальному индексу..." />
                <button type="submit" disabled={!ragQuery.trim()}>Искать по базе</button>
              </form>
              <div class="result-list" style="margin-top: 12px; max-height: 380px;">
                {#each ragResults as chunk}
                  <article>
                    <strong>{chunk.source}</strong>
                    <p>{chunk.content}</p>
                    <small>Сходство (score): {chunk.score.toFixed(3)}</small>
                  </article>
                {:else}
                  <p class="empty">Результатов локального поиска пока нет.</p>
                {/each}
              </div>
            </section>

            <section class="panel">
              <div class="panel-heading compact">
                <h2>Документы в хранилище Vault</h2>
                <button type="button" class="text-button" on:click={refreshRagDocuments}>Обновить список</button>
              </div>
              <div class="result-list" style="max-height: 440px;">
                {#each ragDocuments as document}
                  <article>
                    <strong>{document.source}</strong>
                    <small>{document.indexed_chunks} чанков (сегментов) · Комната: {document.room_id}</small>
                    <button type="button" class="text-button" on:click={() => removeRagDocument(document.id)}>Удалить индекс</button>
                  </article>
                {:else}
                  <p class="empty">В Vault еще нет проиндексированных документов.</p>
                {/each}
              </div>
            </section>
          </div>

        {:else if activeVaultTab === 'rooms'}
          <div class="secondary-grid">
            <section class="panel">
              <div class="panel-heading compact">
                <h2>Создать комнату окружения</h2>
              </div>
              <form on:submit|preventDefault={addRoom} class="stack-form">
                <input bind:value={roomDraft} placeholder="Название комнаты контекста..." />
                <button type="submit" disabled={!roomDraft.trim()}>Создать комнату</button>
              </form>
            </section>

            <section class="panel">
              <div class="panel-heading compact">
                <h2>Существующие комнаты</h2>
                <span class="count">{rooms.length}</span>
              </div>
              <div class="memory-list">
                {#each rooms as room}
                  <article>
                    <p><strong>{room.name}</strong></p>
                    <small>Политика памяти: {room.memory_policy} · Удержание: {room.retention_days} дней · Разрешено моделей: {room.allowed_models.length}</small>
                  </article>
                {:else}
                  <p class="empty">Комнаты контекста не найдены.</p>
                {/each}
              </div>
            </section>
          </div>
        {/if}
      </div>

    {:else if activeTab === 'research'}
      <div class="tab-content">
        <div class="secondary-grid">
          <section class="panel">
            <div class="panel-heading compact">
              <h2>Регистрация фактов исследований (Research Receipts)</h2>
            </div>
            <form on:submit|preventDefault={exportResearchArtifact} class="stack-form">
              <label style="display: flex; flex-direction: column; gap: 4px;">
                <span style="font-size: 11px; font-weight: 600; color: var(--text-secondary);">Цель исследования</span>
                <input bind:value={researchQuery} placeholder="Например: Сравнить скорость локального вывода" />
              </label>

              <label style="display: flex; flex-direction: column; gap: 4px;">
                <span style="font-size: 11px; font-weight: 600; color: var(--text-secondary);">Название источника</span>
                <input bind:value={researchSourceTitle} placeholder="Например: Статья или лог" />
              </label>

              <label style="display: flex; flex-direction: column; gap: 4px;">
                <span style="font-size: 11px; font-weight: 600; color: var(--text-secondary);">Утверждение / Доказательство</span>
                <textarea bind:value={researchClaim} rows="4" placeholder="Текст утверждения..."></textarea>
              </label>

              <button type="submit" disabled={!researchQuery.trim() || !researchClaim.trim()}>Экспортировать Artifact</button>
            </form>
          </section>

          <section class="panel">
            <div class="panel-heading compact">
              <h2>Результат экспорта</h2>
            </div>
            {#if exportedReport}
              <div class="plan-box" style="margin-top: 0;">
                <strong>{exportedReport.artifact.title}</strong>
                <small>Связано фактов: {exportedReport.receipts_count} · ID артефакта: {exportedReport.artifact.id}</small>
                <div style="background: var(--bg-app); padding: 12px; border-radius: 8px; border: 1px solid var(--border-color); margin-top: 8px;">
                  <p style="font-size: 12px; line-height: 1.5; font-family: var(--font-mono);">{exportedReport.artifact.source}</p>
                </div>
              </div>
            {:else}
              <p class="empty">Экспортируйте протокол, чтобы просмотреть результаты генерации артефакта.</p>
            {/if}
          </section>
        </div>
      </div>

    {:else if activeTab === 'system'}
      <div class="tab-content">
        <div class="secondary-grid">
          <!-- Desktop sidecar control -->
          <section class="panel">
            <div class="panel-heading compact">
              <h2>Управление Sidecar сервисом</h2>
              <span class:ok={desktopStatus?.running} class:warn={!desktopStatus?.running} class="status-dot"></span>
            </div>
            <p class="desktop-note" style="font-size: 13.5px; line-height: 1.5; color: var(--text-secondary);">
              {desktopAvailable ? 'Среда Tauri IPC активна. Вы можете перезапускать FastAPI бэкенд из приложения.' : 'Браузерный режим. Управление sidecar заблокировано. Используйте внешний FastAPI URL.'}
            </p>

            <div class="button-grid" style="margin-top: 8px;">
              <button type="button" on:click={startDesktopBackend} disabled={!desktopAvailable}>Запустить sidecar</button>
              <button type="button" class="secondary" on:click={checkDesktopBackend} disabled={!desktopAvailable}>Проверить Health</button>
              <button type="button" class="secondary" on:click={stopDesktopBackend} disabled={!desktopAvailable}>Остановить</button>
            </div>

            {#if desktopStatus}
              <div style="background: var(--bg-input); padding: 10px 14px; border: 1px solid var(--border-color); border-radius: 8px; font-family: var(--font-mono); font-size: 12px; margin-top: 8px;">
                <span>Статус: <strong>{desktopStatus.running ? 'запущен' : 'остановлен'}</strong></span><br>
                <span>Адрес: <strong>{desktopStatus.host}:{desktopStatus.port}</strong></span>
              </div>
            {/if}
          </section>

          <!-- Hardware model router -->
          <section class="panel">
            <div class="panel-heading compact">
              <h2>Конструктор маршрутов моделей (Model Router)</h2>
            </div>
            <label style="display: flex; flex-direction: column; gap: 4px;">
              <span style="font-size: 11px; font-weight: 600; color: var(--text-secondary);">Описание целевой задачи</span>
              <input bind:value={taskDescription} placeholder="Например: локальный чат для кодинга" />
            </label>

            <div class="split-controls">
              <label style="display: flex; flex-direction: column; gap: 4px;">
                <span style="font-size: 11px; font-weight: 600; color: var(--text-secondary);">VRAM видеокарты (ГБ)</span>
                <input type="number" min="0" step="1" bind:value={vramGb} />
              </label>
              <label style="display: flex; flex-direction: column; gap: 4px;">
                <span style="font-size: 11px; font-weight: 600; color: var(--text-secondary);">RAM ОЗУ системы (ГБ)</span>
                <input type="number" min="0" step="1" bind:value={ramGb} />
              </label>
            </div>

            <button type="button" style="margin-top: 8px;" on:click={routeModel}>Рассчитать оптимальную модель</button>

            {#if modelSelection}
              <div class="plan-box" style="margin-top: 12px;">
                <strong>Оптимально: {modelSelection.model}</strong>
                <span>Режим работы: {modelSelection.mode === 'api' ? 'Внешний API' : 'Локальный вывод'}</span>
                <small style="margin-top: 4px; line-height: 1.4;">{modelSelection.reason}</small>
              </div>
            {/if}
          </section>

          <!-- FastAPI config -->
          <section class="panel" style="grid-column: span 2;">
            <div class="panel-heading compact">
              <h2>Сервер подключения</h2>
            </div>
            <label style="display: flex; flex-direction: column; gap: 4px;">
              <span style="font-size: 11px; font-weight: 600; color: var(--text-secondary);">Базовый FastAPI API URL адрес</span>
              <input bind:value={apiBase} style="font-family: var(--font-mono);" aria-label="FastAPI base URL" />
            </label>
            <small style="color: var(--text-muted); line-height: 1.4;">Это адрес, по которому Tauri-клиент общается с серверным sidecar-модулем. Изменяйте только при переносе бэкенда на внешний сервер.</small>
          </section>
        </div>
      </div>
    {/if}
  </main>
</div>
