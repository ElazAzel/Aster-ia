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
    apiBase,
    auditLogs,
    refreshAuditLogs,
    telemetryOptIn,
    reportTelemetryEvent
  } from './stores';
  import { getGpuInfo, installOllama } from './tauri';
  import { exportSystemData, importSystemData, wipeSystemData } from './api';
  import ModelCookbook from './ModelCookbook.svelte';

  let detectedGpus: Array<{ name: string; vram_gb: number }> = [];
  let ollamaInstallStatus = '';
  let ollamaInstalling = false;

  let passphrase = '';
  let importInputText = '';
  let confirmWipe = false;
  let operationStatus = '';
  let operationError = '';

  async function detectHardware() {
    if ($desktopAvailable) {
      try {
        const info = await getGpuInfo();
        detectedGpus = info;
        if (info.length > 0) {
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

  async function handleExport() {
    operationStatus = '';
    operationError = '';
    try {
      const res = await exportSystemData($apiBase, passphrase);
      if (res.backup) {
        importInputText = res.backup;
        operationStatus = 'Резервная копия успешно создана и скопирована в поле ввода ниже!';
        if (navigator.clipboard) {
          await navigator.clipboard.writeText(res.backup);
          operationStatus += ' Текст бэкапа также скопирован в ваш буфер обмена.';
        }
      }
    } catch (err: any) {
      operationError = `Ошибка экспорта: ${err.message || err}`;
    }
  }

  async function handleImport() {
    operationStatus = '';
    operationError = '';
    try {
      const res = await importSystemData($apiBase, importInputText, passphrase);
      if (res.ok) {
        operationStatus = 'Данные успешно импортированы! Перезагрузите или обновите данные.';
        importInputText = '';
        passphrase = '';
      }
    } catch (err: any) {
      operationError = `Ошибка импорта (неверный пароль или поврежденный файл): ${err.message || err}`;
    }
  }

  async function handleWipe() {
    operationStatus = '';
    operationError = '';
    if (!confirmWipe) return;
    try {
      const res = await wipeSystemData($apiBase);
      if (res.ok) {
        operationStatus = 'Все локальные данные безвозвратно удалены! Приложение очищено.';
        confirmWipe = false;
        passphrase = '';
        importInputText = '';
        void refreshAuditLogs();
      }
    } catch (err: any) {
      operationError = `Ошибка очистки: ${err.message || err}`;
    }
  }

  onMount(() => {
    void detectHardware();
    void refreshAuditLogs();
  });

  $: if ($telemetryOptIn) {
    void reportTelemetryEvent('telemetry_opt_in_changed', { enabled: true });
  }
</script>

<div class="tab-content">
  <div class="system-sections">
    <!-- Секция: Инфраструктура -->
    <div>
      <h3 class="system-section-header">Инфраструктура</h3>
      <div class="system-grid-2">
        <section class="panel">
          <div class="panel-heading compact">
            <h2>Sidecar сервис</h2>
            <span class:ok={$desktopStatus?.running} class:warn={!$desktopStatus?.running} class="status-dot"></span>
          </div>
          <p class="desktop-note">
            {$desktopAvailable ? 'Tauri IPC активна. FastAPI бэкенд управляется из приложения.' : 'Браузерный режим. Управление sidecar заблокировано.'}
          </p>
          <div class="button-grid">
            <button type="button" on:click={startDesktopBackend} disabled={!$desktopAvailable}>Запустить</button>
            <button type="button" class="secondary" on:click={checkDesktopBackend} disabled={!$desktopAvailable}>Health</button>
            <button type="button" class="secondary" on:click={stopDesktopBackend} disabled={!$desktopAvailable}>Стоп</button>
          </div>
          {#if $desktopAvailable}
            <div class="config-divider">
              <span class="config-label">Не установлен Ollama?</span>
              <button type="button" class="secondary" on:click={handleInstallOllama} disabled={ollamaInstalling}>
                {ollamaInstalling ? 'Установка...' : 'Скачать и установить Ollama'}
              </button>
              {#if ollamaInstallStatus}
                <div class="status-text">{ollamaInstallStatus}</div>
              {/if}
            </div>
          {/if}
          {#if $desktopStatus}
            <div class="status-indicator">
              <span>Статус: <strong>{$desktopStatus.running ? 'запущен' : 'остановлен'}</strong></span>
              <span>Адрес: <strong>{$desktopStatus.host}:{$desktopStatus.port}</strong></span>
            </div>
          {/if}
        </section>

        <section class="panel">
          <div class="panel-heading compact">
            <h2>Model Router</h2>
          </div>
          <label class="config-label">
            <span>Описание целевой задачи</span>
            <input bind:value={$taskDescription} placeholder="Например: локальный чат для кодинга" />
          </label>
          <div class="split-controls">
            <label class="config-label">
              <span>VRAM видеокарты (ГБ)</span>
              <input type="number" min="0" step="1" bind:value={$vramGb} />
            </label>
            <label class="config-label">
              <span>RAM ОЗУ системы (ГБ)</span>
              <input type="number" min="0" step="1" bind:value={$ramGb} />
            </label>
          </div>
          {#if detectedGpus.length > 0}
            <div class="status-indicator">
              <span>Обнаружено:</span>
              {#each detectedGpus as gpu}
                <span><strong>{gpu.name}</strong> ({gpu.vram_gb} GB VRAM)</span>
              {/each}
            </div>
          {/if}
          <button type="button" on:click={routeModel}>Рассчитать оптимальную модель</button>
          {#if $modelSelection}
            <div class="plan-box">
              <strong>Оптимально: {$modelSelection.model}</strong>
              <span>Режим: {$modelSelection.mode === 'api' ? 'Внешний API' : 'Локальный вывод'}</span>
              <small>{$modelSelection.reason}</small>
            </div>
          {/if}
        </section>

        <section class="panel" class:grid-full={true}>
          <div class="panel-heading compact">
            <h2>Сервер подключения</h2>
          </div>
          <label class="config-label">
            <span>Базовый FastAPI URL</span>
            <input bind:value={$apiBase} style="font-family: var(--font-mono);" aria-label="FastAPI base URL" />
          </label>
          <small class="config-hint">Адрес для связи Tauri-клиента с серверным sidecar-модулем. Изменяйте только при переносе бэкенда.</small>
        </section>
      </div>
    </div>

    <!-- Секция: Модели -->
    <div>
      <h3 class="system-section-header">Модели</h3>
      <ModelCookbook />
    </div>

    <!-- Секция: Конфигурация -->
    <div>
      <h3 class="system-section-header">Конфигурация</h3>
      <div class="system-grid-2">
        <section class="panel">
          <div class="panel-heading compact">
            <h2>Системный промпт</h2>
            {#if $systemPromptSaved}
              <span class="status-text ok">Сохранено</span>
            {/if}
          </div>
          <label class="config-label">
            <span>Системный промпт для чата</span>
            <textarea bind:value={$systemPrompt} rows="4" class="mono-textarea" placeholder="Ты — полезный AI ассистент..."></textarea>
          </label>
          <button type="button" on:click={() => saveSystemPrompt($systemPrompt)}>Сохранить</button>
        </section>

        <section class="panel">
          <div class="panel-heading compact">
            <h2>Горячие клавиши</h2>
          </div>
          <div class="shortcut-list">
            <div><kbd>Ctrl+1-9</kbd><span>Переключить вкладку</span></div>
            <div><kbd>Ctrl+K</kbd><span>Следующая вкладка</span></div>
            <div><kbd>Ctrl+Shift+F</kbd><span>Полноэкранный режим</span></div>
            <div><kbd>Ctrl+Shift+Space</kbd><span>Свернуть/Развернуть окно</span></div>
            <div><kbd>Esc</kbd><span>Закрыть Privacy Radar</span></div>
            <div><kbd>Enter</kbd><span>Отправить сообщение</span></div>
          </div>
        </section>
      </div>
    </div>

    <!-- Секция: Аналитика и Телеметрия -->
    <div>
      <h3 class="system-section-header">Аналитика и Телеметрия</h3>
      <div class="system-grid-2">
        <section class="panel">
          <div class="panel-heading compact">
            <h2>Аналитика DuckDB</h2>
            <button type="button" class="text-button" on:click={fetchAnalyticsStats}>Обновить</button>
          </div>
          {#if $analyticsStats}
            <div class="analytics-kpi">
              <div>
                <strong>{$analyticsStats.total_research_queries}</strong>
                <small>Исследований</small>
              </div>
              <div>
                <strong>{$analyticsStats.sources_consulted}</strong>
                <small>Источников</small>
              </div>
              <div>
                <strong>{$analyticsStats.claims_verified}</strong>
                <small>Утверждений</small>
              </div>
            </div>
          {:else}
            <p class="empty">Нажмите «Обновить» для загрузки статистики DuckDB.</p>
          {/if}
        </section>

        <section class="panel">
          <div class="panel-heading compact">
            <h2>Телеметрия</h2>
            <span class:ok={$telemetryOptIn} class:warn={!$telemetryOptIn} class="status-dot"></span>
          </div>
          <p class="config-hint">
            Разрешить отправку полностью анонимных данных об использовании. Никакие сообщения, файлы или промпты не покидают локальный компьютер.
          </p>
          <label class="toggle-label">
            <input type="checkbox" bind:checked={$telemetryOptIn} />
            <span>Включить анонимную телеметрию (рекомендуется)</span>
          </label>
        </section>
      </div>
    </div>

    <!-- Секция: Данные и безопасность -->
    <div>
      <h3 class="system-section-header">Данные и безопасность</h3>
      <section class="panel">
        <div class="panel-heading compact">
          <h2>Резервное копирование</h2>
        </div>
        <div class="backup-layout">
          <div class="backup-controls">
            <label class="config-label">
              <span>Пароль шифрования</span>
              <input type="password" bind:value={passphrase} placeholder="Минимум 4 символа" />
            </label>
            <div class="button-grid">
              <button type="button" on:click={handleExport} disabled={!passphrase || passphrase.length < 4}>
                Экспортировать
              </button>
              <button type="button" class="secondary" on:click={handleImport} disabled={!passphrase || passphrase.length < 4 || !importInputText}>
                Импортировать
              </button>
            </div>
            <label class="config-label">
              <span>Данные бэкапа (Base64)</span>
              <textarea bind:value={importInputText} rows="3" class="mono-textarea" placeholder="Вставьте зашифрованный Base64 текст..."></textarea>
            </label>
          </div>
          <div class="danger-zone">
            <span class="danger-label">Опасная зона</span>
            <p>Полное удаление всех диалогов, комнат, воспоминаний, RAG-индексов и ключей из связки ОС. Восстановление невозможно!</p>
            <label class="toggle-label">
              <input type="checkbox" bind:checked={confirmWipe} />
              <span>Я подтверждаю удаление всех данных</span>
            </label>
            <button type="button" class="danger-btn" on:click={handleWipe} disabled={!confirmWipe}>
              Безвозвратно удалить всё
            </button>
          </div>
        </div>
        {#if operationStatus}
          <div class="status-banner ok">{operationStatus}</div>
        {/if}
        {#if operationError}
          <div class="status-banner error">{operationError}</div>
        {/if}
      </section>

      <section class="panel">
        <div class="panel-heading compact">
          <h2>Журнал безопасности</h2>
          <button type="button" class="text-button" on:click={refreshAuditLogs}>Обновить</button>
        </div>
        <div class="audit-table-wrapper">
          <table class="audit-table">
            <thead>
              <tr>
                <th>Время</th>
                <th>Действие</th>
                <th>Ресурс</th>
                <th>Детали</th>
              </tr>
            </thead>
            <tbody>
              {#each $auditLogs as log}
                <tr>
                  <td class="audit-ts">{new Date(log.ts).toLocaleString('ru')}</td>
                  <td>
                    <span class="audit-badge" class:approve={log.action === 'approve'} class:deny={log.action !== 'approve'}>
                      {log.action === 'approve' ? 'Разрешено' : 'Отклонено'}
                    </span>
                  </td>
                  <td class="audit-resource">{log.resource}</td>
                  <td class="audit-detail" title={log.details}>{log.details || '—'}</td>
                </tr>
              {:else}
                <tr>
                  <td colspan="4" class="audit-empty">Журнал действий пуст.</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </div>
</div>

<style>
  .desktop-note {
    font-size: 13.5px;
    line-height: 1.5;
    color: var(--text-secondary);
  }
  .config-divider {
    margin-top: 12px;
    border-top: 1px solid var(--border-color);
    padding-top: 12px;
  }
  .config-label {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .config-label > span {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-secondary);
  }
  .config-hint {
    font-size: 12px;
    color: var(--text-muted);
    line-height: 1.4;
  }
  .status-indicator {
    background: var(--bg-input);
    padding: 10px 14px;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    font-family: var(--font-mono);
    font-size: 12px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .status-text {
    font-size: 11px;
    color: var(--color-yellow-text);
    margin-top: 6px;
  }
  .status-text.ok {
    color: var(--color-green-text);
  }
  .mono-textarea {
    font-size: 12px;
    padding: 8px 10px;
    font-family: var(--font-mono);
  }
  .shortcut-list {
    font-size: 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    color: var(--text-secondary);
  }
  .shortcut-list > div {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .shortcut-list kbd {
    background: var(--bg-input);
    padding: 2px 8px;
    border-radius: 4px;
    font-family: var(--font-mono);
    font-size: 11px;
    border: 1px solid var(--border-color);
  }
  .analytics-kpi {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
  }
  .analytics-kpi > div {
    background: var(--bg-input);
    padding: 12px;
    border-radius: 8px;
    text-align: center;
  }
  .analytics-kpi strong {
    font-size: 24px;
    color: var(--color-brand);
    display: block;
  }
  .analytics-kpi small {
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 4px;
  }
  .toggle-label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: var(--text-primary);
    user-select: none;
    cursor: pointer;
  }
  .backup-layout {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
  .backup-controls {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .danger-zone {
    display: flex;
    flex-direction: column;
    gap: 8px;
    border-left: 1px solid var(--border-color);
    padding-left: 16px;
  }
  .danger-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--color-red-text);
  }
  .danger-zone p {
    font-size: 12px;
    line-height: 1.5;
    color: var(--text-secondary);
    margin: 0;
  }
  .danger-btn {
    width: 100%;
    margin-top: 8px;
    font-size: 12.5px;
    background: #eb5757;
    color: #fff;
    border: none;
    min-height: 32px;
    border-radius: 8px;
    cursor: pointer;
  }
  .danger-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .status-banner {
    margin-top: 12px;
    padding: 10px;
    border-radius: 6px;
    font-size: 12px;
  }
  .status-banner.ok {
    background: rgba(39, 174, 96, 0.15);
    border: 1px solid rgba(39, 174, 96, 0.3);
    color: var(--color-green-text);
  }
  .status-banner.error {
    background: rgba(235, 87, 87, 0.15);
    border: 1px solid rgba(235, 87, 87, 0.3);
    color: var(--color-red-text);
  }
  .audit-table-wrapper {
    max-height: 320px;
    overflow-y: auto;
    border: 1px solid var(--border-color);
    border-radius: 8px;
  }
  .audit-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    text-align: left;
  }
  .audit-table th {
    background: var(--bg-input);
    border-bottom: 1px solid var(--border-color);
    padding: 10px;
    position: sticky;
    top: 0;
  }
  .audit-table td {
    padding: 8px 10px;
    border-bottom: 1px solid var(--border-color);
    font-family: var(--font-mono);
  }
  .audit-ts {
    white-space: nowrap;
    color: var(--text-muted);
  }
  .audit-resource {
    color: var(--text-primary);
    font-weight: 500;
  }
  .audit-detail {
    color: var(--text-secondary);
    max-width: 220px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .audit-badge {
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
  }
  .audit-badge.approve {
    background: rgba(39, 174, 96, 0.15);
    color: var(--color-green-text);
  }
  .audit-badge.deny {
    background: rgba(235, 87, 87, 0.15);
    color: var(--color-red-text);
  }
  .audit-empty {
    padding: 24px;
    text-align: center;
    color: var(--text-muted);
  }

  :global(.system-grid-2 .panel.grid-full) {
    grid-column: 1 / -1;
  }

  @media (max-width: 900px) {
    .backup-layout {
      grid-template-columns: 1fr;
    }
    .danger-zone {
      border-left: none;
      padding-left: 0;
      padding-top: 16px;
      border-top: 1px solid var(--border-color);
    }
    .analytics-kpi {
      grid-template-columns: 1fr;
    }
  }
</style>