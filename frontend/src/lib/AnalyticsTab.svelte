<script lang="ts">
  import { onMount } from 'svelte';
  import { apiBase, analyticsStats, fetchAnalyticsStats } from './stores';

  type TopSource = { source: string; count: number };
  type ConfItem = { confidence: string; count: number };
  type RoomDist = { room_name: string; count: number };
  type AgentStats = { total_runs: number; total_steps: number;
    privacy_distribution: Record<string, number>; error_count: number };

  let topSources: TopSource[] = [];
  let confDist: ConfItem[] = [];
  let roomDist: RoomDist[] = [];
  let agentStats: AgentStats | null = null;
  let loading = false;

  async function load() {
    loading = true;
    await fetchAnalyticsStats();
    const base = $apiBase;
    [topSources, confDist, roomDist, agentStats] = await Promise.all([
      fetch(`${base}/api/analytics/top-sources`).then(r => r.json()).catch(() => []),
      fetch(`${base}/api/analytics/claims-confidence`).then(r => r.json()).catch(() => []),
      fetch(`${base}/api/analytics/rooms-distribution`).then(r => r.json()).catch(() => []),
      fetch(`${base}/api/analytics/agent-stats`).then(r => r.json()).catch(() => null),
    ]);
    loading = false;
  }

  onMount(load);

  function barWidth(val: number, max: number) { return max > 0 ? Math.round((val / max) * 100) : 0; }
</script>

<div class="tab-content">
  <div class="secondary-grid" style="grid-template-columns:1fr 1fr;row-gap:14px">

    <section class="panel" style="grid-column:span 2">
      <div class="panel-heading compact">
        <h2>Analytics Dashboard</h2>
        <button type="button" class="text-button" on:click={load} disabled={loading}>
          {loading ? '...' : 'Обновить'}
        </button>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px">
        {#each [
          ['Исследований', $analyticsStats?.total_research_queries ?? 0, '🔍'],
          ['Источников', $analyticsStats?.sources_consulted ?? 0, '🌐'],
          ['Утверждений', $analyticsStats?.claims_verified ?? 0, '✓'],
          ['Запусков агентов', agentStats?.total_runs ?? 0, '🤖'],
          ['Шагов агентов', agentStats?.total_steps ?? 0, '⚙️'],
          ['Ошибок агентов', agentStats?.error_count ?? 0, '✗'],
        ] as [label, val, icon]}
          <div style="background:var(--bg-input);border-radius:10px;padding:14px;text-align:center">
            <div style="font-size:22px;margin-bottom:4px">{icon}</div>
            <div style="font-size:24px;font-weight:700;color:var(--color-brand)">{Number(val).toLocaleString('ru')}</div>
            <div style="font-size:11px;color:var(--text-muted)">{label}</div>
          </div>
        {/each}
      </div>
    </section>

    <section class="panel">
      <div class="panel-heading compact"><h2>Топ источников</h2></div>
      {#if topSources.length === 0}
        <p class="empty">Нет данных. Запустите Deep Research для накопления статистики.</p>
      {:else}
        {@const maxV = Math.max(...topSources.map(s => s.count), 1)}
        <div style="display:flex;flex-direction:column;gap:8px">
          {#each topSources as src}
            <div>
              <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px">
                <span style="color:var(--text-primary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1">{src.source}</span>
                <span style="color:var(--text-muted);margin-left:8px;flex-shrink:0">{src.count}</span>
              </div>
              <div style="height:6px;background:var(--bg-input);border-radius:3px;overflow:hidden">
                <div style="height:100%;width:{barWidth(src.count, maxV)}%;background:var(--color-brand);border-radius:3px;transition:width .3s"></div>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </section>

    <section class="panel">
      <div class="panel-heading compact"><h2>Уверенность утверждений</h2></div>
      {#if confDist.length === 0}
        <p class="empty">Нет данных.</p>
      {:else}
        {@const confColors = {high:'var(--color-green-text)', medium:'var(--color-yellow-text)', low:'var(--color-red-text)'}}
        {@const maxC = Math.max(...confDist.map(c => c.count), 1)}
        <div style="display:flex;flex-direction:column;gap:10px">
          {#each confDist as item}
            {@const c = confColors[item.confidence as keyof typeof confColors] ?? 'var(--color-brand)'}
            <div>
              <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px">
                <span style="color:{c};font-weight:600;text-transform:capitalize">{item.confidence}</span>
                <span style="color:var(--text-muted)">{item.count}</span>
              </div>
              <div style="height:8px;background:var(--bg-input);border-radius:4px;overflow:hidden">
                <div style="height:100%;width:{barWidth(item.count, maxC)}%;background:{c};opacity:0.7;border-radius:4px"></div>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </section>

    <section class="panel">
      <div class="panel-heading compact"><h2>Исследований по комнатам</h2></div>
      {#if roomDist.length === 0}
        <p class="empty">Нет данных.</p>
      {:else}
        {@const maxR = Math.max(...roomDist.map(r => r.count), 1)}
        <div style="display:flex;flex-direction:column;gap:8px">
          {#each roomDist as room}
            <div style="display:flex;align-items:center;gap:10px">
              <span style="font-size:12px;min-width:80px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{room.room_name}</span>
              <div style="flex:1;height:8px;background:var(--bg-input);border-radius:4px;overflow:hidden">
                <div style="height:100%;width:{barWidth(room.count, maxR)}%;background:var(--color-brand);border-radius:4px"></div>
              </div>
              <span style="font-size:12px;color:var(--text-muted);min-width:20px;text-align:right">{room.count}</span>
            </div>
          {/each}
        </div>
      {/if}
    </section>

    <section class="panel">
      <div class="panel-heading compact"><h2>Приватность агентных шагов</h2></div>
      {#if !agentStats || Object.keys(agentStats.privacy_distribution).length === 0}
        <p class="empty">Нет данных.</p>
      {:else}
        {@const privColors = {local:'var(--color-green-text)', hybrid:'var(--color-yellow-text)', external:'var(--color-red-text)'}}
        {@const total = Object.values(agentStats.privacy_distribution).reduce((a,b) => a+b, 0)}
        <div style="display:flex;flex-direction:column;gap:10px">
          {#each Object.entries(agentStats.privacy_distribution) as [level, count]}
            {@const c = privColors[level as keyof typeof privColors] ?? 'var(--color-brand)'}
            {@const pct = total > 0 ? Math.round((Number(count)/total)*100) : 0}
            <div>
              <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px">
                <span style="color:{c};font-weight:600">{level}</span>
                <span style="color:var(--text-muted)">{count} ({pct}%)</span>
              </div>
              <div style="height:8px;background:var(--bg-input);border-radius:4px;overflow:hidden">
                <div style="height:100%;width:{pct}%;background:{c};opacity:0.7;border-radius:4px"></div>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </section>
  </div>
</div>
