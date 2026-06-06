<script lang="ts">
  import {
    completeOnboarding,
    health,
    models,
    refreshHealth,
    refreshModels,
    roomDraft,
    addRoom,
    rooms
  } from './stores';
  import { onMount } from 'svelte';

  let currentStep = 1;
  let newRoomName = 'Разработка';

  onMount(async () => {
    await refreshHealth();
    await refreshModels();
  });

  async function handleAddRoomAndNext() {
    if (newRoomName.trim()) {
      $roomDraft = newRoomName.trim();
      await addRoom();
    }
    currentStep = 4;
  }

  function handleComplete() {
    completeOnboarding();
  }
</script>

<div class="onboarding-overlay" id="onboarding-overlay">
  <div class="onboarding-card">
    <div class="onboarding-header">
      <span class="logo">✦</span>
      <h2>Добро пожаловать в Asterion AI</h2>
      <span class="step-indicator">Шаг {currentStep} из 4</span>
    </div>

    <div class="onboarding-body">
      {#if currentStep === 1}
        <div class="step-content animate-fade">
          <h3>Ваш локальный AI-помощник</h3>
          <p>
            Asterion AI — это персональное рабочее пространство, ориентированное на максимальную конфиденциальность. 
            Все ваши запросы, файлы, воспоминания и сгенерированные данные остаются исключительно на вашей локальной машине.
          </p>
          <div class="features-list">
            <div class="feature-item">
              <strong>🔒 Конфиденциальность</strong>
              <span>Локальные модели Ollama и шифрованная база данных SQLCipher защищают ваши секреты.</span>
            </div>
            <div class="feature-item">
              <strong>🧠 Долговременная память</strong>
              <span>Memory Ledger сохраняет важные факты о вас и ваших проектах.</span>
            </div>
            <div class="feature-item">
              <strong>📂 Локальный RAG (Vault)</strong>
              <span>Загружайте PDF, DOCX и текстовые файлы для моментального поиска по документации.</span>
            </div>
          </div>
        </div>
      {:else if currentStep === 2}
        <div class="step-content animate-fade">
          <h3>Проверка локального окружения</h3>
          <p>Для корректной работы требуется запущенный сервис Ollama.</p>
          
          <div class="status-panel">
            <div class="status-row">
              <span>FastAPI Sidecar:</span>
              <span class="status-val {$health ? 'ok' : 'error'}">
                {$health ? '● Активен' : '○ Недоступен'}
              </span>
            </div>
            <div class="status-row">
              <span>Локальный Ollama:</span>
              <span class="status-val {$health?.privacy?.ollama_status === 'online' ? 'ok' : 'warn'}">
                {$health?.privacy?.ollama_status === 'online' ? '● В сети' : '○ Не подключен'}
              </span>
            </div>
            <div class="status-row models-row">
              <span>Доступные модели:</span>
              {#if $models && $models.length > 0}
                <div class="model-tags">
                  {#each $models as model}
                    <span class="model-tag">{model.name}</span>
                  {/each}
                </div>
              {:else}
                <span class="text-warning">Модели не найдены. Убедитесь, что скачали модель через Ollama (например, llama3.2).</span>
              {/if}
            </div>
          </div>

          <button type="button" class="secondary" on:click={async () => { await refreshHealth(); await refreshModels(); }}>
            🔄 Обновить статус
          </button>
        </div>
      {:else if currentStep === 3}
        <div class="step-content animate-fade">
          <h3>Создайте первую комнату</h3>
          <p>
            Комнаты (Context Rooms) позволяют группировать диалоги, документы RAG и память по разным проектам или темам.
          </p>
          <form on:submit|preventDefault={handleAddRoomAndNext} class="stack-form">
            <label>
              <span>Название комнаты</span>
              <input type="text" bind:value={newRoomName} placeholder="Например: Работа, Учеба, Кодинг..." />
            </label>
            <p style="font-size: 11px; color: var(--text-muted)">
              Вы сможете настроить политику хранения памяти и ограничить список моделей в настройках комнаты.
            </p>
          </form>
        </div>
      {:else if currentStep === 4}
        <div class="step-content animate-fade">
          <h3>Все готово к работе!</h3>
          <p>Короткие советы для быстрого старта:</p>
          <div class="shortcuts-guide">
            <div class="shortcut-row">
              <kbd>Ctrl+K</kbd> / <kbd>Cmd+K</kbd>
              <span>Быстрый поиск комнат, агентов и запуск системных утилит через Command Palette.</span>
            </div>
            <div class="shortcut-row">
              <strong>Privacy Radar</strong>
              <span>Смотрите на круговой радар в правом верхнем углу. Он оценивает риски утечки PII (персональных данных) перед отправкой сообщений.</span>
            </div>
            <div class="shortcut-row">
              <strong>Workbench</strong>
              <span>Правая панель содержит три вкладки: Plan (планирование шагов агента), Logs (логи выполнения в реальном времени) и Artifacts (результаты работы).</span>
            </div>
          </div>
        </div>
      {/if}
    </div>

    <div class="onboarding-footer">
      {#if currentStep > 1}
        <button type="button" class="secondary" on:click={() => currentStep -= 1}>Назад</button>
      {/if}
      
      <div style="margin-left: auto;">
        {#if currentStep < 3}
          <button type="button" on:click={() => currentStep += 1}>Продолжить</button>
        {:else if currentStep === 3}
          <button type="button" on:click={handleAddRoomAndNext} disabled={!newRoomName.trim()}>Создать комнату</button>
        {:else}
          <button type="button" on:click={handleComplete} style="background: var(--color-green)">Начать работу ✨</button>
        {/if}
      </div>
    </div>
  </div>
</div>

<style>
  .onboarding-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(8, 8, 12, 0.85);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
  }

  .onboarding-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    width: 90%;
    max-width: 540px;
    display: flex;
    flex-direction: column;
    box-shadow: var(--shadow-premium);
    overflow: hidden;
    animation: zoomIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  }

  @keyframes zoomIn {
    from { transform: scale(0.96); opacity: 0; }
    to { transform: scale(1); opacity: 1; }
  }

  .onboarding-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 24px 32px;
    border-bottom: 1px solid var(--border-color);
  }

  .logo {
    font-size: 24px;
    background: linear-gradient(135deg, var(--color-brand) 0%, #a89eff 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700;
  }

  .onboarding-header h2 {
    font-size: 16px;
    font-weight: 600;
    margin: 0;
    color: var(--text-primary);
  }

  .step-indicator {
    margin-left: auto;
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .onboarding-body {
    padding: 32px;
    min-height: 280px;
    display: flex;
    flex-direction: column;
  }

  .step-content h3 {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 12px;
    color: var(--text-primary);
  }

  .step-content p {
    font-size: 13.5px;
    color: var(--text-secondary);
    line-height: 1.5;
    margin-bottom: 24px;
  }

  .features-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .feature-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .feature-item strong {
    font-size: 13px;
    color: var(--text-primary);
    font-weight: 600;
  }

  .feature-item span {
    font-size: 12px;
    color: var(--text-secondary);
    line-height: 1.4;
  }

  .status-panel {
    background: var(--bg-input);
    border: 1px solid var(--border-color);
    border-radius: 10px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 20px;
  }

  .status-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 13px;
    color: var(--text-secondary);
  }

  .status-val {
    font-weight: 600;
  }

  .status-val.ok { color: var(--color-green-text); }
  .status-val.warn { color: var(--color-yellow-text); }
  .status-val.error { color: var(--color-red-text); }

  .models-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
    border-top: 1px solid var(--border-color);
    padding-top: 12px;
  }

  .model-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .model-tag {
    font-size: 11px;
    font-family: var(--font-mono);
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    padding: 2px 8px;
    border-radius: 4px;
    color: var(--text-primary);
  }

  .text-warning {
    color: var(--color-yellow-text);
    font-size: 11.5px;
    line-height: 1.4;
  }

  .stack-form {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .stack-form label {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .stack-form label span {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary);
  }

  .shortcuts-guide {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .shortcut-row {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    font-size: 12.5px;
    color: var(--text-secondary);
    line-height: 1.4;
  }

  .shortcut-row kbd {
    background: var(--bg-input);
    border: 1px solid var(--border-color);
    padding: 2px 6px;
    border-radius: 4px;
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 600;
    color: var(--text-primary);
    box-shadow: 0 2px 0 var(--border-color);
    white-space: nowrap;
  }

  .shortcut-row strong {
    color: var(--text-primary);
    font-weight: 600;
    white-space: nowrap;
  }

  .onboarding-footer {
    display: flex;
    align-items: center;
    padding: 20px 32px;
    border-top: 1px solid var(--border-color);
    background: var(--bg-sidebar);
  }

  .onboarding-footer button {
    padding: 9px 24px;
    font-size: 13px;
  }

  .animate-fade {
    animation: fadeIn 0.3s ease-out forwards;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: translateY(0); }
  }
</style>
