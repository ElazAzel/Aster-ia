<script lang="ts">
  const API_BASE = "http://127.0.0.1:8000";

  type WorkflowRun = {
    id: string;
    status: string;
    workflow: Record<string, unknown>;
    results: Record<string, unknown>[];
    created_at: string;
    updated_at: string;
  };

  let runs: WorkflowRun[] = [];
  let loading = false;
  let selectedRun: WorkflowRun | null = null;

  async function loadRuns() {
    loading = true;
    try {
      const res = await fetch(`${API_BASE}/api/workflows/runs`);
      runs = await res.json();
    } catch (e) {
      runs = [];
    } finally {
      loading = false;
    }
  }

  function formatDate(iso: string) {
    return new Date(iso).toLocaleString("ru-RU");
  }

  loadRuns();
</script>

<div class="workflow-viewer">
  <h2>Рабочие процессы</h2>

  <button class="refresh-btn" on:click={loadRuns} disabled={loading}>
    {loading ? "Загрузка..." : "Обновить"}
  </button>

  {#if selectedRun}
    <div class="run-detail">
      <button class="back-btn" on:click={() => (selectedRun = null)}>← Назад</button>
      <h3>Запуск {selectedRun.id.slice(0, 8)}</h3>
      <div class="detail-row">
        <span>Статус:</span>
        <span class="status">{selectedRun.status}</span>
      </div>
      <div class="detail-row">
        <span>Создан:</span>
        <span>{formatDate(selectedRun.created_at)}</span>
      </div>
      {#if selectedRun.results.length > 0}
        <h4>Результаты</h4>
        <pre>{JSON.stringify(selectedRun.results, null, 2)}</pre>
      {/if}
    </div>
  {:else}
    <div class="runs-list">
      {#if runs.length === 0 && !loading}
        <p class="empty">Нет активных процессов</p>
      {/if}
      {#each runs as run}
        <button class="run-card" on:click={() => (selectedRun = run)}>
          <div class="run-header">
            <span class="run-id">{run.id.slice(0, 8)}</span>
            <span class="run-status" class:active={run.status === "running"}>{run.status}</span>
          </div>
          <div class="run-time">{formatDate(run.created_at)}</div>
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .workflow-viewer { max-width: 700px; }
  h2 { font-size: 22px; margin-bottom: 16px; }

  .refresh-btn {
    background: #30363d;
    color: #e1e4e8;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 6px 14px;
    cursor: pointer;
    font: inherit;
    font-size: 13px;
    margin-bottom: 16px;
  }

  .refresh-btn:hover { background: #484f58; }
  .refresh-btn:disabled { opacity: 0.5; }

  .runs-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .run-card {
    display: block;
    width: 100%;
    text-align: left;
    padding: 14px;
    border: 1px solid #21262d;
    border-radius: 8px;
    background: #161b22;
    cursor: pointer;
    font: inherit;
    color: #e1e4e8;
  }

  .run-card:hover { border-color: #58a6ff; }

  .run-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
  }

  .run-id { font-weight: 600; font-size: 14px; }

  .run-status {
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 10px;
    background: #30363d;
    color: #8b949e;
  }

  .run-status.active {
    background: #23863622;
    color: #2ea043;
  }

  .run-time {
    font-size: 12px;
    color: #8b949e;
  }

  .run-detail {
    padding: 16px;
    border: 1px solid #21262d;
    border-radius: 8px;
    background: #161b22;
  }

  .back-btn {
    background: none;
    border: none;
    color: #58a6ff;
    cursor: pointer;
    font: inherit;
    font-size: 13px;
    margin-bottom: 12px;
    padding: 0;
  }

  .run-detail h3 { font-size: 16px; margin-bottom: 12px; }
  .run-detail h4 { font-size: 14px; margin: 16px 0 8px; color: #58a6ff; }

  .detail-row {
    display: flex;
    gap: 8px;
    font-size: 13px;
    margin-bottom: 4px;
  }

  .detail-row span:first-child { color: #8b949e; }
  .status { font-weight: 600; }

  pre {
    background: #0d1117;
    padding: 12px;
    border-radius: 6px;
    font-size: 12px;
    overflow-x: auto;
    color: #c9d1d9;
  }

  .empty { color: #484f58; }
</style>
