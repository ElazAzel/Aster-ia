<script lang="ts">
  import {
    researchDeepQuery,
    deepResearchBusy,
    deepResearchResult,
    runDeepResearch,
    contradictionClaims,
    contradictions,
    runContradictionFinder
  } from './stores';
</script>

<div class="tab-content">
  <div class="secondary-grid">
    <section class="panel">
      <div class="panel-heading compact">
        <h2>Deep Research Studio</h2>
        <span class="risk-pill {$deepResearchResult?.privacy?.level ? `risk-${$deepResearchResult.privacy.level}` : ''}">
          {$deepResearchResult?.privacy?.level ?? '—'}
        </span>
      </div>
      <form on:submit|preventDefault={runDeepResearch} class="stack-form">
        <label style="display:flex;flex-direction:column;gap:4px">
          <span style="font-size:11px;font-weight:600;color:var(--text-secondary)">Цель исследования</span>
          <input bind:value={$researchDeepQuery} placeholder="Например: Сравнить privacy-модели RAG систем..." />
        </label>
        <button type="submit" disabled={$deepResearchBusy || !$researchDeepQuery.trim()}>
          {$deepResearchBusy ? 'Исследую...' : 'Запустить Deep Research'}
        </button>
      </form>

      {#if $deepResearchResult}
        <div class="plan-box" style="margin-top:0">
          <strong>Запрос: {$deepResearchResult.query}</strong>
          <div>
            <p style="font-size:11px;font-weight:600;color:var(--text-secondary);margin-bottom:6px">Подзадачи ({$deepResearchResult.subtasks.length})</p>
            <ol style="padding-left:16px;font-size:12px;color:var(--text-secondary);display:flex;flex-direction:column;gap:4px">
              {#each $deepResearchResult.subtasks as subtask}
                <li>{subtask}</li>
              {/each}
            </ol>
          </div>
        </div>
      {/if}
    </section>

    <section class="panel">
      <div class="panel-heading compact">
        <h2>Результаты ({$deepResearchResult?.results?.length ?? 0})</h2>
      </div>
      <div class="result-list" style="max-height:500px">
        {#each $deepResearchResult?.results ?? [] as result}
          <article>
            <strong>{result.title}</strong>
            {#if result.url}
              <small><a href={result.url} target="_blank" rel="noreferrer" style="color:var(--color-brand)">{result.url}</a></small>
            {/if}
            {#if result.snippet}
              <p style="font-size:12px;line-height:1.5;color:var(--text-secondary)">{result.snippet}</p>
            {/if}
            <small style="color:var(--text-muted)">Подзадача: {result.subtask}</small>
          </article>
        {:else}
          <p class="empty">Запустите исследование для получения результатов.</p>
        {/each}
      </div>
    </section>

    <section class="panel" style="grid-column:span 2">
      <div class="panel-heading compact">
        <h2>Contradiction Finder</h2>
        <span class="count">{$contradictions.length} противоречий</span>
      </div>
      <form on:submit|preventDefault={runContradictionFinder} class="stack-form">
        <label style="display:flex;flex-direction:column;gap:4px">
          <span style="font-size:11px;font-weight:600;color:var(--text-secondary)">Утверждения (одно на строку, минимум 2)</span>
          <textarea bind:value={$contradictionClaims} rows="4" placeholder="Первое утверждение&#10;Второе утверждение&#10;..."></textarea>
        </label>
        <button type="submit" disabled={$contradictionClaims.split('\n').filter(s => s.trim()).length < 2}>
          Найти противоречия
        </button>
      </form>
      {#if $contradictions.length > 0}
        <div class="result-list" style="max-height:300px">
          {#each $contradictions as match}
            <article style="border-left:3px solid var(--color-red);padding-left:12px">
              <strong style="color:var(--color-red-text);font-size:12px">Similarity: {(match.similarity * 100).toFixed(1)}%</strong>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:8px">
                <div style="padding:8px;background:var(--bg-input);border-radius:6px">
                  <small style="color:var(--text-muted)">{match.sentiment_left}</small>
                  <p style="font-size:12px;margin-top:4px">{match.left}</p>
                </div>
                <div style="padding:8px;background:var(--bg-input);border-radius:6px">
                  <small style="color:var(--text-muted)">{match.sentiment_right}</small>
                  <p style="font-size:12px;margin-top:4px">{match.right}</p>
                </div>
              </div>
            </article>
          {/each}
        </div>
      {:else}
        <p class="empty" style="font-size:12px;margin-top:8px">Противоречия не найдены. Добавьте два или более утверждений и запустите поиск.</p>
      {/if}
    </section>
  </div>
</div>
