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
    showLeftPanel
  } from './stores';
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
        bind:value={$roomDraft}
        placeholder="Название..."
        on:keydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); void addRoom(); } }}
      />
      <button type="button" disabled={!$roomDraft.trim()} on:click={addRoom}>+</button>
    </div>
  </div>

  <!-- Model Selector -->
  <div class="left-panel-section" style="border-bottom: 1px solid var(--border-color);">
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
  <div class="left-panel-section" style="flex: 1; overflow: hidden; display: flex; flex-direction: column;">
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
