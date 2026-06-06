<script lang="ts">
  import { onMount } from 'svelte';
  import {
    DEFAULT_API_BASE,
    analyzePrivacy,
    createMemory,
    deleteMemory,
    getAgentCatalog,
    getHealth,
    getModels,
    listMemories,
    searchRag,
    selectModel,
    simulateAgentTask,
    validateAgentCatalog,
    type AgentCatalog,
    type AgentManifest,
    type AgentPlan,
    type CatalogValidation,
    type HealthResponse,
    type MemoryRecord,
    type ModelInfo,
    type ModelSelection,
    type PrivacyReport,
    type RagChunk,
    type RiskLevel
  } from './lib/api';
  import StreamingChat from './lib/StreamingChat.svelte';

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
  let memories: MemoryRecord[] = [];
  let memoryDraft = '';
  let ragQuery = '';
  let ragResults: RagChunk[] = [];
  let agentTask = 'Проверить локальный документ и найти противоречия';
  let agentPlan: AgentPlan | null = null;
  let statusText = 'Ожидание проверки';
  let busy = false;
  let errorText = '';

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
    if (level === 'green') return 'Локально';
    if (level === 'yellow') return 'Требует внимания';
    if (level === 'red') return 'Нужно согласие';
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

  async function refreshMemories() {
    const result = await runStep('Читаю память комнаты', () => listMemories(apiBase, roomId));
    if (result) memories = result;
  }

  async function refreshAll() {
    busy = true;
    await Promise.allSettled([refreshHealth(), refreshModels(), refreshCatalog(), refreshMemories(), analyzeCurrentPrivacy()]);
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

  async function simulatePlan() {
    const task = agentTask.trim();
    if (!task) return;
    const result = await runStep('Генерирую AgentPlan', () => simulateAgentTask(apiBase, task));
    if (result) agentPlan = result;
  }

  function agentGroupTitle(agent: AgentManifest) {
    if (agent.privacy_level === 'hybrid') return 'hybrid';
    if (agent.privacy_level === 'external') return 'external';
    return 'local';
  }

  onMount(() => {
    void refreshAll();
  });
</script>

<svelte:head>
  <title>Asterion AI Workspace</title>
</svelte:head>

<div class="app-shell">
  <aside class="side-rail" aria-label="Навигация Asterion">
    <div class="brand">
      <span class="brand-mark">A</span>
      <div>
        <strong>Asterion AI</strong>
        <small>Local-first workspace</small>
      </div>
    </div>

    <nav>
      <a href="#chat">Чат</a>
      <a href="#agents">Агенты</a>
      <a href="#privacy">Privacy</a>
      <a href="#memory">Память</a>
      <a href="#rag">RAG</a>
    </nav>

    <div class="system-meter">
      <span class:ok={health?.status === 'ok'} class:warn={health?.status !== 'ok'} class="status-dot"></span>
      <div>
        <strong>{health?.status ?? 'offline'}</strong>
        <small>uptime {formatUptime(health?.uptime_seconds)}</small>
      </div>
    </div>
  </aside>

  <main class="workspace">
    <header class="topbar">
      <div>
        <p class="eyebrow">Runtime console</p>
        <h1>Командный центр</h1>
      </div>
      <label class="api-field">
        <span>FastAPI</span>
        <input bind:value={apiBase} aria-label="FastAPI base URL" />
      </label>
      <button type="button" on:click={refreshAll} disabled={busy}>
        {busy ? 'Проверка' : 'Обновить'}
      </button>
    </header>

    {#if errorText}
      <p class="notice error">{errorText}</p>
    {:else}
      <p class="notice">{statusText}</p>
    {/if}

    <div class="primary-grid">
      <section id="chat" class="panel chat-panel" aria-labelledby="chat-title">
        <div class="panel-heading">
          <div>
            <p class="eyebrow">SSE streaming</p>
            <h2 id="chat-title">Живой чат</h2>
          </div>
          <div class="inline-controls">
            <label>
              <span>Комната</span>
              <input bind:value={roomId} on:change={() => void refreshMemories()} />
            </label>
            <label>
              <span>Модель</span>
              <select bind:value={selectedModel}>
                {#if models.length === 0}
                  <option value={selectedModel}>{selectedModel}</option>
                {:else}
                  {#each models as model}
                    <option value={model.name}>{model.name}</option>
                  {/each}
                {/if}
              </select>
            </label>
          </div>
        </div>
        <StreamingChat {apiBase} {roomId} model={selectedModel} />
      </section>

      <aside class="right-stack" aria-label="Операционные панели">
        <section id="privacy" class="panel">
          <div class="panel-heading compact">
            <h2>Privacy Radar</h2>
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
              <span>Web</span>
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
                <span class={`risk-${item.risk}`}></span>
                <strong>{item.what}</strong>
                <small>{item.destination}</small>
              </li>
            {/each}
          </ul>
        </section>

        <section class="panel">
          <div class="panel-heading compact">
            <h2>Model Router</h2>
          </div>
          <label class="field">
            <span>Задача</span>
            <input bind:value={taskDescription} />
          </label>
          <div class="split-controls">
            <label>
              <span>VRAM</span>
              <input type="number" min="0" step="1" bind:value={vramGb} />
            </label>
            <label>
              <span>RAM</span>
              <input type="number" min="0" step="1" bind:value={ramGb} />
            </label>
          </div>
          <button type="button" on:click={routeModel}>Выбрать модель</button>
          {#if modelSelection}
            <p class="result-line">
              <strong>{modelSelection.model}</strong>
              <span>{modelSelection.mode}</span>
            </p>
            <small>{modelSelection.reason}</small>
          {/if}
        </section>

        <section id="memory" class="panel">
          <div class="panel-heading compact">
            <h2>Memory Ledger</h2>
            <span class="count">{memories.length}</span>
          </div>
          <form on:submit|preventDefault={addMemory} class="stack-form">
            <textarea bind:value={memoryDraft} placeholder="Новая память комнаты" rows="2"></textarea>
            <button type="submit" disabled={!memoryDraft.trim()}>Добавить</button>
          </form>
          <div class="memory-list">
            {#each memories as memory}
              <article>
                <p>{memory.content}</p>
                <small>{memory.source}</small>
                <button type="button" class="text-button" on:click={() => removeMemory(memory.id)}>Удалить</button>
              </article>
            {:else}
              <p class="empty">Активной памяти нет.</p>
            {/each}
          </div>
        </section>
      </aside>
    </div>

    <section id="agents" class="panel agent-panel">
      <div class="panel-heading">
        <div>
          <p class="eyebrow">Runtime catalog</p>
          <h2>Агенты и скиллы</h2>
        </div>
        <div class="catalog-state">
          <span class:ok={catalogValidation?.ok} class:warn={!catalogValidation?.ok} class="status-dot"></span>
          <strong>{catalogValidation?.agents_count ?? 0} агентов</strong>
          <strong>{catalogValidation?.skills_count ?? 0} скиллов</strong>
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
              <small>{agentGroupTitle(agent)} · {agent.skills.length} skills</small>
            </button>
          {/each}
        </div>

        {#if selectedAgent}
          <article class="agent-detail">
            <div>
              <p class="eyebrow">{selectedAgent.id}</p>
              <h3>{selectedAgent.name}</h3>
              <p>{selectedAgent.description}</p>
            </div>
            <dl>
              <div>
                <dt>Privacy</dt>
                <dd>{selectedAgent.privacy_level}</dd>
              </div>
              <div>
                <dt>Model</dt>
                <dd>{selectedAgent.default_model}</dd>
              </div>
              <div>
                <dt>Network</dt>
                <dd>{selectedAgent.permissions.network ? 'on' : 'off'}</dd>
              </div>
              <div>
                <dt>Shell</dt>
                <dd>{selectedAgent.permissions.shell ? 'on' : 'off'}</dd>
              </div>
            </dl>
            <div class="chip-row">
              {#each selectedAgent.skills as skill}
                <span>{skill}</span>
              {/each}
            </div>
            <ol>
              {#each selectedAgent.acceptance_checks as check}
                <li>{check}</li>
              {/each}
            </ol>
          </article>
        {/if}
      </div>
    </section>

    <div class="secondary-grid">
      <section id="rag" class="panel">
        <div class="panel-heading compact">
          <h2>RAG Search</h2>
        </div>
        <form on:submit|preventDefault={runRagSearch} class="stack-form">
          <input bind:value={ragQuery} placeholder="Поиск по локальному индексу" />
          <button type="submit" disabled={!ragQuery.trim()}>Искать</button>
        </form>
        <div class="result-list">
          {#each ragResults as chunk}
            <article>
              <strong>{chunk.source}</strong>
              <p>{chunk.content}</p>
              <small>score {chunk.score.toFixed(3)}</small>
            </article>
          {:else}
            <p class="empty">Результатов пока нет.</p>
          {/each}
        </div>
      </section>

      <section class="panel">
        <div class="panel-heading compact">
          <h2>Task Simulator</h2>
        </div>
        <form on:submit|preventDefault={simulatePlan} class="stack-form">
          <textarea bind:value={agentTask} rows="3"></textarea>
          <button type="submit" disabled={!agentTask.trim()}>Собрать AgentPlan</button>
        </form>
        {#if agentPlan}
          <div class="plan-box">
            <strong>{agentPlan.estimated_tokens} токенов</strong>
            <ol>
              {#each agentPlan.steps as step}
                <li>{step}</li>
              {/each}
            </ol>
            <div class="chip-row">
              {#each agentPlan.required_permissions as permission}
                <span>{permission}</span>
              {/each}
            </div>
          </div>
        {/if}
      </section>
    </div>
  </main>
</div>
