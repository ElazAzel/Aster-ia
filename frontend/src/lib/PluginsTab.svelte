<script lang="ts">
  import {
    plugins,
    uploadFile,
    uploadBusy,
    uploadResult,
    uploadVaultFile
  } from './stores';
</script>

<div class="tab-content">
  <div class="secondary-grid">
    <section class="panel">
      <div class="panel-heading compact">
        <h2>Plugin Manager</h2>
        <span class="count">{$plugins.length} плагинов</span>
      </div>
      <div class="plan-box" style="margin-top:0;background:var(--bg-input)">
        <p style="font-size:12px;color:var(--text-secondary)">Плагины загружаются из <code style="background:var(--bg-card);padding:2px 6px;border-radius:4px;font-family:var(--font-mono)">~/.asterion/plugins/*/manifest.json</code></p>
      </div>
      <div class="result-list" style="max-height:400px">
        {#each $plugins as plugin}
          <article>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <strong>{plugin.name}</strong>
              <span style="font-size:10px;padding:2px 6px;border-radius:4px;background:var(--bg-input);border:1px solid var(--border-color);color:var(--text-secondary)">{plugin.trust_level}</span>
            </div>
            {#if plugin.description}
              <p style="font-size:12px;color:var(--text-secondary)">{plugin.description}</p>
            {/if}
            <small style="font-family:var(--font-mono)">{plugin.path}</small>
          </article>
        {:else}
          <p class="empty">Плагины не найдены. Создайте папку с manifest.json в ~/.asterion/plugins/</p>
        {/each}
      </div>
    </section>
    <section class="panel">
      <div class="panel-heading compact"><h2>Загрузить файл в Vault</h2></div>
      <p style="font-size:13px;color:var(--text-secondary)">Загрузите PDF или TXT для индексации в Knowledge Vault текущей комнаты.</p>
      <label
        style="display:block;cursor:pointer;padding:20px;border:2px dashed var(--border-color);border-radius:10px;text-align:center;transition:var(--transition-smooth)"
        on:dragover|preventDefault
        on:drop|preventDefault={(e) => { $uploadFile = e.dataTransfer?.files[0] ?? null; }}
      >
        <input type="file" accept=".pdf,.txt,.md,.docx,.csv" style="display:none" on:change={(e) => { $uploadFile = (e.target as HTMLInputElement).files?.[0] ?? null; }} />
        {#if $uploadFile}
          <span style="font-size:14px;color:var(--color-brand)">{$uploadFile.name}</span>
        {:else}
          <span style="font-size:13px;color:var(--text-muted)">Нажмите или перетащите файл сюда</span>
        {/if}
      </label>
      <button type="button" on:click={uploadVaultFile} disabled={!$uploadFile || $uploadBusy} style="margin-top:8px">
        {$uploadBusy ? 'Индексирую...' : '📁 Загрузить и индексировать'}
      </button>
      {#if $uploadResult}
        <div class="plan-box" style="margin-top:8px">
          <strong>✓ Проиндексировано</strong>
          <p style="font-size:12px">{$uploadResult.source} — {$uploadResult.indexed_chunks} чанков</p>
        </div>
      {/if}
    </section>
  </div>
</div>
