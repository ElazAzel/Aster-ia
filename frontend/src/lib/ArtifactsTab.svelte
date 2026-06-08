<script lang="ts">
  import { allArtifacts, refreshArtifacts } from './stores';
</script>

<div class="tab-content">
  <section class="panel" style="flex:1;overflow:hidden">
    <div class="panel-heading compact">
      <h2>Хранилище артефактов</h2>
      <div style="display:flex;gap:8px;align-items:center">
        <span class="count">{$allArtifacts.length} артефактов</span>
        <button type="button" class="text-button" on:click={refreshArtifacts}>Обновить</button>
      </div>
    </div>
    <div class="result-list" style="max-height:calc(100vh - 200px)">
      {#each $allArtifacts as artifact}
        <article>
          <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <strong>{artifact.title}</strong>
            <span style="font-size:10px;padding:2px 6px;border-radius:4px;background:var(--color-brand-glow);border:1px solid var(--color-brand);color:var(--color-brand-text);text-transform:uppercase">{artifact.kind}</span>
          </div>
          <small>Комната: {artifact.room_id} · Блоков: {artifact.blocks.length} · {new Date(artifact.created_at).toLocaleString('ru')}</small>
          {#if artifact.blocks[0]?.content}
            <p style="font-size:12px;color:var(--text-secondary);line-height:1.4;margin-top:4px">{artifact.blocks[0].content.slice(0, 200)}{artifact.blocks[0].content.length > 200 ? '...' : ''}</p>
          {/if}
        </article>
      {:else}
        <p class="empty">Артефактов пока нет. Начните чат или создайте исследование.</p>
      {/each}
    </div>
  </section>
</div>
