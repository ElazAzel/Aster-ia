<script lang="ts">
  import {
    rooms,
    roomId,
    roomDraft,
    selectedModel,
    models,
    memories,
    memoryDraft,
    addRoom,
    addMemory,
    removeMemory,
    refreshMemories,
    refreshRagDocuments,
    showLeftPanel,
    // Chat stores
    conversations,
    conversationId,
    conversationSearchQuery,
    refreshConversations,
    renameConversation,
    removeConversation
  } from './stores';

  $: filteredConversations = $conversations.filter(conv => {
    const query = $conversationSearchQuery.toLowerCase().trim();
    if (!query) return true;
    const dateStr = new Date(conv.created_at).toLocaleString('ru').toLowerCase();
    const titleStr = (conv.title || '').toLowerCase();
    return dateStr.includes(query) || titleStr.includes(query);
  });

  function handleNewChat() {
    $conversationId = null;
  }

  async function handleDelete(id: string) {
    if (confirm('Вы уверены, что хотите удалить этот диалог?')) {
      await removeConversation(id);
    }
  }

  async function handleRename(id: string, currentTitle: string | null, created_at: string) {
    const fallbackTitle = `Чат ${new Date(created_at).toLocaleString('ru')}`;
    const newTitle = prompt('Введите новое название диалога:', currentTitle || fallbackTitle);
    if (newTitle !== null && newTitle.trim()) {
      await renameConversation(id, newTitle.trim());
    }
  }
</script>

<aside class="left-panel" class:hidden={!$showLeftPanel} aria-label="Контекст и память">
  <div class="left-panel-header">
    <h2>Контекст</h2>
  </div>

  <!-- Room Selector -->
  <div class="left-panel-section" style="border-bottom: 1px solid var(--border-color);">
    <h3>Комнаты</h3>
    <div class="room-list">
      {#each $rooms as room}
        <button
          type="button"
          class="room-item"
          class:active={$roomId === room.id}
          on:click={() => {
            $roomId = room.id;
            $conversationId = null;
            void refreshMemories();
            void refreshRagDocuments();
            void refreshConversations();
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
        bind:value={$roomDraft}
        placeholder="Название..."
        on:keydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); void addRoom(); } }}
      />
      <button type="button" disabled={!$roomDraft.trim()} on:click={addRoom}>+</button>
    </div>
  </div>

  <!-- Conversations Section -->
  <div class="left-panel-section" style="border-bottom: 1px solid var(--border-color); flex: 1; display: flex; flex-direction: column; overflow: hidden; min-height: 180px;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
      <h3>Диалоги</h3>
      <button type="button" class="text-button" on:click={handleNewChat} style="font-size: 11px;">+ Новый</button>
    </div>
    
    <!-- Search Bar -->
    <div class="search-wrapper" style="margin-bottom: 8px;">
      <input
        type="text"
        bind:value={$conversationSearchQuery}
        placeholder="Поиск диалогов..."
        style="width: 100%; font-size: 12px; padding: 6px 10px; border-radius: 6px; background: var(--bg-input); border: 1px solid var(--border-color); color: var(--text-primary);"
      />
    </div>

    <!-- Conversations List -->
    <div class="conversation-list" style="flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 4px;">
      {#each filteredConversations as conv}
        <div
          class="conversation-row"
          class:active={$conversationId === conv.id}
          style="display: flex; align-items: center; justify-content: space-between; width: 100%; border-radius: 6px; padding: 4px 6px; transition: var(--transition-smooth);"
        >
          <button
            type="button"
            class="conversation-item-btn"
            on:click={() => $conversationId = conv.id}
            style="flex: 1; display: flex; flex-direction: column; align-items: flex-start; text-align: left; background: transparent; border: none; cursor: pointer; padding: 4px; overflow: hidden;"
          >
            <span class="conv-title" style="font-size: 12.5px; font-weight: 500; color: var(--text-primary); text-overflow: ellipsis; overflow: hidden; white-space: nowrap; width: 100%;">
              {conv.title || `Чат ${new Date(conv.created_at).toLocaleString('ru')}`}
            </span>
            <div style="display: flex; gap: 8px; margin-top: 2px; font-size: 10.5px; color: var(--text-muted);">
              <span>{conv.message_count} сообщ.</span>
              <span>{new Date(conv.created_at).toLocaleDateString('ru')}</span>
            </div>
          </button>
          
          <div class="action-buttons" style="display: flex; gap: 4px; opacity: 0; transition: opacity 0.2s;">
            <button type="button" class="icon-btn" on:click={() => handleRename(conv.id, conv.title, conv.created_at)} title="Переименовать" style="background: transparent; border: none; cursor: pointer; padding: 2px 4px; font-size: 11px; color: var(--text-secondary);">✏️</button>
            <button type="button" class="icon-btn" on:click={() => handleDelete(conv.id)} title="Удалить" style="background: transparent; border: none; cursor: pointer; padding: 2px 4px; font-size: 11px; color: var(--text-secondary);">🗑️</button>
          </div>
        </div>
      {:else}
        <p class="empty" style="padding: 8px 10px; font-size: 12px;">Диалоги не найдены</p>
      {/each}
    </div>
  </div>

  <!-- Model Selector -->
  <div class="left-panel-section" style="border-bottom: 1px solid var(--border-color); flex-shrink: 0;">
    <h3>Модель</h3>
    <select style="font-size: 12px; padding: 6px 10px;" bind:value={$selectedModel}>
      {#if $models.length === 0}
        <option value={$selectedModel}>{$selectedModel}</option>
      {:else}
        {#each $models as model}
          <option value={model.name}>{model.name}</option>
        {/each}
      {/if}
    </select>
  </div>

  <!-- Memory Ledger -->
  <div class="left-panel-section" style="flex: 1; overflow: hidden; display: flex; flex-direction: column; max-height: 200px;">
    <h3>Память (Ledger)</h3>
    <div class="left-panel-input-row">
      <input
        bind:value={$memoryDraft}
        placeholder="Запомнить..."
        on:keydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); void addMemory(); } }}
      />
      <button type="button" disabled={!$memoryDraft.trim()} on:click={addMemory}>+</button>
    </div>
    <div class="memory-ledger">
      {#each $memories as memory}
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

<style>
  .conversation-row {
    background: transparent;
  }
  .conversation-row:hover {
    background: var(--bg-input);
  }
  .conversation-row:hover .action-buttons {
    opacity: 1 !important;
  }
  .conversation-row.active {
    background: var(--bg-primary-hover);
    border-left: 3px solid var(--color-brand);
    border-top-left-radius: 0;
    border-bottom-left-radius: 0;
  }
  .icon-btn:hover {
    filter: brightness(1.2);
  }
</style>
