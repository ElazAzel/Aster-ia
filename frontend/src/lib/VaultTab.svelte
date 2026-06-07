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
    ragFolderScopes,
    removeRagDocument,
    removeRagFolderScope,
    refreshRagDocuments,
    refreshRagFolderScopes,
    roomDraft,
    addRoom,
    rooms,
    // File upload stores/methods
    uploadFile,
    uploadBusy,
    uploadResult,
    uploadVaultFile,
    desktopAvailable,
    localFilePath,
    indexLocalVaultFile,
    showToast
  } from './stores';
  import { pickRagFile } from './tauri';

  async function handleBrowse() {
    const path = await pickRagFile();
    if (path) {
      $localFilePath = path;
      await indexLocalVaultFile();
    }
  }

  let isDragging = false;

  function handleDragOver(e: DragEvent) {
    e.preventDefault();
    isDragging = true;
  }

  function handleDragLeave() {
    isDragging = false;
  }

  async function handleDrop(e: DragEvent) {
    e.preventDefault();
    isDragging = false;
    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      const droppedFile = files[0];
      const name = droppedFile.name.toLowerCase();
      if (name.endsWith('.pdf') || name.endsWith('.docx') || name.endsWith('.txt') || name.endsWith('.md')) {
        $uploadFile = droppedFile;
        await uploadVaultFile();
      } else {
        showToast('Поддерживаются только .pdf, .docx, .txt, .md файлы', 'error');
      }
    }
  }
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
      <!-- Search Panel -->
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

      <!-- Upload Panel -->
      <section class="panel">
        <div class="panel-heading compact">
          <h2>Добавить знания в Vault</h2>
        </div>
        
        <p style="font-size:13px;color:var(--text-secondary)">
          Добавьте локальные документы для контекстного поиска (RAG) в текущей комнате.
        </p>

        {#if $desktopAvailable}
          <div class="desktop-picker-section" style="display:flex;flex-direction:column;gap:12px;margin-bottom:12px;">
            <div style="display:flex;gap:12px;align-items:center;">
              <input type="text" readonly placeholder="Путь к локальному файлу..." bind:value={$localFilePath} style="flex:1;font-size:12px;padding:8px 10px;" />
              <button type="button" class="secondary" on:click={handleBrowse} style="min-height:36px;padding:0 12px;font-size:12px;">Обзор...</button>
            </div>
            {#if $localFilePath}
              <button type="button" on:click={indexLocalVaultFile} disabled={$uploadBusy} style="width:100%;font-size:13px;">
                {$uploadBusy ? 'Индексирую локальный файл...' : '📁 Проиндексировать выбранный файл'}
              </button>
            {/if}
          </div>
        {/if}

        <label
          class="drop-zone"
          class:dragging={isDragging}
          on:dragover|preventDefault={handleDragOver}
          on:dragleave={handleDragLeave}
          on:drop|preventDefault={handleDrop}
          style="display:block;cursor:pointer;padding:36px 20px;border:2px dashed var(--border-color);border-radius:12px;text-align:center;transition:var(--transition-smooth);background:rgba(255,255,255,0.01);"
        >
          <input
            type="file"
            accept=".pdf,.docx,.txt,.md"
            style="display:none"
            on:change={async (e) => {
              const files = (e.target as HTMLInputElement).files;
              if (files && files.length > 0) {
                $uploadFile = files[0];
                await uploadVaultFile();
              }
            }}
          />
          
          <div class="drop-zone-content" style="display:flex;flex-direction:column;align-items:center;gap:10px;">
            <span style="font-size:32px;">📥</span>
            {#if $uploadBusy}
              <span style="font-size:13px;color:var(--color-brand);font-weight:600;">Индексация документа...</span>
            {:else if $uploadFile}
              <span style="font-size:13px;color:var(--color-brand);font-weight:600;">Выбран: {$uploadFile.name}</span>
              <span style="font-size:11px;color:var(--text-muted);">Нажмите или перетащите для замены</span>
            {:else}
              <span style="font-size:13px;color:var(--text-secondary);font-weight:500;">Перетащите файл сюда или нажмите для обзора</span>
              <span style="font-size:11px;color:var(--text-muted);">Поддерживаются .pdf, .docx, .txt, .md</span>
            {/if}
          </div>
        </label>

        {#if $uploadResult}
          <div class="plan-box" style="margin-top:8px;padding:12px;border:1px solid var(--color-green-border);background:var(--color-green-glow);border-radius:8px;">
            <strong style="color:var(--color-green-text);font-size:13px;display:block;margin-bottom:4px;">✓ Успешно проиндексировано</strong>
            <p style="font-size:12px;margin:0;color:var(--text-secondary);">{$uploadResult.source} ({$uploadResult.indexed_chunks} сегментов)</p>
          </div>
        {/if}
      </section>

      <!-- Documents Panel -->
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

      <section class="panel">
        <div class="panel-heading compact">
          <h2>Разрешенные папки RAG</h2>
          <button type="button" class="text-button" on:click={refreshRagFolderScopes}>Обновить</button>
        </div>
        <div class="result-list" style="max-height: 320px;">
          {#each $ragFolderScopes as scope}
            <article>
              <strong>{scope.label || scope.path}</strong>
              <small>{scope.path} · Комната: {scope.room_id} · {scope.recursive ? 'с подпапками' : 'только папка'}</small>
              <button type="button" class="text-button" on:click={() => removeRagFolderScope(scope.id)}>Отозвать доступ</button>
            </article>
          {:else}
            <p class="empty">Для этой комнаты пока нет разрешенных папок RAG.</p>
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

<style>
  .drop-zone {
    transition: border-color 0.2s, background-color 0.2s, transform 0.2s;
  }
  .drop-zone:hover {
    border-color: var(--color-brand) !important;
    background: rgba(124, 109, 250, 0.03) !important;
  }
  .drop-zone.dragging {
    border-color: var(--color-brand) !important;
    background: rgba(124, 109, 250, 0.08) !important;
    transform: scale(0.98);
  }
</style>
