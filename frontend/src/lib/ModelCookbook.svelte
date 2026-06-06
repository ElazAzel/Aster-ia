<script lang="ts">
  import { apiBase, models, selectedModel, showToast, runStep } from './stores';
  import { pullModel } from './api';

  type Recipe = {
    id: string;
    title: string;
    model: string;
    profile: string;
    vram: string;
    mode: 'chat' | 'code' | 'research' | 'embedding';
    reason: string;
  };

  const RECIPES: Recipe[] = [
    {
      id: 'starter-chat',
      title: 'Starter Chat',
      model: 'llama3.2',
      profile: 'Быстрый локальный ассистент',
      vram: '4-6 GB',
      mode: 'chat',
      reason: 'Хороший первый выбор для локального чата и коротких задач.'
    },
    {
      id: 'coding',
      title: 'Coding Copilot',
      model: 'qwen2.5-coder:7b',
      profile: 'Код, ревью, shell-plan',
      vram: '8 GB',
      mode: 'code',
      reason: 'Оптимизирован для кода и хорошо вписывается в Agent Lab.'
    },
    {
      id: 'research',
      title: 'Research Analyst',
      model: 'mistral:7b',
      profile: 'Сводки, receipts, аргументы',
      vram: '8 GB',
      mode: 'research',
      reason: 'Стабильная универсальная модель для Research Studio.'
    },
    {
      id: 'power',
      title: 'Power User',
      model: 'llama3.1:8b',
      profile: 'Длинные ответы и контекст',
      vram: '10-12 GB',
      mode: 'chat',
      reason: 'Компромисс между качеством, скоростью и локальным запуском.'
    },
    {
      id: 'small',
      title: 'Low VRAM',
      model: 'phi3:mini',
      profile: 'Ноутбук без мощной GPU',
      vram: '2-4 GB',
      mode: 'chat',
      reason: 'Запасной вариант для слабого железа.'
    },
    {
      id: 'embedding',
      title: 'Vault Embeddings',
      model: 'nomic-embed-text',
      profile: 'RAG и semantic search',
      vram: 'CPU OK',
      mode: 'embedding',
      reason: 'Обязательная embedding-модель для Knowledge Vault.'
    },
    {
      id: 'deepseek',
      title: 'Reasoning Local',
      model: 'deepseek-r1:8b',
      profile: 'Планирование и анализ',
      vram: '10-12 GB',
      mode: 'research',
      reason: 'Подходит для декомпозиции задач и сложных рассуждений.'
    },
    {
      id: 'fast-drafts',
      title: 'Fast Drafts',
      model: 'gemma2:2b',
      profile: 'Черновики, краткие ответы',
      vram: '2-4 GB',
      mode: 'chat',
      reason: 'Лёгкий режим для быстрых локальных черновиков.'
    }
  ];

  let active = RECIPES[0];
  let pulling = false;
  let pullLog: string[] = [];

  $: installedNames = $models.map((model) => model.name);
  $: activeInstalled = isInstalled(active.model);

  function isInstalled(model: string) {
    const base = model.split(':')[0];
    return installedNames.some((name) => name === model || name.split(':')[0] === base);
  }

  function selectRecipe(recipe: Recipe) {
    active = recipe;
    if (isInstalled(recipe.model)) {
      selectedModel.set(recipe.model);
      showToast(`Модель ${recipe.model} выбрана`, 'success');
    }
  }

  function chunkLabel(chunk: Record<string, unknown>) {
    const status = String(chunk.status ?? 'progress');
    const completed = Number(chunk.completed ?? 0);
    const total = Number(chunk.total ?? 0);
    if (total > 0) {
      const percent = Math.min(100, Math.round((completed / total) * 100));
      return `${status} · ${percent}%`;
    }
    return status;
  }

  async function installActive() {
    pulling = true;
    pullLog = [];
    const ok = await runStep(`Загружаю модель ${active.model}`, async () => {
      for await (const chunk of pullModel($apiBase, active.model)) {
        pullLog = [...pullLog.slice(-12), chunkLabel(chunk)];
      }
      return true;
    });
    pulling = false;
    if (ok) {
      selectedModel.set(active.model);
      showToast(`Модель ${active.model} готова`, 'success');
    }
  }
</script>

<section class="panel" style="grid-column: span 2;">
  <div class="panel-heading compact">
    <h2>Model Cookbook</h2>
    <span class:ok={activeInstalled} class:warn={!activeInstalled} class="status-dot"></span>
  </div>

  <div class="cookbook-layout">
    <div class="recipe-list">
      {#each RECIPES as recipe}
        <button
          type="button"
          class:active={active.id === recipe.id}
          on:click={() => selectRecipe(recipe)}
        >
          <span>
            <strong>{recipe.title}</strong>
            <small>{recipe.model} · {recipe.vram}</small>
          </span>
          {#if isInstalled(recipe.model)}
            <span class="recipe-state">installed</span>
          {/if}
        </button>
      {/each}
    </div>

    <div class="recipe-detail">
      <div>
        <span class="canvas-label">{active.mode}</span>
        <h3>{active.title}</h3>
        <p>{active.profile}</p>
      </div>
      <div class="plan-box" style="margin-top: 0;">
        <strong>{active.model}</strong>
        <small>VRAM: {active.vram}</small>
        <p>{active.reason}</p>
      </div>
      <div class="button-grid">
        <button type="button" on:click={() => selectedModel.set(active.model)} disabled={!activeInstalled}>
          Выбрать
        </button>
        <button type="button" class="secondary" on:click={installActive} disabled={pulling || activeInstalled}>
          {pulling ? 'Загрузка...' : activeInstalled ? 'Установлена' : 'Pull через Ollama'}
        </button>
      </div>
      {#if pullLog.length > 0}
        <div class="pull-log">
          {#each pullLog as row}
            <span>{row}</span>
          {/each}
        </div>
      {/if}
    </div>
  </div>
</section>

<style>
  .cookbook-layout {
    display: grid;
    grid-template-columns: minmax(220px, 0.85fr) minmax(280px, 1.15fr);
    gap: 14px;
  }

  .recipe-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .recipe-list button {
    align-items: center;
    background: var(--bg-input);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    color: var(--text-secondary);
    display: flex;
    justify-content: space-between;
    min-height: 58px;
    padding: 10px 12px;
    text-align: left;
  }

  .recipe-list button.active {
    border-color: rgba(124, 109, 250, 0.55);
    color: var(--text-primary);
  }

  .recipe-list strong,
  .recipe-list small {
    display: block;
  }

  .recipe-list strong {
    font-size: 13px;
  }

  .recipe-list small,
  .recipe-detail p,
  .recipe-detail small {
    color: var(--text-secondary);
    font-size: 12px;
    line-height: 1.45;
  }

  .recipe-state {
    color: var(--color-green-text);
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
  }

  .recipe-detail {
    display: flex;
    flex-direction: column;
    gap: 12px;
    min-width: 0;
  }

  .recipe-detail h3 {
    font-size: 18px;
    margin: 4px 0;
  }

  .canvas-label {
    color: var(--text-muted);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .pull-log {
    background: var(--bg-input);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    color: var(--text-secondary);
    display: flex;
    flex-direction: column;
    font-family: var(--font-mono);
    font-size: 11px;
    gap: 4px;
    max-height: 160px;
    overflow-y: auto;
    padding: 10px;
  }

  @media (max-width: 900px) {
    .cookbook-layout {
      grid-template-columns: 1fr;
    }
  }
</style>
