<script lang="ts">
  import {
    plugins,
    uploadFile,
    uploadBusy,
    uploadResult,
    uploadVaultFile,
    desktopAvailable,
    localFilePath,
    indexLocalVaultFile,
    openDesignSourcePath,
    openDesignPreview,
    openDesignPreviewBusy,
    openDesignSearchQuery,
    openDesignSelectedCandidate,
    previewOpenDesignCatalog,
    stageOpenDesignCandidate
  } from './stores';
  import type { OpenDesignSkillCandidate } from './api';
  import { pickRagFile } from './tauri';

  async function handleBrowse() {
    const path = await pickRagFile();
    if (path) {
      $localFilePath = path;
    }
  }

  function selectCandidate(candidate: OpenDesignSkillCandidate) {
    $openDesignSelectedCandidate = candidate;
  }

  function consentTone(candidate: OpenDesignSkillCandidate) {
    const consents = candidate.manifest.requires_consent;
    if (consents.includes('external_api') || consents.includes('shell')) return 'red';
    if (consents.length > 0) return 'yellow';
    return 'green';
  }

  function privacyLabel(candidate: OpenDesignSkillCandidate) {
    const consents = candidate.manifest.requires_consent;
    if (consents.includes('external_api')) return 'Внешний API';
    if (consents.includes('shell')) return 'Терминал';
    if (consents.includes('public_web')) return 'Веб-доступ';
    if (consents.includes('file_write')) return 'Запись файлов';
    return 'Локально';
  }

  function matchesCandidate(candidate: OpenDesignSkillCandidate) {
    const query = $openDesignSearchQuery.trim().toLowerCase();
    if (!query) return true;
    const haystack = [
      candidate.manifest.name,
      candidate.manifest.category,
      candidate.manifest.description,
      candidate.mode ?? '',
      candidate.upstream ?? '',
      candidate.manifest.triggers.join(' ')
    ].join(' ').toLowerCase();
    return haystack.includes(query);
  }

  $: candidates = $openDesignPreview?.candidates ?? [];
  $: filteredCandidates = candidates.filter(matchesCandidate);
  $: localCandidates = candidates.filter((candidate) => candidate.manifest.requires_consent.length === 0).length;
  $: elevatedCandidates = Math.max(0, candidates.length - localCandidates);
  $: selected = $openDesignSelectedCandidate ?? filteredCandidates[0] ?? null;
</script>

<div class="tab-content plugins-workspace">
  <section class="extension-hero">
    <div>
      <p class="eyebrow">Расширения платформы</p>
      <h2>Open Design и локальные плагины</h2>
      <p>
        Единая панель для проверки локальных plugin manifest и безопасного просмотра Open Design
        skills. Preview не выполняет инструкции, не скачивает upstream assets и не запускает скрипты.
      </p>
    </div>
    <div class="hero-metrics" aria-label="Сводка расширений">
      <div>
        <strong>{$plugins.length}</strong>
        <span>плагинов</span>
      </div>
      <div>
        <strong>{$openDesignPreview?.scanned_count ?? 0}</strong>
        <span>OD skills</span>
      </div>
      <div>
        <strong>{elevatedCandidates}</strong>
        <span>consent gates</span>
      </div>
    </div>
  </section>

  <div class="extensions-grid">
    <section class="panel extension-panel">
      <div class="panel-heading compact">
        <div>
          <p class="eyebrow">Trust registry</p>
          <h2>Plugin Manager</h2>
        </div>
        <span class="count">{$plugins.length}</span>
      </div>
      <p class="helper-text">
        Локальные плагины читаются из
        <code>~/.asterion/plugins/*/manifest.json</code>. Elevated trust остается заблокированным до согласия.
      </p>

      <div class="result-list plugin-list">
        {#each $plugins as plugin}
          <article>
            <div class="card-row">
              <strong>{plugin.name}</strong>
              <span class="trust-pill">{plugin.trust_level}</span>
            </div>
            {#if plugin.description}
              <p>{plugin.description}</p>
            {/if}
            <small>{plugin.path}</small>
          </article>
        {:else}
          <div class="empty-state-card">
            <strong>Плагины не найдены</strong>
            <p>Добавьте локальный `manifest.json` в `~/.asterion/plugins/`, затем обновите каталог.</p>
          </div>
        {/each}
      </div>
    </section>

    <section class="panel extension-panel open-design-panel">
      <div class="panel-heading compact">
        <div>
          <p class="eyebrow">Open Design</p>
          <h2>Skill Explorer</h2>
        </div>
        <span class="count">{$openDesignPreview?.returned_count ?? 0}</span>
      </div>

      <div class="path-row">
        <label>
          <span>Папка skills</span>
          <input
            bind:value={$openDesignSourcePath}
            placeholder="%LOCALAPPDATA%\Programs\Open Design\resources\open-design\skills"
            autocomplete="off"
          />
        </label>
        <button type="button" on:click={previewOpenDesignCatalog} disabled={!$openDesignSourcePath.trim() || $openDesignPreviewBusy}>
          {$openDesignPreviewBusy ? 'Сканирую' : 'Сканировать'}
        </button>
      </div>

      <div class="od-toolbar">
        <input
          bind:value={$openDesignSearchQuery}
          placeholder="Поиск: platform, figma, image, frontend..."
          aria-label="Поиск Open Design skills"
        />
        <div class="scan-summary">
          <span class="risk-pill risk-green">{localCandidates} local</span>
          <span class="risk-pill risk-yellow">{elevatedCandidates} gated</span>
        </div>
      </div>

      {#if $openDesignPreviewBusy}
        <div class="skeleton-stack" aria-live="polite">
          <span class="skeleton skeleton-text"></span>
          <span class="skeleton skeleton-text short"></span>
          <span class="skeleton skeleton-card"></span>
        </div>
      {:else}
        {#if $openDesignPreview?.warnings.length}
          <div class="scan-warning" aria-live="polite">
            <strong>Ограничения preview</strong>
            <ul>
              {#each $openDesignPreview.warnings as warning}
                <li>{warning}</li>
              {/each}
            </ul>
          </div>
        {/if}
      {/if}

      {#if !$openDesignPreviewBusy && filteredCandidates.length > 0}
        <div class="od-list" role="listbox" aria-label="Open Design skill candidates">
          {#each filteredCandidates as candidate}
            <button
              type="button"
              role="option"
              aria-selected={selected?.content_sha256 === candidate.content_sha256}
              class:active={selected?.content_sha256 === candidate.content_sha256}
              on:click={() => selectCandidate(candidate)}
            >
              <span class="candidate-main">
                <strong>{candidate.manifest.name}</strong>
                <small>{candidate.manifest.category} · {candidate.mode ?? 'skill'}</small>
              </span>
              <span class="risk-pill risk-{consentTone(candidate)}">{privacyLabel(candidate)}</span>
            </button>
          {/each}
        </div>
      {:else if !$openDesignPreviewBusy && $openDesignPreview}
        <div class="empty-state-card">
          <strong>Ничего не найдено</strong>
          <p>Уточните запрос или сбросьте фильтр поиска.</p>
        </div>
      {:else if !$openDesignPreviewBusy}
        <div class="empty-state-card">
          <strong>Каталог еще не просканирован</strong>
          <p>Нажмите «Сканировать», чтобы получить локальный preview Open Design skills.</p>
        </div>
      {/if}
    </section>

    <section class="panel extension-panel detail-panel">
      <div class="panel-heading compact">
        <div>
          <p class="eyebrow">Review</p>
          <h2>Кандидат к применению</h2>
        </div>
      </div>

      {#if selected}
        <div class="candidate-detail">
          <div>
            <h3>{selected.manifest.name}</h3>
            <p>{selected.manifest.description}</p>
          </div>

          <dl>
            <div>
              <dt>Категория</dt>
              <dd>{selected.manifest.category}</dd>
            </div>
            <div>
              <dt>Privacy</dt>
              <dd>{selected.manifest.privacy_level}</dd>
            </div>
            <div>
              <dt>Hash</dt>
              <dd>{selected.content_sha256.slice(0, 12)}</dd>
            </div>
          </dl>

          <div>
            <h4>Consent gates</h4>
            <div class="chip-row">
              {#each selected.manifest.requires_consent as consent}
                <span>{consent}</span>
              {:else}
                <span>local-only</span>
              {/each}
            </div>
          </div>

          <div>
            <h4>Источник</h4>
            <code class="source-path">{selected.source_path}</code>
          </div>

          {#if selected.warnings.length > 0}
            <div class="warning-box">
              <strong>Предупреждения</strong>
              <ul>
                {#each selected.warnings as warning}
                  <li>{warning}</li>
                {/each}
              </ul>
            </div>
          {/if}

          <button type="button" on:click={() => stageOpenDesignCandidate(selected)}>
            Перенести в Agent Lab
          </button>
        </div>
      {:else}
        <div class="empty-state-card">
          <strong>Выберите skill</strong>
          <p>После выбора Asterion покажет источник, hash и consent gates для безопасного применения.</p>
        </div>
      {/if}
    </section>
  </div>

  <section class="panel vault-strip">
    <div>
      <p class="eyebrow">Knowledge Vault</p>
      <h2>Индексировать источник</h2>
      <p>Добавляйте документы в текущую комнату без смешивания с Open Design preview.</p>
    </div>

    {#if $desktopAvailable}
      <div class="vault-actions">
        <input type="text" readonly placeholder="Путь к файлу..." bind:value={$localFilePath} />
        <button type="button" class="secondary" on:click={handleBrowse}>Обзор</button>
        <button type="button" on:click={indexLocalVaultFile} disabled={!$localFilePath || $uploadBusy}>
          {$uploadBusy ? 'Индексирую' : 'Индексировать'}
        </button>
      </div>
    {:else}
      <label
        class="drop-zone"
        on:dragover|preventDefault
        on:drop|preventDefault={(event) => { $uploadFile = event.dataTransfer?.files[0] ?? null; }}
      >
        <input
          type="file"
          accept=".pdf,.txt,.md,.docx,.csv"
          on:change={(event) => { $uploadFile = (event.target as HTMLInputElement).files?.[0] ?? null; }}
        />
        <span>{$uploadFile ? $uploadFile.name : 'Выберите или перетащите PDF, DOCX, TXT, MD, CSV'}</span>
      </label>
      <button type="button" on:click={uploadVaultFile} disabled={!$uploadFile || $uploadBusy}>
        {$uploadBusy ? 'Индексирую' : 'Загрузить и индексировать'}
      </button>
    {/if}

    {#if $uploadResult}
      <div class="indexed-result" aria-live="polite">
        <strong>Проиндексировано</strong>
        <span>{$uploadResult.source} · {$uploadResult.indexed_chunks} чанков</span>
      </div>
    {/if}
  </section>
</div>

<style>
  .plugins-workspace {
    gap: 16px;
    overflow-y: auto;
  }

  .extension-hero {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 20px;
    align-items: center;
    padding: 20px;
    border: 1px solid var(--border-color);
    border-radius: 12px;
    background: linear-gradient(135deg, rgba(124, 109, 250, 0.1), rgba(48, 201, 126, 0.04));
  }

  .extension-hero h2 {
    font-size: 24px;
    margin-bottom: 6px;
  }

  .extension-hero p {
    color: var(--text-secondary);
    font-size: 13.5px;
    line-height: 1.5;
    max-width: 760px;
  }

  .hero-metrics {
    display: grid;
    grid-template-columns: repeat(3, 96px);
    gap: 8px;
  }

  .hero-metrics div {
    min-height: 72px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 2px;
    padding: 10px;
    border-radius: 10px;
    background: var(--bg-input);
    border: 1px solid var(--border-color);
  }

  .hero-metrics strong {
    font-size: 22px;
  }

  .hero-metrics span,
  .helper-text,
  .scan-summary {
    color: var(--text-secondary);
    font-size: 12px;
  }

  .extensions-grid {
    display: grid;
    grid-template-columns: minmax(260px, 0.85fr) minmax(360px, 1.25fr) minmax(320px, 1fr);
    gap: 16px;
    min-height: 540px;
  }

  .extension-panel {
    min-height: 0;
  }

  .plugin-list,
  .od-list {
    max-height: none;
    flex: 1;
  }

  .card-row,
  .path-row,
  .od-toolbar,
  .vault-actions {
    display: flex;
    gap: 10px;
    align-items: center;
  }

  .card-row {
    justify-content: space-between;
  }

  .trust-pill {
    font-size: 10px;
    padding: 3px 7px;
    border-radius: 6px;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    color: var(--text-secondary);
    white-space: nowrap;
  }

  .path-row {
    align-items: end;
  }

  .path-row label {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .path-row label span,
  .candidate-detail dt {
    color: var(--text-muted);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  .path-row button,
  .vault-actions button,
  .drop-zone,
  .candidate-detail button {
    min-height: 44px;
  }

  .od-toolbar input {
    flex: 1;
  }

  .scan-summary {
    display: flex;
    gap: 6px;
    white-space: nowrap;
  }

  .od-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    overflow-y: auto;
  }

  .od-list button {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 10px;
    align-items: center;
    padding: 12px;
    background: var(--bg-input);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    text-align: left;
  }

  .od-list button:hover,
  .od-list button.active {
    background: var(--bg-card-hover);
    border-color: var(--color-brand);
  }

  .candidate-main {
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .candidate-main strong {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .candidate-main small {
    color: var(--text-secondary);
  }

  .candidate-detail {
    display: flex;
    flex-direction: column;
    gap: 16px;
    overflow-y: auto;
  }

  .candidate-detail h3 {
    font-size: 20px;
    margin-bottom: 6px;
  }

  .candidate-detail h4 {
    font-size: 12px;
    margin-bottom: 8px;
    color: var(--text-secondary);
    text-transform: uppercase;
  }

  .candidate-detail p {
    color: var(--text-secondary);
    font-size: 13.5px;
    line-height: 1.5;
  }

  .candidate-detail dl {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
  }

  .candidate-detail dl div {
    padding: 10px;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    background: var(--bg-input);
    min-width: 0;
  }

  .candidate-detail dd {
    margin-top: 3px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .source-path {
    display: block;
    padding: 10px;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    background: var(--bg-input);
    color: var(--text-secondary);
    font-size: 11px;
    overflow-wrap: anywhere;
  }

  .warning-box,
  .scan-warning,
  .empty-state-card,
  .indexed-result {
    border: 1px solid var(--border-color);
    border-radius: 10px;
    background: var(--bg-input);
    padding: 14px;
  }

  .warning-box,
  .scan-warning {
    border-color: var(--color-yellow-border);
    background: var(--color-yellow-glow);
  }

  .warning-box ul,
  .scan-warning ul {
    margin: 8px 0 0 18px;
    color: var(--text-secondary);
    font-size: 12px;
    line-height: 1.4;
  }

  .empty-state-card p {
    color: var(--text-secondary);
    font-size: 12.5px;
    line-height: 1.5;
    margin-top: 6px;
  }

  .skeleton-stack {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .vault-strip {
    display: grid;
    grid-template-columns: minmax(260px, 0.6fr) minmax(0, 1fr) auto;
    gap: 14px;
    align-items: center;
  }

  .vault-strip p {
    color: var(--text-secondary);
    font-size: 13px;
  }

  .vault-actions {
    min-width: 0;
  }

  .drop-zone {
    display: flex;
    align-items: center;
    justify-content: center;
    border: 2px dashed var(--border-color);
    border-radius: 10px;
    padding: 12px 16px;
    cursor: pointer;
    color: var(--text-secondary);
    text-align: center;
  }

  .drop-zone:hover {
    border-color: var(--color-brand);
    color: var(--text-primary);
  }

  .drop-zone input {
    display: none;
  }

  .indexed-result {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 180px;
  }

  .indexed-result span {
    color: var(--text-secondary);
    font-size: 12px;
  }

  @media (max-width: 1200px) {
    .extensions-grid,
    .vault-strip,
    .extension-hero {
      grid-template-columns: 1fr;
    }

    .hero-metrics {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
  }

  @media (max-width: 720px) {
    .card-row,
    .path-row,
    .od-toolbar,
    .vault-actions {
      flex-direction: column;
      align-items: stretch;
    }

    .hero-metrics {
      grid-template-columns: 1fr;
    }
  }
</style>
