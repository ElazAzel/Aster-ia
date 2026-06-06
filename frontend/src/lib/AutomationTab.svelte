<script lang="ts">
  import {
    workflowResult,
    workflowName,
    workflowSteps,
    workflowPending,
    startWorkflow,
    approveWorkflow
  } from './stores';

  const WORKFLOW_TEMPLATES = [
    { name: 'Проверка файлов', steps: [{"name":"Сканировать файлы","type":"action"},{"name":"Проверить на вирусы","type":"action"},{"name":"Отчёт","type":"action"}] },
    { name: 'Ревью кода', steps: [{"name":"Загрузить код","type":"action"},{"name":"Проверить стиль","type":"action"},{"name":"Утвердить изменения","type":"human_approval"},{"name":"Создать PR","type":"action"}] },
    { name: 'Исследование', steps: [{"name":"Собрать источники","type":"action"},{"name":"Анализировать","type":"action"},{"name":"Создать отчёт","type":"human_approval"}] },
  ];

  function applyWorkflowTemplate(index: number) {
    if (index >= 0 && index < WORKFLOW_TEMPLATES.length) {
      workflowName.set(WORKFLOW_TEMPLATES[index].name);
      workflowSteps.set(JSON.stringify(WORKFLOW_TEMPLATES[index].steps, null, 2));
    }
  }
</script>

<div class="tab-content">
  <div class="secondary-grid">
    <section class="panel">
      <div class="panel-heading compact">
        <h2>Automation Board</h2>
        {#if $workflowResult}
          <span class="count" style="color:{$workflowResult.status === 'completed' ? 'var(--color-green-text)' : 'var(--color-red-text)'}">
            {$workflowResult.status}
          </span>
        {/if}
      </div>
      <label style="display:flex;flex-direction:column;gap:4px;margin-bottom:8px">
        <span style="font-size:11px;font-weight:600;color:var(--text-secondary);">Шаблон</span>
        <select on:change={(e) => applyWorkflowTemplate(parseInt(e.currentTarget.value))} style="font-size:12px;padding:6px 10px">
          <option value="-1">Выберите шаблон...</option>
          {#each WORKFLOW_TEMPLATES as template, i}
            <option value={i}>{template.name}</option>
          {/each}
        </select>
      </label>
      <label style="display:flex;flex-direction:column;gap:4px">
        <span style="font-size:11px;font-weight:600;color:var(--text-secondary)">Название workflow</span>
        <input bind:value={$workflowName} placeholder="Мой рабочий процесс" />
      </label>
      <label style="display:flex;flex-direction:column;gap:4px;margin-top:8px">
        <span style="font-size:11px;font-weight:600;color:var(--text-secondary)">Шаги (JSON)</span>
        <textarea bind:value={$workflowSteps} rows="6" style="font-family:var(--font-mono);font-size:12px" placeholder={JSON.stringify([{"name":"Шаг 1","type":"action"}])}></textarea>
      </label>
      <div style="display:flex;gap:8px;margin-top:8px">
        <button type="button" on:click={startWorkflow} disabled={!$workflowSteps.trim()}>▶ Запустить</button>
        {#if $workflowPending}
          <button type="button" on:click={() => approveWorkflow(true)} style="background:var(--color-green);color:#fff">✓ Подтвердить</button>
          <button type="button" class="secondary" on:click={() => approveWorkflow(false)}>✗ Отклонить</button>
        {/if}
      </div>
      {#if $workflowPending}
        <div style="padding:12px;background:var(--color-yellow-glow);border:1px solid var(--color-yellow-border);border-radius:8px;margin-top:8px">
          <strong style="color:var(--color-yellow-text);font-size:13px">⚠ Human Approval Gate</strong>
          <p style="font-size:12px;color:var(--text-secondary);margin-top:4px">Workflow ожидает вашего подтверждения для продолжения.</p>
        </div>
      {/if}
    </section>
    <section class="panel">
      <div class="panel-heading compact"><h2>Результат выполнения</h2></div>
      {#if $workflowResult}
        <div class="plan-box" style="margin-top:0">
          <strong>Run ID: {$workflowResult.run_id}</strong>
          <ol style="padding-left:16px;font-size:12px;color:var(--text-secondary);display:flex;flex-direction:column;gap:4px">
            {#each $workflowResult.results as step}
              <li><strong style="color:var(--text-primary)">{step.step}</strong> — {step.status}</li>
            {/each}
          </ol>
        </div>
      {:else}
        <p class="empty">Запустите workflow для просмотра результатов.</p>
      {/if}
    </section>
  </div>
</div>
