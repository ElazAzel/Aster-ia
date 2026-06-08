<script lang="ts">
  const API_BASE = "http://127.0.0.1:8000";

  let health: { status: string; version: string } | null = null;
  let ollamaModels: string[] = [];
  let checking = false;

  async function checkHealth() {
    checking = true;
    try {
      const res = await fetch(`${API_BASE}/api/health`);
      health = await res.json();
    } catch (e) {
      health = null;
    }
    try {
      const res = await fetch(`${API_BASE}/api/models`);
      const data = await res.json();
      ollamaModels = data.models ?? [];
    } catch (e) {
      ollamaModels = [];
    } finally {
      checking = false;
    }
  }

  checkHealth();
</script>

<div class="system-status">
  <h2>Системный монитор</h2>

  <button class="refresh-btn" on:click={checkHealth} disabled={checking}>
    {checking ? "Проверка..." : "Обновить"}
  </button>

  <div class="status-grid">
    <div class="status-card" class:ok={health !== null} class:error={health === null}>
      <div class="card-label">API Backend</div>
      <div class="card-value">{health ? "Работает" : "Недоступен"}</div>
      {#if health}
        <div class="card-detail">v{health.version}</div>
      {/if}
    </div>

    <div class="status-card" class:ok={ollamaModels.length > 0} class:error={ollamaModels.length === 0}>
      <div class="card-label">Ollama</div>
      <div class="card-value">{ollamaModels.length > 0 ? `${ollamaModels.length} моделей` : "Недоступен"}</div>
      {#if ollamaModels.length > 0}
        <div class="card-detail">{ollamaModels.slice(0, 3).join(", ")}{ollamaModels.length > 3 ? "..." : ""}</div>
      {/if}
    </div>

    <div class="status-card">
      <div class="card-label">Хранилище</div>
      <div class="card-value">SQLCipher</div>
      <div class="card-detail">Зашифровано (keyring)</div>
    </div>

    <div class="status-card">
      <div class="card-label">RAG</div>
      <div class="card-value">LanceDB</div>
      <div class="card-detail">nomic-embed-text</div>
    </div>
  </div>
</div>

<style>
  .system-status { max-width: 700px; }
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
    margin-bottom: 20px;
  }

  .refresh-btn:hover { background: #484f58; }
  .refresh-btn:disabled { opacity: 0.5; }

  .status-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 12px;
  }

  .status-card {
    padding: 16px;
    border: 1px solid #21262d;
    border-radius: 8px;
    background: #161b22;
  }

  .status-card.ok { border-left: 3px solid #2ea043; }
  .status-card.error { border-left: 3px solid #f85149; }

  .card-label {
    font-size: 12px;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
  }

  .card-value {
    font-size: 16px;
    font-weight: 600;
    color: #e1e4e8;
  }

  .card-detail {
    font-size: 12px;
    color: #8b949e;
    margin-top: 4px;
  }
</style>
