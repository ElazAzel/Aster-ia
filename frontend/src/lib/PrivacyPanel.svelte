<script lang="ts">
  const API_BASE = "http://127.0.0.1:8000";

  let prompt = "";
  let report: { level: string; items: { what: string; destination: string; risk: string }[] } | null = null;
  let analyzing = false;

  const riskColors: Record<string, string> = {
    green: "#2ea043",
    yellow: "#d29922",
    red: "#f85149",
  };

  async function analyze() {
    if (!prompt.trim()) return;
    analyzing = true;
    report = null;
    try {
      const res = await fetch(`${API_BASE}/api/privacy/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model_type: "local",
          files_attached: false,
          memory_enabled: false,
          web_access: true,
        }),
      });
      report = await res.json();
    } catch (e) {
      report = { level: "error", items: [] };
    } finally {
      analyzing = false;
    }
  }
</script>

<div class="privacy-panel">
  <h2>Анализ приватности</h2>
  <p class="description">Проверьте уровень риска перед отправкой запроса.</p>

  <form on:submit|preventDefault={analyze}>
    <textarea
      bind:value={prompt}
      placeholder="Введите промпт для анализа..."
      rows="4"
    />
    <button type="submit" disabled={analyzing || !prompt.trim()}>
      {analyzing ? "Анализ..." : "Анализировать"}
    </button>
  </form>

  {#if report}
    <div class="result">
      <div class="level-badge" style:background={riskColors[report.level] ?? "#484f58"}>
        {report.level.toUpperCase()}
      </div>

      <div class="items">
        {#each report.items as item}
          <div class="item">
            <span class="item-what">{item.what}</span>
            <span class="item-dest">{item.destination}</span>
            <span class="item-risk" style:color={riskColors[item.risk] ?? "#8b949e"}>
              {item.risk}
            </span>
          </div>
        {/each}
      </div>
    </div>
  {/if}

  <div class="info-card">
    <h3>Уровни риска</h3>
    <div class="risk-legend">
      <span class="legend-item"><span class="dot" style:background="#2ea043"></span> Green — всё локально</span>
      <span class="legend-item"><span class="dot" style:background="#d29922"></span> Yellow — данные покидают контекст</span>
      <span class="legend-item"><span class="dot" style:background="#f85149"></span> Red — данные уходят на внешний API</span>
    </div>
  </div>
</div>

<style>
  .privacy-panel {
    max-width: 600px;
  }

  h2 {
    font-size: 22px;
    margin-bottom: 8px;
  }

  .description {
    color: #8b949e;
    font-size: 14px;
    margin-bottom: 20px;
  }

  textarea {
    width: 100%;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px;
    background: #0d1117;
    color: #e1e4e8;
    font: inherit;
    font-size: 14px;
    resize: none;
  }

  textarea:focus {
    outline: none;
    border-color: #58a6ff;
  }

  button {
    margin-top: 8px;
    background: #1f6feb;
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    cursor: pointer;
    font: inherit;
    font-size: 14px;
  }

  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .result {
    margin-top: 20px;
    padding: 16px;
    border: 1px solid #21262d;
    border-radius: 8px;
    background: #161b22;
  }

  .level-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 13px;
    font-weight: 700;
    color: #fff;
    margin-bottom: 12px;
  }

  .items {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .item {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 13px;
  }

  .item-what {
    font-weight: 600;
    min-width: 100px;
  }

  .item-dest {
    color: #8b949e;
    flex: 1;
  }

  .item-risk {
    font-weight: 600;
    text-transform: uppercase;
    font-size: 12px;
  }

  .info-card {
    margin-top: 24px;
    padding: 16px;
    border: 1px solid #21262d;
    border-radius: 8px;
    background: #161b22;
  }

  .info-card h3 {
    font-size: 15px;
    margin-bottom: 10px;
    color: #58a6ff;
  }

  .risk-legend {
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 13px;
    color: #8b949e;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
  }
</style>
