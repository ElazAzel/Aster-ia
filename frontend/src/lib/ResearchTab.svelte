<script lang="ts">
  import {
    researchQuery,
    researchClaim,
    researchSourceTitle,
    exportedReport,
    exportResearchArtifact
  } from './stores';
</script>

<div class="tab-content">
  <div class="secondary-grid">
    <section class="panel">
      <div class="panel-heading compact">
        <h2>Регистрация фактов исследований (Research Receipts)</h2>
      </div>
      <form on:submit|preventDefault={exportResearchArtifact} class="stack-form">
        <label style="display: flex; flex-direction: column; gap: 4px;">
          <span style="font-size: 11px; font-weight: 600; color: var(--text-secondary);">Цель исследования</span>
          <input bind:value={$researchQuery} placeholder="Например: Сравнить скорость локального вывода" />
        </label>

        <label style="display: flex; flex-direction: column; gap: 4px;">
          <span style="font-size: 11px; font-weight: 600; color: var(--text-secondary);">Название источника</span>
          <input bind:value={$researchSourceTitle} placeholder="Например: Статья или лог" />
        </label>

        <label style="display: flex; flex-direction: column; gap: 4px;">
          <span style="font-size: 11px; font-weight: 600; color: var(--text-secondary);">Утверждение / Доказательство</span>
          <textarea bind:value={$researchClaim} rows="4" placeholder="Текст утверждения..."></textarea>
        </label>

        <button type="submit" disabled={!$researchQuery.trim() || !$researchClaim.trim()}>Экспортировать Artifact</button>
      </form>
    </section>

    <section class="panel">
      <div class="panel-heading compact">
        <h2>Результат экспорта</h2>
      </div>
      {#if $exportedReport}
        <div class="plan-box" style="margin-top: 0;">
          <strong>{$exportedReport.artifact.title}</strong>
          <small>Связано фактов: {$exportedReport.receipts_count} · ID артефакта: {$exportedReport.artifact.id}</small>
          <div style="background: var(--bg-app); padding: 12px; border-radius: 8px; border: 1px solid var(--border-color); margin-top: 8px;">
            <p style="font-size: 12px; line-height: 1.5; font-family: var(--font-mono);">{$exportedReport.artifact.source}</p>
          </div>
        </div>
      {:else}
        <p class="empty">Экспортируйте протокол, чтобы просмотреть результаты генерации артефакта.</p>
      {/if}
    </section>
  </div>
</div>
