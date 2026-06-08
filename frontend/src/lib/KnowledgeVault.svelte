<script lang="ts">
  const API_BASE = "http://127.0.0.1:8000";

  let query = "";
  let results: { id: string; content: string; source: string; score: number }[] = [];
  let searching = false;

  async function search() {
    if (!query.trim()) return;
    searching = true;
    try {
      const res = await fetch(`${API_BASE}/api/rag/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, room_id: "default", limit: 8 }),
      });
      results = await res.json();
    } catch (e) {
      results = [];
    } finally {
      searching = false;
    }
  }
</script>

<div class="knowledge-vault">
  <h2>Хранилище знаний</h2>
  <p class="description">Поиск по проиндексированным документам (RAG).</p>

  <form on:submit|preventDefault={search}>
    <input
      bind:value={query}
      type="text"
      placeholder="Поиск по документам..."
    />
    <button type="submit" disabled={searching || !query.trim()}>
      {searching ? "Поиск..." : "Найти"}
    </button>
  </form>

  {#if results.length > 0}
    <div class="results">
      {#each results as r}
        <div class="result-card">
          <div class="result-header">
            <span class="result-source">{r.source.split(/[/\\]/).pop()}</span>
            <span class="result-score">{(r.score * 100).toFixed(0)}%</span>
          </div>
          <p class="result-content">{r.content.slice(0, 300)}{r.content.length > 300 ? "..." : ""}</p>
        </div>
      {/each}
    </div>
  {:else if !searching && query}
    <p class="empty">Ничего не найдено</p>
  {/if}
</div>

<style>
  .knowledge-vault {
    max-width: 700px;
  }

  h2 { font-size: 22px; margin-bottom: 8px; }
  .description { color: #8b949e; font-size: 14px; margin-bottom: 20px; }

  form {
    display: flex;
    gap: 8px;
  }

  input {
    flex: 1;
    padding: 10px 12px;
    border: 1px solid #30363d;
    border-radius: 8px;
    background: #0d1117;
    color: #e1e4e8;
    font: inherit;
    font-size: 14px;
  }

  input:focus { outline: none; border-color: #58a6ff; }

  button {
    background: #1f6feb;
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    cursor: pointer;
    font: inherit;
    font-size: 14px;
  }

  button:disabled { opacity: 0.5; cursor: not-allowed; }

  .results {
    margin-top: 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .result-card {
    padding: 14px;
    border: 1px solid #21262d;
    border-radius: 8px;
    background: #161b22;
  }

  .result-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
  }

  .result-source {
    font-size: 13px;
    color: #58a6ff;
    font-weight: 600;
  }

  .result-score {
    font-size: 12px;
    color: #8b949e;
  }

  .result-content {
    font-size: 13px;
    color: #c9d1d9;
    line-height: 1.5;
  }

  .empty {
    margin-top: 16px;
    color: #484f58;
  }
</style>
