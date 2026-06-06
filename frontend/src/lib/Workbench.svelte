<script lang="ts">
  import {
    showRightPanel,
    activeWorkbenchTab,
    flightLogs,
    agentTask,
    selectedAgent,
    selectedAgentId,
    agentPlan,
    agentRun,
    exportedReport,
    simulatePlan,
    createPlannedAgentRun
  } from './stores';

  const PERMISSION_PRESETS = [
    { label: 'Минимальные', permissions: { allowed_folders: [], network: false, shell: false } },
    { label: 'Чтение файлов', permissions: { allowed_folders: ['~/documents'], network: false, shell: false } },
    { label: 'Веб-доступ', permissions: { allowed_folders: [], network: true, shell: false } },
    { label: 'Полный доступ', permissions: { allowed_folders: ['~'], network: true, shell: true } },
  ];
  let permissionPreset = PERMISSION_PRESETS[0];
</script>

<aside class="right-panel" class:hidden={!$showRightPanel} aria-label="Workbench панель">
  <!-- Workbench Tabs -->
  <div class="workbench-tabs">
    <button
      type="button"
      class="workbench-tab"
      class:active={$activeWorkbenchTab === 'plan'}
      on:click={() => $activeWorkbenchTab = 'plan'}
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
      <span>План</span>
    </button>
    <button
      type="button"
      class="workbench-tab"
      class:active={$activeWorkbenchTab === 'logs'}
      on:click={() => $activeWorkbenchTab = 'logs'}
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
      <span>Логи</span>
      {#if $flightLogs.length > 0}
        <span class="tab-badge">{$flightLogs.length}</span>
      {/if}
    </button>
    <button
      type="button"
      class="workbench-tab"
      class:active={$activeWorkbenchTab === 'artifacts'}
      on:click={() => $activeWorkbenchTab = 'artifacts'}
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
      <span>Артефакты</span>
    </button>
  </div>

  <!-- Workbench Content -->
  <div class="workbench-content">
    {#if $activeWorkbenchTab === 'plan'}
      <div class="workbench-plan-section">
        <div style="display: flex; flex-direction: column; gap: 8px;">
          <p style="font-size: 12px; font-weight: 600; color: var(--text-secondary);">Конструктор задач (Agent Lab)</p>
          <form on:submit|preventDefault={simulatePlan} class="stack-form" style="gap: 8px;">
            <textarea bind:value={$agentTask} rows="3" placeholder="Опишите задачу для агента..." style="font-size: 12px; padding: 8px 10px;"></textarea>
            <div style="display:flex;gap:8px;align-items:center">
              <select bind:value={permissionPreset} style="flex:1;font-size:11px;padding:6px 8px">
                {#each PERMISSION_PRESETS as preset}
                  <option value={preset}>{preset.label}</option>
                {/each}
              </select>
              <button type="submit" disabled={!$agentTask.trim()} style="min-height: 32px; font-size: 12px; padding: 0 14px;">Собрать AgentPlan</button>
            </div>
          </form>
        </div>

        {#if $agentPlan}
          <div class="plan-box" style="padding: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <strong style="font-size: 12px;">~{$agentPlan.estimated_tokens} токенов</strong>
              <button type="button" class="text-button" on:click={createPlannedAgentRun}>Запустить</button>
            </div>
            <ol style="font-size: 12px; padding-left: 16px; display: flex; flex-direction: column; gap: 4px; color: var(--text-secondary);">
              {#each $agentPlan.steps as step}
                <li>{step}</li>
              {/each}
            </ol>
            <div class="chip-row">
              {#each $agentPlan.required_permissions as permission}
                <span style="font-size: 10px;">{permission}</span>
              {/each}
            </div>
          </div>
        {:else}
          <div class="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
            <p>Создайте план задачи для агента</p>
          </div>
        {/if}
      </div>

    {:else if $activeWorkbenchTab === 'logs'}
      {#if $agentRun}
        <div style="display: flex; flex-direction: column; gap: 4px; padding-bottom: 8px; border-bottom: 1px solid var(--border-color);">
          <div style="display: flex; align-items: center; justify-content: space-between;">
            <strong style="font-size: 12px;">{$agentRun.agent_id}</strong>
            <span class="count" style="font-size: 10px;">{$agentRun.status}</span>
          </div>
          <small style="font-size: 10px; color: var(--text-muted); font-family: var(--font-mono);">Run: {$agentRun.id}</small>
        </div>
        <div style="display: flex; flex-direction: column; gap: 6px;">
          {#each $flightLogs as log}
            <div class="workbench-log-entry">
              <div class="log-header">
                <span class="log-action">{log.action}</span>
                <span class="log-meta">{log.tool} · {log.privacy_level}</span>
              </div>
              {#if log.output}
                <div class="log-output">{log.output}</div>
              {/if}
            </div>
          {:else}
            <p class="empty" style="font-size: 12px;">Логи выполнения отсутствуют.</p>
          {/each}
        </div>
      {:else}
        <div class="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
          <p>Запустите задачу агента для просмотра логов</p>
        </div>
      {/if}

    {:else if $activeWorkbenchTab === 'artifacts'}
      {#if $exportedReport}
        <div class="artifact-card">
          <div class="artifact-header">
            <span class="artifact-title">{$exportedReport.artifact.title}</span>
            <span class="artifact-kind">{$exportedReport.artifact.kind}</span>
          </div>
          <div class="artifact-preview">
            <span style="font-size: 11px; color: var(--text-muted);">ID: {$exportedReport.artifact.id}</span>
            <br>
            <span style="font-size: 11px; color: var(--text-muted);">Фактов: {$exportedReport.receipts_count}</span>
          </div>
          <div style="background: var(--bg-input); padding: 10px; border-radius: 6px; border: 1px solid var(--border-color); font-size: 11px; line-height: 1.5; font-family: var(--font-mono); color: var(--text-secondary); max-height: 200px; overflow-y: auto;">
            {$exportedReport.artifact.source}
          </div>
        </div>
      {:else}
        <div class="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
          <p>Экспортируйте артефакты из исследований или задач</p>
        </div>
      {/if}

      {#if $agentPlan}
        <div class="artifact-card">
          <div class="artifact-header">
            <span class="artifact-title">AgentPlan</span>
            <span class="artifact-kind">task</span>
          </div>
          <div class="artifact-preview">
            <strong style="font-size: 12px;">{$agentPlan.estimated_tokens} токенов</strong>
            <ul style="padding-left: 14px; margin-top: 4px; font-size: 11px;">
              {#each $agentPlan.steps as step}
                <li>{step}</li>
              {/each}
            </ul>
          </div>
        </div>
      {/if}
    {/if}
  </div>
</aside>
