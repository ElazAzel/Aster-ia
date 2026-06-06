<script lang="ts">
  import { onMount } from 'svelte';
  import {
    showCommandPalette,
    activeTab,
    toggleTheme,
    rooms,
    roomId,
    catalog,
    selectedAgentId,
    showToast,
    refreshRooms
  } from './stores';

  let searchInput: HTMLInputElement;
  let query = '';
  let selectedIndex = 0;

  // Base navigation commands
  const baseCommands = [
    { id: 'nav-chat', title: 'Перейти в Чат', category: 'Навигация', action: () => { $activeTab = 'chat'; } },
    { id: 'nav-agents', title: 'Открыть Лабораторию агентов', category: 'Навигация', action: () => { $activeTab = 'agents'; } },
    { id: 'nav-vault', title: 'Открыть Хранилище (RAG Vault)', category: 'Навигация', action: () => { $activeTab = 'vault'; } },
    { id: 'nav-research-deep', title: 'Открыть Deep Research', category: 'Навигация', action: () => { $activeTab = 'research_deep'; } },
    { id: 'nav-images', title: 'Открыть Студию изображений', category: 'Навигация', action: () => { $activeTab = 'images'; } },
    { id: 'nav-automation', title: 'Открыть Автоматизацию (Workflows)', category: 'Навигация', action: () => { $activeTab = 'automation'; } },
    { id: 'nav-artifacts', title: 'Открыть Браузер артефактов', category: 'Навигация', action: () => { $activeTab = 'artifacts_browser'; } },
    { id: 'nav-plugins', title: 'Открыть Настройки плагинов', category: 'Навигация', action: () => { $activeTab = 'plugins'; } },
    { id: 'nav-system', title: 'Открыть Системные настройки', category: 'Навигация', action: () => { $activeTab = 'system'; } },
    { id: 'cmd-theme', title: 'Переключить тему (Светлая / Темная)', category: 'Утилиты', action: () => { toggleTheme(); showToast('Тема оформления переключена', 'success'); } },
  ];

  // Dynamic commands list
  $: roomCommands = $rooms.map(room => ({
    id: `room-${room.id}`,
    title: `Перейти в комнату: ${room.name}`,
    category: 'Контекстные комнаты',
    action: () => {
      $roomId = room.id;
      $activeTab = 'chat';
      showToast(`Вы перешли в комнату "${room.name}"`, 'success');
    }
  }));

  $: agentCommands = ($catalog?.agents || []).map(agent => ({
    id: `agent-${agent.id}`,
    title: `Выбрать агента: ${agent.name}`,
    category: 'Агенты',
    action: () => {
      $selectedAgentId = agent.id;
      $activeTab = 'chat';
      showToast(`Выбран агент "${agent.name}"`, 'success');
    }
  }));

  $: allCommands = [...baseCommands, ...roomCommands, ...agentCommands];

  $: filteredCommands = allCommands.filter(cmd => 
    cmd.title.toLowerCase().includes(query.toLowerCase()) ||
    cmd.category.toLowerCase().includes(query.toLowerCase())
  );

  // Keep index in bounds when filter changes
  $: {
    if (selectedIndex >= filteredCommands.length) {
      selectedIndex = Math.max(0, filteredCommands.length - 1);
    }
  }

  onMount(() => {
    searchInput?.focus();
    void refreshRooms();
  });

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      selectedIndex = (selectedIndex + 1) % filteredCommands.length;
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      selectedIndex = (selectedIndex - 1 + filteredCommands.length) % filteredCommands.length;
    } else if (event.key === 'Enter') {
      event.preventDefault();
      if (filteredCommands[selectedIndex]) {
        executeCommand(filteredCommands[selectedIndex]);
      }
    } else if (event.key === 'Escape') {
      event.preventDefault();
      $showCommandPalette = false;
    }
  }

  function executeCommand(cmd: typeof allCommands[number]) {
    cmd.action();
    $showCommandPalette = false;
  }
</script>

<div class="cmd-overlay" role="presentation" on:mousedown|self={() => $showCommandPalette = false}>
  <div class="cmd-dialog" role="dialog" aria-modal="true">
    <div class="cmd-input-wrapper">
      <span class="cmd-search-icon">🔍</span>
      <input
        type="text"
        placeholder="Поиск комнат, агентов, вкладок и системных команд..."
        bind:value={query}
        bind:this={searchInput}
        on:keydown={handleKeydown}
        class="cmd-input"
        id="cmd-palette-input"
      />
    </div>

    <div class="cmd-results" id="cmd-palette-results">
      {#if filteredCommands.length > 0}
        {@const categories = [...new Set(filteredCommands.map(c => c.category))]}
        {#each categories as category}
          <div class="cmd-group-title">{category}</div>
          {#each filteredCommands.filter(c => c.category === category) as cmd}
            {@const globalIndex = filteredCommands.indexOf(cmd)}
            <button
              type="button"
              class="cmd-item {globalIndex === selectedIndex ? 'selected' : ''}"
              on:click={() => executeCommand(cmd)}
              on:mouseenter={() => selectedIndex = globalIndex}
              id="cmd-item-{cmd.id}"
            >
              <span class="cmd-item-title">{cmd.title}</span>
              {#if globalIndex === selectedIndex}
                <span class="cmd-item-enter">⏎ Enter</span>
              {/if}
            </button>
          {/each}
        {/each}
      {:else}
        <div class="cmd-empty">Ничего не найдено по запросу "{query}"</div>
      {/if}
    </div>

    <div class="cmd-footer">
      <span><kbd>↑↓</kbd> Навигация</span>
      <span><kbd>Enter</kbd> Выбрать</span>
      <span><kbd>Esc</kbd> Закрыть</span>
    </div>
  </div>
</div>

<style>
  .cmd-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(8, 8, 12, 0.65);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    display: flex;
    justify-content: center;
    padding-top: 100px;
    z-index: 99999;
  }

  .cmd-dialog {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 14px;
    width: 90%;
    max-width: 600px;
    max-height: 480px;
    display: flex;
    flex-direction: column;
    box-shadow: var(--shadow-premium);
    overflow: hidden;
    animation: cmdSlideIn 0.22s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  }

  @keyframes cmdSlideIn {
    from { transform: translateY(-20px) scale(0.97); opacity: 0; }
    to { transform: translateY(0) scale(1); opacity: 1; }
  }

  .cmd-input-wrapper {
    display: flex;
    align-items: center;
    padding: 16px 20px;
    border-bottom: 1px solid var(--border-color);
    gap: 12px;
  }

  .cmd-search-icon {
    font-size: 16px;
    color: var(--text-muted);
  }

  .cmd-input {
    background: transparent;
    border: none;
    padding: 0;
    margin: 0;
    width: 100%;
    font-size: 15px;
    color: var(--text-primary);
    box-shadow: none !important;
  }

  .cmd-results {
    flex: 1;
    overflow-y: auto;
    padding: 12px 8px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .cmd-group-title {
    font-size: 10px;
    font-weight: 700;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    padding: 12px 12px 6px;
  }

  .cmd-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    background: transparent;
    border: 1px solid transparent;
    padding: 10px 14px;
    border-radius: 8px;
    cursor: pointer;
    text-align: left;
    min-height: unset;
    color: var(--text-secondary);
    transition: none;
  }

  .cmd-item.selected {
    background: var(--bg-primary-hover, rgba(124, 109, 250, 0.08));
    border-color: rgba(124, 109, 250, 0.15);
    color: var(--text-primary);
  }

  .cmd-item-title {
    font-size: 13.5px;
    font-weight: 500;
  }

  .cmd-item-enter {
    font-size: 10.5px;
    color: var(--text-muted);
    background: var(--bg-input);
    border: 1px solid var(--border-color);
    padding: 2px 6px;
    border-radius: 4px;
    font-family: var(--font-mono);
  }

  .cmd-empty {
    padding: 24px;
    text-align: center;
    color: var(--text-secondary);
    font-size: 13px;
  }

  .cmd-footer {
    display: flex;
    gap: 16px;
    padding: 12px 20px;
    background: var(--bg-sidebar);
    border-top: 1px solid var(--border-color);
    font-size: 11px;
    color: var(--text-muted);
  }

  .cmd-footer kbd {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    padding: 1px 4px;
    border-radius: 3px;
    font-family: var(--font-mono);
  }
</style>
