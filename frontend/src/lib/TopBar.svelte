<script lang="ts">
  import { activeTab, showLeftPanel, showRightPanel, privacyPopoverOpen, refreshAll, busy } from './stores';
  import PrivacyRadar from './PrivacyRadar.svelte';
</script>

<header class="topbar">
  <div>
    {#if $activeTab === 'chat'}
      <p class="eyebrow">Окружение диалога</p>
      <h1>Интерактивный чат</h1>
    {:else if $activeTab === 'agents'}
      <p class="eyebrow">Манифесты процессов</p>
      <h1>Каталог Агентов</h1>
    {:else if $activeTab === 'vault'}
      <p class="eyebrow">Органайзер контекста</p>
      <h1>Хранилище знаний</h1>
    {:else if $activeTab === 'research'}
      <p class="eyebrow">Верификация источников</p>
      <h1>Журнал исследований</h1>
    {:else if $activeTab === 'system'}
      <p class="eyebrow">Аппаратный роутинг</p>
      <h1>Консоль конфигураций</h1>
    {:else if $activeTab === 'research_deep'}
      <p class="eyebrow">Аналитика источников</p>
      <h1>Deep Research Studio</h1>
    {:else if $activeTab === 'images'}
      <p class="eyebrow">Генерация изображений</p>
      <h1>Image Studio</h1>
    {:else if $activeTab === 'automation'}
      <p class="eyebrow">Рабочие процессы</p>
      <h1>Automation Board</h1>
    {:else if $activeTab === 'artifacts_browser'}
      <p class="eyebrow">Хранилище артефактов</p>
      <h1>Артефакты</h1>
    {:else if $activeTab === 'plugins'}
      <p class="eyebrow">Расширения</p>
      <h1>Plugin Manager</h1>
    {/if}
  </div>

  <div class="top-controls">
    {#if $activeTab === 'chat'}
      <!-- Panel toggle buttons -->
      <div class="panel-toggle-group">
        <button
          type="button"
          class="panel-toggle-btn"
          class:active={$showLeftPanel}
          on:click={() => $showLeftPanel = !$showLeftPanel}
          title="Показать/скрыть боковую панель"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="3" x2="9" y2="21"/></svg>
          <span>Контекст</span>
        </button>
        <button
          type="button"
          class="panel-toggle-btn"
          class:active={$showRightPanel}
          on:click={() => $showRightPanel = !$showRightPanel}
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
          on:click={() => $privacyPopoverOpen = !$privacyPopoverOpen}
        >
          <span class="status-dot ok"></span>
          <span>Безопасность</span>
        </button>

        <div class="privacy-popover" class:visible={$privacyPopoverOpen}>
          <PrivacyRadar />
        </div>
      </div>
    {/if}

    <button type="button" class="secondary" style="min-height: 32px; padding: 0 12px; margin-left: 8px;" on:click={refreshAll} disabled={$busy}>
      {$busy ? 'Проверка...' : 'Обновить'}
    </button>
  </div>
</header>
