<script lang="ts">
  import { onMount } from 'svelte';
  import { activeTab, showLeftPanel, showRightPanel, privacyPopoverOpen, refreshAll, busy } from './stores';
  import PrivacyRadar from './PrivacyRadar.svelte';
  import { isTauriRuntime, toggleFullscreen } from './tauri';

  let fsActive = false;
  let tauri = false;

  function handleFullscreen() {
    toggleFullscreen().then(fs => {
      fsActive = fs;
    });
  }

  onMount(() => {
    tauri = isTauriRuntime();
  });
</script>

<header class="topbar">
  <div>
    {#if $activeTab === 'command_center'}
      <p class="eyebrow">Панель управления</p>
      <h1>Command Center</h1>
    {:else if $activeTab === 'chat'}
      <p class="eyebrow">Окружение диалога</p>
      <h1>Интерактивный чат</h1>
    {:else if $activeTab === 'voice'}
      <p class="eyebrow">Локальная речь и заметки</p>
      <h1>Voice Mode</h1>
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
      <div class="panel-toggle-group">
        <button
          type="button"
          class="panel-toggle-btn"
          class:active={$showLeftPanel}
          on:click={() => $showLeftPanel = !$showLeftPanel}
          title="Показать/скрыть боковую панель"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="3" x2="9" y2="21"/></svg>
          <span class="ctrl-label">Контекст</span>
        </button>
        <button
          type="button"
          class="panel-toggle-btn"
          class:active={$showRightPanel}
          on:click={() => $showRightPanel = !$showRightPanel}
          title="Показать/скрыть Workbench"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="15" y1="3" x2="15" y2="21"/></svg>
          <span class="ctrl-label">Workbench</span>
        </button>
      </div>

      <div class="privacy-popover-trigger">
        <button
          type="button"
          class="privacy-badge-compact"
          on:click={() => $privacyPopoverOpen = !$privacyPopoverOpen}
          title="Безопасность"
        >
          <span class="status-dot ok"></span>
          <span class="ctrl-label">Безопасность</span>
        </button>

        <div class="privacy-popover" class:visible={$privacyPopoverOpen}>
          <PrivacyRadar />
        </div>
      </div>
    {/if}

    {#if tauri}
      <button
        type="button"
        class="fs-toggle"
        on:click={handleFullscreen}
        title={fsActive ? 'Выйти из полноэкранного режима (Ctrl+Shift+F)' : 'Полноэкранный режим (Ctrl+Shift+F)'}
      >
        {#if fsActive}
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/><line x1="14" y1="10" x2="21" y2="3"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
        {:else}
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
        {/if}
      </button>
    {/if}

    <button type="button" class="secondary" style="min-height: 32px; padding: 0 12px;" on:click={refreshAll} disabled={$busy}>
      {$busy ? 'Проверка...' : 'Обновить'}
    </button>
  </div>
</header>