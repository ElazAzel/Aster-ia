<script lang="ts">
  const API_BASE = "http://127.0.0.1:8000";

  let models: string[] = [];
  let selectedModel = "llama3.2";
  let loading = false;
  let error = "";

  async function loadModels() {
    loading = true;
    error = "";
    try {
      const res = await fetch(`${API_BASE}/api/models`);
      const data = await res.json();
      models = data.models ?? [];
    } catch (e) {
      error = "Не удалось загрузить модели. Проверьте, запущен ли Ollama.";
    } finally {
      loading = false;
    }
  }

  async function selectModel() {
    try {
      await fetch(`${API_BASE}/api/models/select`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model: selectedModel }),
      });
    } catch (e) {
      error = "Ошибка выбора модели";
    }
  }

  loadModels();
</script>

<div class="model-settings">
  <h2>Настройки моделей</h2>

  {#if error}
    <p class="error">{error}</p>
  {/if}

  {#if loading}
    <p class="loading">Загрузка моделей...</p>
  {:else}
    <div class="model-list">
      <label for="model-select">Активная модель</label>
      <select id="model-select" bind:value={selectedModel} on:change={selectModel}>
        {#each models as model}
          <option value={model}>{model}</option>
        {/each}
      </select>
    </div>

    <button class="refresh-btn" on:click={loadModels}>Обновить список</button>

    <div class="info-card">
      <h3>Локальные модели</h3>
      <p>Все модели работают через Ollama на <code>127.0.0.1:11434</code>.</p>
      <p>Данные не покидают ваш компьютер.</p>
    </div>
  {/if}
</div>

<style>
  .model-settings {
    max-width: 600px;
  }

  h2 {
    font-size: 22px;
    margin-bottom: 20px;
    color: #e1e4e8;
  }

  .model-list {
    margin-bottom: 16px;
  }

  label {
    display: block;
    font-size: 13px;
    color: #8b949e;
    margin-bottom: 6px;
  }

  select {
    width: 100%;
    padding: 10px 12px;
    border: 1px solid #30363d;
    border-radius: 8px;
    background: #0d1117;
    color: #e1e4e8;
    font: inherit;
    font-size: 14px;
  }

  select:focus {
    outline: none;
    border-color: #58a6ff;
  }

  .refresh-btn {
    background: #30363d;
    color: #e1e4e8;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 8px 16px;
    cursor: pointer;
    font: inherit;
    font-size: 14px;
  }

  .refresh-btn:hover {
    background: #484f58;
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
    margin-bottom: 8px;
    color: #58a6ff;
  }

  .info-card p {
    font-size: 13px;
    color: #8b949e;
    line-height: 1.5;
  }

  code {
    background: #1c2128;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 13px;
  }

  .error {
    color: #f85149;
    margin-bottom: 12px;
  }

  .loading {
    color: #8b949e;
  }
</style>
