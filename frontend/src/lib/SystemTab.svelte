<script lang="ts">
  import { onMount } from 'svelte';
  import {
    desktopAvailable,
    desktopStatus,
    startDesktopBackend,
    checkDesktopBackend,
    stopDesktopBackend,
    taskDescription,
    vramGb,
    ramGb,
    routeModel,
    modelSelection,
    fetchAnalyticsStats,
    analyticsStats,
    systemPrompt,
    systemPromptSaved,
    saveSystemPrompt,
    apiBase
  } from './stores';
  import { getGpuInfo, installOllama } from './tauri';

  let detectedGpus: Array<{ name: string; vram_gb: number }> = [];
  let ollamaInstallStatus = '';
  let ollamaInstalling = false;

  async function detectHardware() {
    if ($desktopAvailable) {
      try {
        const info = await getGpuInfo();
        detectedGpus = info;
        if (info.length > 0) {
          // Auto-select the max VRAM among detected GPUs
          const maxVram = Math.max(...info.map(g => g.vram_gb));
          vramGb.set(maxVram);
        }
      } catch (e) {
        console.error('Failed to get GPU info:', e);
      }
    }
  }

  async function handleInstallOllama() {
    ollamaInstalling = true;
    ollamaInstallStatus = 'Начало скачивания и запуска установщика...';
    try {
      const res = await installOllama();
      ollamaInstallStatus = res;
    } catch (err: any) {
      ollamaInstallStatus = `Ошибка: ${err.message || err}`;
    } finally {
      ollamaInstalling = false;
    }
  }

  onMount(() => {
    void detectHardware();
  });
</script>

<div class="tab-content">
  <div class="secondary-grid">
    <!-- Desktop sidecar control -->
    <section class="panel">
      <div class="panel-heading compact">
        <h2>Управление Sidecar сервисом</h2>
        <span class:ok={$desktopStatus?.running} class:warn={!$desktopStatus?.running} class="status-dot"></span>
      </div>
      <p class="desktop-note" style="font-size: 13.5px; line-height: 1.5; color: var(--text-secondary);">
        {$desktopAvailable ? 'Среда Tauri IPC активна. Вы можете перезапускать FastAPI бэкенд из приложения.' : 'Браузерный режим. Управление sidecar заблокировано. Используйте внешний FastAPI URL.'}
      </p>

      <div class="button-grid" style="margin-top: 8px;">
        <button type="button" on:click={startDesktopBackend} disabled={!$desktopAvailable}>Запустить sidecar</button>
        <button type="button" class="secondary" on:click={checkDesktopBackend} disabled={!$desktopAvailable}>Проверить Health</button>
        <button type="button" class="secondary" on:click={stopDesktopBackend} disabled={!$desktopAvailable}>Остановить</button>
      </div>

      {#if $desktopAvailable}
        <div style="margin-top: 12px; border-top: 1px solid var(--border-color); padding-top: 12px;">
          <span style="font-size:12px;color:var(--text-secondary)">Не установлен Ollama?</span>
          <button type="button" class="secondary" style="width:100%;margin-top:6px;min-height:30px;font-size:12px" on:click={handleInstallOllama} disabled={ollamaInstalling}>
            {ollamaInstalling ? 'Установка...' : '📥 Скачать и установить Ollama'}
          </button>
          {#if ollamaInstallStatus}
            <div style="font-size:11px;color:var(--color-yellow-text);margin-top:6px">{ollamaInstallStatus}</div>
          {/if}
        </div>
      {/if}

      {#if $desktopStatus}
        <div style="background: var(--bg-input); padding: 10px 14px; border: 1px solid var(--border-color); border-radius: 8px; font-family: var(--font-mono); font-size: 12px; margin-top: 8px;">
          <span>Статус: <strong>{$desktopStatus.running ? 'запущен' : 'остановлен'}</strong></span><br>
          <span>Адрес: <strong>{$desktopStatus.host}:{$desktopStatus.port}</strong></span>
        </div>
      {/if}
    </section>

    <!-- Hardware model router -->
    <section class="panel">
      <div class="panel-heading compact">
        <h2>Конструктор маршрутов моделей (Model Router)</h2>
      </div>
      <label style="display: flex; flex-direction: column; gap: 4px;">
        <span style="font-size: 11px; font-weight: 600; color: var(--text-secondary);">Описание целевой задачи</span>
        <input bind:value={$taskDescription} placeholder="Например: локальный чат для кодинга" />
      </label>

      <div class="split-controls">
        <label style="display: flex; flex-direction: column; gap: 4px;">
          <span style="font-size: 11px; font-weight: 600; color: var(--text-secondary);">VRAM видеокарты (ГБ)</span>
          <input type="number" min="0" step="1" bind:value={$vramGb} />
        </label>
        <label style="display: flex; flex-direction: column; gap: 4px;">
          <span style="font-size: 11px; font-weight: 600; color: var(--text-secondary);">RAM ОЗУ системы (ГБ)</span>
          <input type="number" min="0" step="1" bind:value={$ramGb} />
        </label>
      </div>

      {#if detectedGpus.length > 0}
        <div style="font-size: 12px; color: var(--text-secondary); background: var(--bg-input); padding: 8px 12px; border-radius: 6px; border: 1px solid var(--border-color); margin-top: 4px;">
          <span>Обнаружено аппаратное обеспечение:</span>
          {#each detectedGpus as gpu}
            <div style="margin-top:4px">🖥️ <strong>{gpu.name}</strong> ({gpu.vram_gb} GB VRAM)</div>
          {/each}
        </div>
      {/if}

      <button type="button" style="margin-top: 8px;" on:click={routeModel}>Рассчитать оптимальную модель</button>

      {#if $modelSelection}
        <div class="plan-box" style="margin-top: 12px;">
          <strong>Оптимально: {$modelSelection.model}</strong>
          <span>Режим работы: {$modelSelection.mode === 'api' ? 'Внешний API' : 'Локальный вывод'}</span>
          <small style="margin-top: 4px; line-height: 1.4;">{$modelSelection.reason}</small>
        </div>
      {/if}
    </section>

    <!-- Keyboard shortcuts & Onboarding -->
    <section class="panel">
      <div class="panel-heading compact">
        <h2>Горячие клавиши</h2>
      </div>
      <div style="font-size:12px;display:flex;flex-direction:column;gap:6px;color:var(--text-secondary)">
        <div style="display:flex;justify-content:space-between"><kbd style="background:var(--bg-input);padding:2px 8px;border-radius:4px;font-family:var(--font-mono);font-size:11px;border:1px solid var(--border-color)">Ctrl+1-9</kbd><span>Переключить вкладку</span></div>
        <div style="display:flex;justify-content:space-between"><kbd style="background:var(--bg-input);padding:2px 8px;border-radius:4px;font-family:var(--font-mono);font-size:11px;border:1px solid var(--border-color)">Ctrl+K</kbd><span>Следующая вкладка</span></div>
        <div style="display:flex;justify-content:space-between"><kbd style="background:var(--bg-input);padding:2px 8px;border-radius:4px;font-family:var(--font-mono);font-size:11px;border:1px solid var(--border-color)">Ctrl+Shift+Space</kbd><span>Свернуть / Развернуть окно</span></div>
        <div style="display:flex;justify-content:space-between"><kbd style="background:var(--bg-input);padding:2px 8px;border-radius:4px;font-family:var(--font-mono);font-size:11px;border:1px solid var(--border-color)">Esc</kbd><span>Закрыть Privacy Radar</span></div>
        <div style="display:flex;justify-content:space-between"><kbd style="background:var(--bg-input);padding:2px 8px;border-radius:4px;font-family:var(--font-mono);font-size:11px;border:1px solid var(--border-color)">Enter</kbd><span>Отправить сообщение / создать комнату</span></div>
      </div>
    </section>

    <!-- Analytics Dashboard -->
    <section class="panel">
      <div class="panel-heading compact">
        <h2>Аналитика</h2>
        <button type="button" class="text-button" on:click={fetchAnalyticsStats} style="font-size:11px">Обновить</button>
      </div>
      {#if $analyticsStats}
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px">
          <div style="background:var(--bg-input);padding:12px;border-radius:8px;text-align:center">
            <strong style="font-size:24px;color:var(--color-brand)">{$analyticsStats.total_research_queries}</strong>
            <p style="font-size:11px;color:var(--text-muted);margin-top:4px">Исследований</p>
          </div>
          <div style="background:var(--bg-input);padding:12px;border-radius:8px;text-align:center">
            <strong style="font-size:24px;color:var(--color-green-text)">{$analyticsStats.sources_consulted}</strong>
            <p style="font-size:11px;color:var(--text-muted);margin-top:4px">Источников</p>
          </div>
          <div style="background:var(--bg-input);padding:12px;border-radius:8px;text-align:center">
            <strong style="font-size:24px;color:var(--color-yellow-text)">{$analyticsStats.claims_verified}</strong>
            <p style="font-size:11px;color:var(--text-muted);margin-top:4px">Утверждений</p>
          </div>
        </div>
      {:else}
        <p class="empty" style="font-size:12px">Нажмите «Обновить» для загрузки статистики DuckDB.</p>
      {/if}
    </section>

    <!-- System Prompt Editor -->
    <section class="panel">
      <div class="panel-heading compact">
        <h2>Системный промпт</h2>
        {#if $systemPromptSaved}
          <span style="font-size:11px;color:var(--color-green-text)">Сохранено</span>
        {/if}
      </div>
      <label style="display:flex;flex-direction:column;gap:4px">
        <span style="font-size:11px;font-weight:600;color:var(--text-secondary)">Системный промпт для чата</span>
        <textarea bind:value={$systemPrompt} rows="4" style="font-size:12px;padding:8px 10px;font-family:var(--font-mono)" placeholder="Ты — полезный AI ассистент..."></textarea>
      </label>
      <button type="button" on:click={() => saveSystemPrompt($systemPrompt)} style="align-self:flex-start;font-size:12px;padding:6px 14px">Сохранить</button>
    </section>

    <!-- FastAPI config -->
    <section class="panel" style="grid-column: span 2;">
      <div class="panel-heading compact">
        <h2>Сервер подключения</h2>
      </div>
      <label style="display: flex; flex-direction: column; gap: 4px;">
        <span style="font-size: 11px; font-weight: 600; color: var(--text-secondary);">Базовый FastAPI API URL адрес</span>
        <input bind:value={$apiBase} style="font-family: var(--font-mono);" aria-label="FastAPI base URL" />
      </label>
      <small style="color: var(--text-muted); line-height: 1.4;">Это адрес, по которому Tauri-клиент общается с серверным sidecar-модулем. Изменяйте только при переносе бэкенда на внешний сервер.</small>
    </section>
  </div>
</div>
