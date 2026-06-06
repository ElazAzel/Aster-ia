<script lang="ts">
  import {
    exportedReport,
    researchClaim,
    researchQuery,
    researchSourceTitle
  } from './stores';

  type ArtifactLike = {
    artifact?: {
      id: string;
      title: string;
      kind: string;
      blocks?: Array<{ type: string; title?: string | null; content?: string | null }>;
      source?: string;
    };
    receipts_count?: number;
  };

  $: report = $exportedReport as ArtifactLike | null;
  $: blocks = report?.artifact?.blocks ?? [];
</script>

<section class="panel" style="grid-column: span 2;">
  <div class="panel-heading compact">
    <h2>Research Canvas</h2>
    {#if report?.artifact}
      <span class="count">{report.receipts_count ?? 0} receipts</span>
    {/if}
  </div>

  <div class="research-canvas-grid">
    <div class="canvas-column">
      <span class="canvas-label">Goal</span>
      <strong>{$researchQuery || 'Нет цели исследования'}</strong>
      <small>Canvas собирает цель, источник, claim и экспортированный artifact в один обзор.</small>
    </div>

    <div class="canvas-column">
      <span class="canvas-label">Source</span>
      <strong>{$researchSourceTitle || 'Manual source'}</strong>
      <p>{$researchClaim || 'Claim пока не заполнен.'}</p>
    </div>

    <div class="canvas-column">
      <span class="canvas-label">Artifact</span>
      {#if report?.artifact}
        <strong>{report.artifact.title}</strong>
        <small>{report.artifact.kind} · {report.artifact.id}</small>
      {:else}
        <p>Экспортируйте Research Receipt, чтобы увидеть структуру artifact.</p>
      {/if}
    </div>
  </div>

  {#if blocks.length > 0}
    <div class="canvas-blocks">
      {#each blocks as block}
        <div class="canvas-block">
          <span>{block.type}</span>
          <strong>{block.title || 'Block'}</strong>
          {#if block.content}
            <p>{block.content}</p>
          {/if}
        </div>
      {/each}
    </div>
  {:else}
    <p class="empty" style="margin-top: 12px;">Пока нет block-level данных. Создайте research artifact.</p>
  {/if}
</section>

<style>
  .research-canvas-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }

  .canvas-column,
  .canvas-block {
    background: var(--bg-input);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 12px;
    min-width: 0;
  }

  .canvas-column {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .canvas-label,
  .canvas-block span {
    color: var(--text-muted);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .canvas-column strong,
  .canvas-block strong {
    color: var(--text-primary);
    font-size: 13px;
    overflow-wrap: anywhere;
  }

  .canvas-column p,
  .canvas-column small,
  .canvas-block p {
    color: var(--text-secondary);
    font-size: 12px;
    line-height: 1.45;
    margin: 0;
    overflow-wrap: anywhere;
  }

  .canvas-blocks {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin-top: 12px;
  }

  @media (max-width: 900px) {
    .research-canvas-grid,
    .canvas-blocks {
      grid-template-columns: 1fr;
    }
  }
</style>
