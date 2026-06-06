<script lang="ts">
  import { agentRun, flightLogs } from './stores';

  function formatTs(ts: string) {
    try {
      return new Date(ts).toLocaleTimeString('ru', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch {
      return ts;
    }
  }
</script>

{#if $agentRun}
  <div style="display: flex; flex-direction: column; gap: 4px; padding-bottom: 8px; border-bottom: 1px solid var(--border-color);">
    <div style="display: flex; align-items: center; justify-content: space-between;">
      <strong style="font-size: 12px;">{$agentRun.agent_id}</strong>
      <span class="count" style="font-size: 10px;">{$agentRun.status}</span>
    </div>
    <small style="font-size: 10px; color: var(--text-muted); font-family: var(--font-mono);">
      Run: {$agentRun.id}
    </small>
  </div>

  <div style="display: flex; flex-direction: column; gap: 6px;">
    {#each $flightLogs as log}
      <div class="workbench-log-entry">
        <div class="log-header">
          <span class="log-action">{log.action}</span>
          <span class="log-meta">{formatTs(log.ts)} · {log.tool} · {log.privacy_level}</span>
        </div>
        {#if log.input}
          <div class="log-output">input: {log.input}</div>
        {/if}
        {#if log.output}
          <div class="log-output">{log.output}</div>
        {/if}
        {#if log.error}
          <div class="log-output" style="color: var(--color-red-text);">{log.error}</div>
        {/if}
      </div>
    {:else}
      <p class="empty" style="font-size: 12px;">Логи выполнения отсутствуют.</p>
    {/each}
  </div>
{:else}
  <div class="empty-state">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
    <p>Запустите задачу агента для просмотра Flight Recorder</p>
  </div>
{/if}
