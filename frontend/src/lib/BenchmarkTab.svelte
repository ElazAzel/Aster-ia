<script lang="ts">
  import { onMount } from 'svelte';
  import { apiBase, models, vramGb, ramGb, showToast } from './stores';
  import { runBenchmark, getVllmStatus, type BenchmarkModelResult } from './api';

  let results: BenchmarkModelResult[] = [];
  let running = false;
  let runsPer = 3;
  let maxTok = 128;
  let selectedModels: string[] = [];
  let sortBy: keyof BenchmarkModelResult = 'avg_tokens_per_second';
  let sortAsc = false;
  let vllmStatus: { available: boolean; models: string[] } | null = null;

  onMount(async () => {
    const v = await getVllmStatus($apiBase).catch(() => null);
    vllmStatus = v;
  });

  $: installedModels = $models.map(m => m.name).filter(n => !n.includes('embed'));
  $: sorted = [...results].sort((a, b) => {
    const av = a[sortBy] as number, bv = b[sortBy] as number;
    return sortAsc ? av - bv : bv - av;
  });

  async function run() {
    running = true; results = [];
    const targets = selectedModels.length > 0 ? selectedModels : undefined;
    try {
      const res = await runBenchmark($apiBase, targets, runsPer, maxTok);
      results = res?.results ?? [];
      showToast(`Benchmark готов: ${results.length} моделей`, 'success');
    } catch (e) { showToast(`Ошибка: ${String(e)}`, 'error'); }
    running = false;
  }

  function tpsColor(tps: number) {
    if (tps >= 20) return 'var(--color-green-text)';
    if (tps >= 8) return 'var(--color-yellow-text)';
    return 'var(--color-red-text)';
  }
  function tpsLabel(tps: number) {
    if (tps >= 20) return 'Быстро';
    if (tps >= 8) return 'Нормально';
    return 'Медленно';
  }
  function toggleSort(key: keyof BenchmarkModelResult) {
    if (sortBy === key) sortAsc = !sortAsc; else { sortBy = key; sortAsc = false; }
  }
  function thStyle(key: keyof BenchmarkModelResult) {
    return sortBy === key ? 'color:var(--text-primary);cursor:pointer' : 'cursor:pointer';
  }
</script>

<div class="tab-content">
  <div class="secondary-grid">
    <section class="panel">
      <div class="panel-heading compact">
        <h2>Model Benchmark</h2>
        <span class="risk-pill risk-green">Локально</span>
      </div>
      <p style="font-size:12px;color:var(--text-secondary);margin-bottom:12px">
        Измеряет токен/с, время до первого токена и латентность. Все тесты выполняются локально.
      </p>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px">
        <label style="display:flex;flex-direction:column;gap:3px">
          <span style="font-size:11px;font-weight:600;color:var(--text-secondary)">Запусков на модель</span>
          <input type="number" bind:value={runsPer} min="1" max="10" />
        </label>
        <label style="display:flex;flex-direction:column;gap:3px">
          <span style="font-size:11px;font-weight:600;color:var(--text-secondary)">Токенов ответа</span>
          <input type="number" bind:value={maxTok} min="8" max="512" step="8" />
        </label>
      </div>

      <div style="margin-bottom:12px">
        <span style="font-size:11px;font-weight:600;color:var(--text-secondary);display:block;margin-bottom:6px">
          Модели (пусто = все установленные)
        </span>
        <div style="display:flex;flex-direction:column;gap:4px;max-height:160px;overflow-y:auto">
          {#each installedModels as model}
            <label style="display:flex;align-items:center;gap:8px;font-size:12px;cursor:pointer">
              <input type="checkbox" bind:group={selectedModels} value={model} />
              <span>{model}</span>
            </label>
          {/each}
        </div>
      </div>

      <button type="button" on:click={run} disabled={running} style="width:100%">
        {running ? 'Тестирую...' : 'Запустить Benchmark'}
      </button>

      {#if vllmStatus}
        <div class="plan-box" style="margin-top:12px;background:var(--bg-input)">
          <strong style="font-size:12px">vLLM: {vllmStatus.available ? 'доступен' : 'не запущен'}</strong>
          {#if vllmStatus.available && vllmStatus.models.length > 0}
            <p style="font-size:11px;color:var(--text-secondary);margin-top:4px">
              Модели: {vllmStatus.models.join(', ')}
            </p>
          {:else if !vllmStatus.available}
            <p style="font-size:11px;color:var(--text-muted);margin-top:4px">
              Запуск: <code>python -m vllm.entrypoints.openai.api_server --model &lt;name&gt; --port 8100</code>
            </p>
          {/if}
        </div>
      {/if}
    </section>

    <section class="panel" style="flex:1;overflow:hidden">
      <div class="panel-heading compact">
        <h2>Результаты ({results.length})</h2>
        {#if results.length > 0}
          <span style="font-size:11px;color:var(--text-muted)">Клик на заголовок = сортировка</span>
        {/if}
      </div>

      {#if results.length > 0}
        <div style="overflow-x:auto">
          <table style="width:100%;border-collapse:collapse;font-size:12px">
            <thead>
              <tr style="background:var(--bg-input)">
                <th style="text-align:left;padding:8px 10px;color:var(--text-secondary);font-weight:600">Модель</th>
                {#each [['avg_tokens_per_second','tok/s'],['avg_time_to_first_token_ms','TTFT ms'],['avg_total_time_ms','Total ms'],['vram_estimate_gb','VRAM']] as [k,l]}
                  <th on:click={() => toggleSort(k as keyof BenchmarkModelResult)}
                    style="text-align:right;padding:8px 10px;font-weight:600;{thStyle(k as keyof BenchmarkModelResult)}">
                    {l} {sortBy === k ? (sortAsc ? '↑' : '↓') : ''}
                  </th>
                {/each}
                <th style="text-align:center;padding:8px 10px;font-weight:600">Оценка</th>
              </tr>
            </thead>
            <tbody>
              {#each sorted as r}
                <tr style="border-bottom:1px solid var(--border-color)">
                  <td style="padding:8px 10px;font-weight:500">
                    {r.model}
                    {#if r.error}<small style="display:block;color:var(--color-red-text);font-size:10px">✗ {r.error.slice(0,40)}</small>{/if}
                  </td>
                  <td style="text-align:right;padding:8px 10px;color:{tpsColor(r.avg_tokens_per_second)};font-family:var(--font-mono)">
                    {r.avg_tokens_per_second.toFixed(1)}
                  </td>
                  <td style="text-align:right;padding:8px 10px;font-family:var(--font-mono)">{r.avg_time_to_first_token_ms.toFixed(0)}</td>
                  <td style="text-align:right;padding:8px 10px;font-family:var(--font-mono)">{r.avg_total_time_ms.toFixed(0)}</td>
                  <td style="text-align:right;padding:8px 10px;font-family:var(--font-mono)">{r.vram_estimate_gb.toFixed(1)} GB</td>
                  <td style="text-align:center;padding:8px 10px;font-size:11px;font-weight:600;color:{tpsColor(r.avg_tokens_per_second)}">
                    {tpsLabel(r.avg_tokens_per_second)}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {:else if running}
        <div style="padding:32px;text-align:center;color:var(--text-muted)">
          <div style="font-size:24px;margin-bottom:8px">⏳</div>
          Тестирую модели... это может занять 1-3 минуты
        </div>
      {:else}
        <p class="empty">Запустите тест для просмотра результатов.</p>
      {/if}
    </section>
  </div>
</div>
