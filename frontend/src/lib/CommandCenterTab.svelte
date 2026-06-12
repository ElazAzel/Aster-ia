<script lang="ts">
  import {
    activeTab,
    selectedModel,
    vramGb,
    ramGb,
    auditLogs,
    desktopStatus,
    refreshAuditLogs
  } from './stores';
  import { onMount } from 'svelte';

  function getPrivacyLevel(log: { resource: string; details?: string | null }) {
    const text = `${log.resource} ${log.details ?? ''}`.toLowerCase();
    if (text.includes('external') || text.includes('api') || text.includes('gpt') || text.includes('shell') || text.includes('терминал')) {
      return 'EXTERNAL';
    }
    if (text.includes('deep research') || text.includes('searxng') || text.includes('hybrid') || text.includes('поиск') || text.includes('гибрид')) {
      return 'HYBRID';
    }
    return 'LOCAL';
  }

  function getPrivacyColor(level: string) {
    if (level === 'LOCAL') return 'var(--color-green)';
    if (level === 'HYBRID') return 'var(--color-yellow)';
    return 'var(--color-red)';
  }

  function getPrivacyText(level: string) {
    if (level === 'LOCAL') return 'ЛОКАЛЬНО';
    if (level === 'HYBRID') return 'ГИБРИД';
    return 'ВНЕШНИЙ';
  }

  function formatLogTime(ts: string) {
    try {
      const date = new Date(ts);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      if (diffMins < 1) return 'Только что';
      if (diffMins < 60) return `${diffMins} мин назад`;
      const diffHrs = Math.floor(diffMins / 60);
      if (diffHrs < 24) return `${diffHrs} ч назад`;
      return date.toLocaleDateString('ru-RU', { month: 'short', day: 'numeric' });
    } catch {
      return ts;
    }
  }

  $: displayLogs = $auditLogs && $auditLogs.length > 0 ? $auditLogs.slice(0, 5) : [];

  $: localCount = displayLogs.filter(log => getPrivacyLevel(log) === 'LOCAL').length;
  $: totalCount = displayLogs.length;
  $: localPercent = totalCount > 0 ? Math.round((localCount / totalCount) * 100) : 100;

  onMount(() => {
    void refreshAuditLogs();
  });
</script>

<div class="tab-content" style="overflow-y: auto; padding: 24px 32px;">
  <div style="display: grid; grid-template-columns: repeat(12, 1fr); gap: 24px; max-width: 1400px; margin: 0 auto; width: 100%;">
    
    <!-- Welcome Header / Overview -->
    <div style="grid-column: span 12; display: flex; justify-content: space-between; align-items: end; margin-bottom: 8px;">
      <div>
        <h2 style="font-family: var(--font-sans); font-size: 36px; font-weight: 700; color: var(--text-primary); letter-spacing: -0.02em; margin-bottom: 4px;">Система Активна</h2>
        <p style="font-family: var(--font-mono); font-size: 13px; color: var(--text-secondary);">Asterion Node-01 готов к оркестрации локального окружения.</p>
      </div>

      <!-- Privacy Radar widget -->
      <div class="bento-card" style="padding: 12px 20px; display: flex; align-items: center; gap: 16px; width: 260px; height: 80px; flex-shrink: 0;">
        <div style="position: relative; width: 48px; height: 48px; flex-shrink: 0; display: flex; align-items: center; justify-content: center;">
          <svg style="transform: rotate(-90deg); width: 100%; height: 100%;" viewBox="0 0 36 36">
            <path style="color: var(--border-color);" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" stroke-width="3"></path>
            <path style="color: var(--color-green);" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" stroke-dasharray="{localPercent}, 100" stroke-width="3"></path>
          </svg>
          <span style="position: absolute; font-family: var(--font-mono); font-size: 11px; font-weight: 700; color: var(--text-primary);">{localPercent}%</span>
        </div>
        <div>
          <p style="font-family: var(--font-mono); font-size: 10px; color: var(--text-secondary); text-transform: uppercase; margin: 0; line-height: 1.2;">Приватность</p>
          <p style="font-family: var(--font-sans); font-size: 11px; font-weight: 600; color: var(--color-green); margin: 2px 0 0 0; display: flex; align-items: center; gap: 4px;">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            Защищено
          </p>
        </div>
      </div>
    </div>

    <!-- Quick Actions (8 Cols Grid) -->
    <div style="grid-column: span 8; display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;">
      
      <!-- Start Chat Button -->
      <button type="button" class="bento-card" style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 160px; border: 1px solid var(--border-color); background: rgba(124, 109, 250, 0.04); cursor: pointer; text-align: center; text-decoration: none;" on:click={() => $activeTab = 'chat'}>
        <svg style="color: var(--color-brand); margin-bottom: 12px; transition: transform 0.2s;" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="group-hover:-translate-y-1"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
        <span style="font-family: var(--font-sans); font-size: 15px; font-weight: 600; color: var(--text-primary);">Умный Чат</span>
      </button>

      <!-- Deep Research Button -->
      <button type="button" class="bento-card" style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 160px; border: 1px solid var(--border-color); background: rgba(245, 184, 49, 0.04); cursor: pointer; text-align: center; text-decoration: none;" on:click={() => $activeTab = 'research_deep'}>
        <svg style="color: var(--color-yellow); margin-bottom: 12px;" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/><path d="M11 8v6"/><path d="M8 11h6"/></svg>
        <span style="font-family: var(--font-sans); font-size: 15px; font-weight: 600; color: var(--text-primary);">Deep Research</span>
      </button>

      <!-- Open Documents Button -->
      <button type="button" class="bento-card" style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 160px; border: 1px solid var(--border-color); background: rgba(48, 201, 126, 0.04); cursor: pointer; text-align: center; text-decoration: none;" on:click={() => $activeTab = 'vault'}>
        <svg style="color: var(--color-green); margin-bottom: 12px;" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2L2 7l10 5 10-5-10-5z"></path><path d="M2 17l10 5 10-5"></path><path d="M2 12l10 5 10-5"></path></svg>
        <span style="font-family: var(--font-sans); font-size: 15px; font-weight: 600; color: var(--text-primary);">База Знаний (Vault)</span>
      </button>

      <!-- Run Agent Button -->
      <button type="button" class="bento-card" style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 160px; border: 1px solid var(--border-color); background: rgba(198, 191, 255, 0.04); cursor: pointer; text-align: center; text-decoration: none;" on:click={() => $activeTab = 'agents'}>
        <svg style="color: var(--color-brand-hover); margin-bottom: 12px;" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
        <span style="font-family: var(--font-sans); font-size: 15px; font-weight: 600; color: var(--text-primary);">Запуск Агентов</span>
      </button>

      <!-- Generate Image Button -->
      <button type="button" class="bento-card" style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 160px; border: 1px solid var(--border-color); background: rgba(124, 109, 250, 0.04); cursor: pointer; text-align: center; text-decoration: none;" on:click={() => $activeTab = 'images'}>
        <svg style="color: var(--color-brand); margin-bottom: 12px;" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/></svg>
        <span style="font-family: var(--font-sans); font-size: 15px; font-weight: 600; color: var(--text-primary);">Студия Изображений</span>
      </button>

      <!-- Automation Board Button -->
      <button type="button" class="bento-card" style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 160px; border: 1px solid var(--border-color); background: rgba(146, 142, 160, 0.04); cursor: pointer; text-align: center; text-decoration: none;" on:click={() => $activeTab = 'automation'}>
        <svg style="color: var(--text-muted); margin-bottom: 12px;" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
        <span style="font-family: var(--font-sans); font-size: 15px; font-weight: 600; color: var(--text-primary);">Автоматизация</span>
      </button>

    </div>

    <!-- System Status Panel (4 Cols) -->
    <div style="grid-column: span 4; display: flex; flex-direction: column; gap: 20px;">
      <div class="bento-card" style="position: relative; overflow: hidden; display: flex; flex-direction: column; justify-content: space-between; height: 340px;">
        <!-- Secure indicator bar at top -->
        <div style="position: absolute; top: 0; left: 0; height: 3px; background: var(--color-green); width: 100%;"></div>
        
        <!-- Header -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <h3 style="font-family: var(--font-sans); font-size: 15px; font-weight: 600; color: var(--text-primary); display: flex; align-items: center; gap: 8px; margin: 0;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect><rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect><line x1="6" y1="6" x2="6.01" y2="6"></line><line x1="6" y1="18" x2="6.01" y2="18"></line></svg>
            Статус системы
          </h3>
          <span style="font-family: var(--font-mono); font-size: 11px; display: flex; align-items: center; gap: 6px; color: var(--color-green); font-weight: 600; text-transform: uppercase;">
            <span style="width: 8px; height: 8px; border-radius: 50%; background: var(--color-green); display: inline-block;"></span>
            Online
          </span>
        </div>

        <!-- Model indicator -->
        <div style="margin-bottom: 20px;">
          <p style="font-family: var(--font-mono); font-size: 10px; color: var(--text-muted); text-transform: uppercase; margin-bottom: 6px;">Текущая Модель</p>
          <div style="background: var(--bg-input); border: 1px solid var(--border-color); padding: 12px; border-radius: 6px; display: flex; flex-direction: column; gap: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="font-family: var(--font-mono); font-size: 13px; font-weight: 600; color: var(--text-primary);">{$selectedModel}</span>
              <span style="font-family: var(--font-mono); font-size: 9px; padding: 2px 6px; background: rgba(48, 201, 126, 0.1); border: 1px solid rgba(48, 201, 126, 0.2); color: var(--color-green); rounded: 2px;">LOCAL</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; font-family: var(--font-mono); font-size: 11px; color: var(--text-secondary);">
              <span>Скорость вывода:</span>
              <span style="color: var(--text-primary); font-weight: 600;">~65 tok/s</span>
            </div>
          </div>
        </div>

        <!-- VRAM Usage -->
        <div style="margin-bottom: 16px;">
          <div style="display: flex; justify-content: space-between; align-items: end; font-family: var(--font-mono); font-size: 11px; margin-bottom: 6px;">
            <span style="color: var(--text-secondary); text-transform: uppercase;">Использование VRAM</span>
            <span style="color: var(--text-primary); font-weight: 600;">{$vramGb} GB <span style="color: var(--text-muted); font-weight: 400;">/ 24 GB</span></span>
          </div>
          <div style="width: 100%; height: 8px; background: var(--bg-input); border: 1px solid var(--border-color); border-radius: 4px; overflow: hidden;">
            <div style="height: 100%; bg: var(--color-brand); background-color: var(--color-brand); width: {Math.min(100, Math.round(($vramGb / 24) * 100))}%"></div>
          </div>
        </div>

        <!-- System RAM Usage -->
        <div>
          <div style="display: flex; justify-content: space-between; align-items: end; font-family: var(--font-mono); font-size: 11px; margin-bottom: 6px;">
            <span style="color: var(--text-secondary); text-transform: uppercase;">Системная память RAM</span>
            <span style="color: var(--text-primary); font-weight: 600;">{$ramGb} GB <span style="color: var(--text-muted); font-weight: 400;">/ 32 GB</span></span>
          </div>
          <div style="width: 100%; height: 8px; background: var(--bg-input); border: 1px solid var(--border-color); border-radius: 4px; overflow: hidden;">
            <div style="height: 100%; bg: var(--color-yellow); background-color: var(--color-yellow); width: {Math.min(100, Math.round(($ramGb / 32) * 100))}%"></div>
          </div>
        </div>

      </div>
    </div>

    <!-- Bottom Left: Recent Items (12 Cols) -->
    <div style="grid-column: span 12; display: flex; flex-direction: column;" class="bento-card">
      <div style="border-bottom: 1px solid var(--border-color); padding-bottom: 14px; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center;">
        <h3 style="font-family: var(--font-sans); font-size: 15px; font-weight: 600; color: var(--text-primary); display: flex; align-items: center; gap: 8px; margin: 0;">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          Последние операции
        </h3>
        <button type="button" class="text-button" style="font-family: var(--font-mono); font-size: 11px; text-transform: uppercase; cursor: pointer;" on:click={refreshAuditLogs}>Обновить</button>
      </div>

      <div style="overflow-x: auto; width: 100%;">
        <table style="width: 100%; border-collapse: collapse; text-align: left;">
          <tbody>
            {#each displayLogs as log}
              {@const level = getPrivacyLevel(log)}
              <tr style="border-bottom: 1px solid rgba(71, 69, 84, 0.3); transition: background 0.2s;" class="hover:bg-surface-container-high/20">
                <td style="padding: 12px 16px; width: 140px; font-family: var(--font-mono); font-size: 12px; color: var(--text-muted);">{formatLogTime(log.ts)}</td>
                <td style="padding: 12px 16px;">
                  <span style="display: inline-flex; align-items: center; gap: 8px;">
                    {#if level === 'LOCAL'}
                      <svg style="color: var(--color-green);" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                    {:else if level === 'HYBRID'}
                      <svg style="color: var(--color-yellow);" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                    {:else}
                      <svg style="color: var(--color-red);" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                    {/if}
                    <span style="font-family: var(--font-sans); font-size: 13.5px; font-weight: 500; color: var(--text-primary);">{log.resource}</span>
                  </span>
                </td>
                <td style="padding: 12px 16px; font-family: var(--font-sans); font-size: 12.5px; color: var(--text-secondary);">{log.details || '—'}</td>
                <td style="padding: 12px 16px; text-align: right;">
                  <span style="padding: 3px 8px; border-radius: 4px; font-family: var(--font-mono); font-size: 10px; font-weight: 700; border: 1px solid {getPrivacyColor(level)}2b; background: {getPrivacyColor(level)}12; color: {getPrivacyColor(level)};">
                    {getPrivacyText(level)}
                  </span>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>

  </div>
</div>
