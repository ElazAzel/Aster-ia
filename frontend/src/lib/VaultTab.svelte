<script lang="ts">
  import {
    activeVaultTab,
    memories,
    memoryDraft,
    addMemory,
    removeMemory,
    ragQuery,
    runRagSearch,
    ragResults,
    ragDocuments,
    removeRagDocument,
    refreshRagDocuments,
    roomDraft,
    addRoom,
    rooms
  } from './stores';
</script>

<div class="tab-content">
  <!-- Sub navigation tabs within Vault -->
  <div class="knowledge-tabs">
    <button class:active={$activeVaultTab === 'memory'} on:click={() => $activeVaultTab = 'memory'}>Память контекста (Ledger)</button>
    <button class:active={$activeVaultTab === 'rag'} on:click={() => $activeVaultTab = 'rag'}>Поиск и файлы RAG (Vault)</button>
    <button class:active={$activeVaultTab === 'rooms'} on:click={() => $activeVaultTab = 'rooms'}>Комнаты окружения</button>
  </div>

  {#if $activeVaultTab === 'memory'}
    <div class="secondary-grid">
      <section class="panel">
        <div class="panel-heading compact">
          <h2>Журнал долгосрочной памяти комнаты</h2>
          <span class="count">{ $memories.length } записей</span>
        </div>
        <form on:submit|preventDefault={addMemory} class="stack-form">
          <textarea bind:value={$memoryDraft} placeholder="Введите новое утверждение для фиксации в памяти комнаты..." rows="3"></textarea>
          <button type="submit" disabled={!$memoryDraft.trim()}>Добавить в Ledger</button>
        </form>
      </section>

      <section class="panel">
        <div class="panel-heading compact">
          <h2>Активные воспоминания в памяти</h2>
        </div>
        <div class="memory-list">
          {#each $memories as memory}
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

  {:else if $activeVaultTab === 'rag'}
    <div class="secondary-grid">
      <section class="panel">
        <div class="panel-heading compact">
          <h2>Локальный RAG-поиск</h2>
        </div>
        <form on:submit|preventDefault={runRagSearch} class="stack-form">
          <input bind:value={$ragQuery} placeholder="Запрос по локальному индексу..." />
          <button type="submit" disabled={!$ragQuery.trim()}>Искать по базе</button>
        </form>
        <div class="result-list" style="margin-top: 12px; max-height: 380px;">
          {#each $ragResults as chunk}
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
          {#each $ragDocuments as document}
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

  {:else if $activeVaultTab === 'rooms'}
    <div class="secondary-grid">
      <section class="panel">
        <div class="panel-heading compact">
          <h2>Создать комнату окружения</h2>
        </div>
        <form on:submit|preventDefault={addRoom} class="stack-form">
          <input bind:value={$roomDraft} placeholder="Название комнаты контекста..." />
          <button type="submit" disabled={!$roomDraft.trim()}>Создать комнату</button>
        </form>
      </section>

      <section class="panel">
        <div class="panel-heading compact">
          <h2>Существующие комнаты</h2>
          <span class="count">{$rooms.length}</span>
        </div>
        <div class="memory-list">
          {#each $rooms as room}
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
