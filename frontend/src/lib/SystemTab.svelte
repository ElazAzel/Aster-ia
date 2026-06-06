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

  let detectedGpus: Array<{ name: string; vram_gb: number }> = [];
  let ollamaInstallStatus = '';
  let ollamaInstalling = false;

  // Data management variables
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

    <!-- Telemetry config -->
    <section class="panel" style="grid-column: span 2;">
      <div class="panel-heading compact">
        <h2>Телеметрия и аналитика</h2>
        <span class:ok={$telemetryOptIn} class:warn={!$telemetryOptIn} class="status-dot"></span>
      </div>
      <p style="font-size: 13px; line-height: 1.5; color: var(--text-secondary); margin-bottom: 12px; margin-top: 4px;">
        Разрешить отправку полностью анонимных данных об использовании и возникающих ошибках.
        Мы собираем только обезличенные технические параметры (платформа, объем RAM/VRAM, тип события)
        для улучшения стабильности Asterion AI. Никакие ваши сообщения, файлы, личные данные или промпты
        никогда не покидают локальный компьютер в соответствии с контрактом Local-first.
      </p>
      <label style="display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-primary); user-select: none; cursor: pointer;">
        <input type="checkbox" bind:checked={$telemetryOptIn} />
        <span>Включить анонимную телеметрию (Рекомендуется)</span>
      </label>
    </section>

    <!-- Data Management & Backups -->
    <section class="panel" style="grid-column: span 2;">
      <div class="panel-heading compact">
        <h2>Управление данными и резервное копирование</h2>
      </div>
      
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 8px;">
        <div style="display: flex; flex-direction: column; gap: 12px;">
          <label style="display: flex; flex-direction: column; gap: 4px;">
            <span style="font-size: 11px; font-weight: 600; color: var(--text-secondary);">Пароль шифрования бэкапа</span>
            <input type="password" bind:value={passphrase} placeholder="Минимум 4 символа" style="font-size:12.5px" />
          </label>
          
          <div style="display: flex; gap: 8px;">
            <button type="button" on:click={handleExport} disabled={!passphrase || passphrase.length < 4} style="flex:1;font-size:12px;min-height:30px">
              📥 Экспортировать бэкап
            </button>
            <button type="button" class="secondary" on:click={handleImport} disabled={!passphrase || passphrase.length < 4 || !importInputText} style="flex:1;font-size:12px;min-height:30px">
              📤 Импортировать бэкап
            </button>
          </div>
          
          <label style="display: flex; flex-direction: column; gap: 4px; margin-top: 4px;">
            <span style="font-size: 11px; font-weight: 600; color: var(--text-secondary);">Данные бэкапа (Base64 текст)</span>
            <textarea bind:value={importInputText} rows="3" placeholder="Вставьте сюда зашифрованный Base64 текст для восстановления..." style="font-size:11px; font-family:var(--font-mono); padding:6px;"></textarea>
          </label>
        </div>

        <div style="display: flex; flex-direction: column; justify-content: space-between; border-left: 1px solid var(--border-color); padding-left: 16px;">
          <div>
            <span style="font-size: 12px; font-weight: 600; color: var(--color-red-text);">⚠️ Опасная зона</span>
            <p style="font-size: 12px; line-height: 1.5; color: var(--text-secondary); margin: 6px 0 12px 0;">
              Полное удаление всех ваших диалогов, комнат, локальных воспоминаний, RAG-индексов и ключей из связки ключей ОС. Восстановление будет невозможно!
            </p>
            <label style="display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text-secondary); user-select: none;">
              <input type="checkbox" bind:checked={confirmWipe} />
              <span>Я подтверждаю полное удаление данных</span>
            </label>
          </div>
          
          <button type="button" class="danger-btn" on:click={handleWipe} disabled={!confirmWipe} style="width:100%; margin-top: 12px; font-size:12.5px; background: #eb5757; color:#fff; border:none; min-height: 32px;">
            💥 Безвозвратно удалить все данные
          </button>
        </div>
      </div>

      {#if operationStatus}
        <div style="margin-top: 12px; padding: 10px; background: rgba(39, 174, 96, 0.15); border: 1px solid rgba(39, 174, 96, 0.3); border-radius: 6px; font-size: 12px; color: var(--color-green-text);">
          {operationStatus}
        </div>
      {/if}
      {#if operationError}
        <div style="margin-top: 12px; padding: 10px; background: rgba(235, 87, 87, 0.15); border: 1px solid rgba(235, 87, 87, 0.3); border-radius: 6px; font-size: 12px; color: var(--color-red-text);">
          {operationError}
        </div>
      {/if}
    </section>

    <!-- Audit & Consent Log Table -->
    <section class="panel" style="grid-column: span 2;">
      <div class="panel-heading compact">
        <h2>Журнал безопасности и согласий</h2>
        <button type="button" class="text-button" on:click={refreshAuditLogs} style="font-size:11px">Обновить</button>
      </div>
      
      <div style="max-height: 280px; overflow-y: auto; border: 1px solid var(--border-color); border-radius: 8px;">
        <table style="width: 100%; border-collapse: collapse; font-size: 12px; text-align: left;">
          <thead>
            <tr style="background: var(--bg-input); border-bottom: 1px solid var(--border-color);">
              <th style="padding: 10px;">Время</th>
              <th style="padding: 10px;">Действие</th>
              <th style="padding: 10px;">Ресурс</th>
              <th style="padding: 10px;">Детали</th>
            </tr>
          </thead>
          <tbody>
            {#each $auditLogs as log}
              <tr style="border-bottom: 1px solid var(--border-color); font-family: var(--font-mono);">
                <td style="padding: 8px 10px; white-space: nowrap; color: var(--text-muted);">
                  {new Date(log.ts).toLocaleString('ru')}
                </td>
                <td style="padding: 8px 10px;">
                  <span class="status-badge" style="padding: 2px 6px; border-radius: 4px; font-size:10px; font-weight:700; text-transform:uppercase; background: {log.action === 'approve' ? 'rgba(39,174,96,0.15)' : 'rgba(235,87,87,0.15)'}; color: {log.action === 'approve' ? 'var(--color-green-text)' : 'var(--color-red-text)'};">
                    {log.action === 'approve' ? 'Разрешено' : 'Отклонено'}
                  </span>
                </td>
                <td style="padding: 8px 10px; color: var(--text-primary); font-weight: 500;">
                  {log.resource}
                </td>
                <td style="padding: 8px 10px; color: var(--text-secondary); max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title={log.details}>
                  {log.details || '—'}
                </td>
              </tr>
            {:else}
              <tr>
                <td colspan="4" style="padding: 24px; text-align: center; color: var(--text-muted);">
                  Журнал действий пуст.
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>
  </div>
</div>
