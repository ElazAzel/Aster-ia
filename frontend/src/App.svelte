<script lang="ts">
  // Contract check: Интерактивный чат
  import { onMount, onDestroy } from 'svelte';
  import {
    activeTab,
    roomId,
    selectedModel,
    rooms,
    models,
    statusText,
    errorText,
    clearError,
    showLeftPanel,
    showRightPanel,
    desktopAvailable,
    apiBase,
    refreshAll,
    checkDesktopBackend,
    privacyPopoverOpen,
    activeConsentRequest,
    showOnboarding,
    showCommandPalette,
    reportTelemetryEvent,
    telemetryOptIn,
    stopAgentRunEvents
  } from './lib/stores';

  // Import Svelte Components
  import SideRail from './lib/SideRail.svelte';
  import TopBar from './lib/TopBar.svelte';
  import OnboardingWizard from './lib/OnboardingWizard.svelte';
  import CommandPalette from './lib/CommandPalette.svelte';
  import ContextPanel from './lib/ContextPanel.svelte';
  import Workbench from './lib/Workbench.svelte';
  import StreamingChat from './lib/StreamingChat.svelte';
  import ToastContainer from './lib/ToastContainer.svelte';
  import VoiceTab from './lib/VoiceTab.svelte';

  // Import Tab Components
  import AgentLabTab from './lib/AgentLabTab.svelte';
  import VaultTab from './lib/VaultTab.svelte';
  import ResearchTab from './lib/ResearchTab.svelte';
  import SystemTab from './lib/SystemTab.svelte';
  import DeepResearchTab from './lib/DeepResearchTab.svelte';
  import ImageStudioTab from './lib/ImageStudioTab.svelte';
  import AutomationTab from './lib/AutomationTab.svelte';
  import ArtifactsTab from './lib/ArtifactsTab.svelte';
  import PluginsTab from './lib/PluginsTab.svelte';
  import BenchmarkTab from './lib/BenchmarkTab.svelte';
  import AnalyticsTab from './lib/AnalyticsTab.svelte';
  import CommandCenterTab from './lib/CommandCenterTab.svelte';

  import { isTauriRuntime, toggleFullscreen } from './lib/tauri';

  const isSplash = typeof window !== 'undefined' && window.location.search.includes('splash=true');

  const TAB_TABS = [
    'command_center',
    'chat',
    'voice',
    'agents',
    'vault',
    'research',
    'system',
    'research_deep',
    'images',
    'automation',
    'artifacts_browser',
    'plugins',
    'benchmark',
    'analytics'
  ] as const;

  // Reactively calculate layout class based on panels visibility
  $: workbenchLayoutClass = $showLeftPanel && $showRightPanel
    ? 'layout-default'
    : $showLeftPanel && !$showRightPanel
      ? 'layout-left-only'
      : !$showLeftPanel && $showRightPanel
        ? 'layout-right-only'
        : 'layout-full-chat';

  function handleKeydown(event: KeyboardEvent) {
    if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
      event.preventDefault();
      $showCommandPalette = !$showCommandPalette;
    }
    if ((event.metaKey || event.ctrlKey) && event.key >= '1' && event.key <= '9') {
      event.preventDefault();
      const idx = parseInt(event.key) - 1;
      if (idx < TAB_TABS.length) $activeTab = TAB_TABS[idx];
    }
    if ((event.metaKey || event.ctrlKey) && event.shiftKey && (event.key === 'f' || event.key === 'F')) {
      event.preventDefault();
      void toggleFullscreen();
    }
    if (event.key === 'Escape') {
      $privacyPopoverOpen = false;
    }
  }

  // Clear error when switching tabs
  $: if ($activeTab) clearError();

  // Auto-dismiss error after 8s
  let errorTimer: ReturnType<typeof setTimeout> | undefined;
  $: {
    if ($errorText) {
      if (errorTimer) clearTimeout(errorTimer);
      errorTimer = setTimeout(() => { clearError(); }, 8000);
    }
  }

  let telemetryUnsub: (() => void) | undefined;

  onMount(() => {
    $desktopAvailable = isTauriRuntime();
    if (!isSplash) {
      void refreshAll();
      if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
      }
      document.addEventListener('keydown', handleKeydown);
      void reportTelemetryEvent('app_start');

      telemetryUnsub = telemetryOptIn.subscribe(val => {
        if (typeof localStorage !== 'undefined') {
          localStorage.setItem('asterion_telemetry_opt_in', val ? 'true' : 'false');
        }
      });
    }
  });

  onDestroy(() => {
    if (!isSplash) {
      document.removeEventListener('keydown', handleKeydown);
      stopAgentRunEvents();
      if (errorTimer) clearTimeout(errorTimer);
      if (telemetryUnsub) telemetryUnsub();
    }
  });
</script>

<svelte:head>
  <title>Asterion AI Workspace</title>
  <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
  <link rel="alternate icon" type="image/x-icon" href="/favicon.ico" />
</svelte:head>

{#if isSplash}
  <div class="splashscreen-view">
    <div class="splash-logo">✦</div>
    <div class="splash-title">Asterion AI</div>
    <div class="splash-subtitle">Инициализация локального AI-окружения...</div>
    <div class="spinner"></div>
  </div>
{:else}
  <div class="app-shell">
    <!-- Background mesh gradient glow spheres -->
    <div class="bg-gradient-glow">
      <div class="glow-sphere-3"></div>
    </div>

    <SideRail />

    <!-- Workspace Canvas -->
    <main class="workspace">
      <TopBar />

      <!-- Error/Status notice -->
      {#if $errorText}
        <div class="notice error" style="display:flex;justify-content:space-between;align-items:center">
          <span>{$errorText}</span>
          <button type="button" class="text-button" on:click={clearError} style="font-size:12px;margin-left:12px">✕</button>
        </div>
      {:else if $statusText && $statusText !== 'Готово'}
        <p class="notice">{$statusText}</p>
      {/if}

      <!-- Tab Contents -->
      {#if $activeTab === 'command_center'}
        <CommandCenterTab />
      {:else if $activeTab === 'chat'}
        <!-- Three-column Workbench Layout -->
        <div class="workbench-layout {workbenchLayoutClass}">
          <ContextPanel />

          <!-- Center Panel — Chat -->
          <main class="center-panel" style="display: flex; flex-direction: column; height: 100%; overflow: hidden;">
            <StreamingChat
              apiBase={$apiBase}
              roomId={$roomId}
              model={$selectedModel}
              rooms={$rooms}
              modelNames={$models.map(m => m.name)}
            />
          </main>

          <Workbench />
        </div>

      {:else if $activeTab === 'agents'}
        <AgentLabTab />

      {:else if $activeTab === 'voice'}
        <VoiceTab />

      {:else if $activeTab === 'vault'}
        <VaultTab />

      {:else if $activeTab === 'research'}
        <ResearchTab />

      {:else if $activeTab === 'system'}
        <SystemTab />

      {:else if $activeTab === 'research_deep'}
        <DeepResearchTab />

      {:else if $activeTab === 'images'}
        <ImageStudioTab />

      {:else if $activeTab === 'automation'}
        <AutomationTab />

      {:else if $activeTab === 'artifacts_browser'}
        <ArtifactsTab />

      {:else if $activeTab === 'plugins'}
        <PluginsTab />

      {:else if $activeTab === 'benchmark'}
        <BenchmarkTab />

      {:else if $activeTab === 'analytics'}
        <AnalyticsTab />
      {/if}
    </main>
    
    {#if $activeConsentRequest}
      <div class="modal-overlay" role="presentation" on:click|self={$activeConsentRequest.onDeny} on:keydown|self={$activeConsentRequest.onDeny}>
        <div class="consent-modal">
          <div class="modal-header">
            <h3>🛡️ Запрос согласия на операцию</h3>
            <span class="privacy-badge {$activeConsentRequest.privacyLevel}">
              {$activeConsentRequest.privacyLevel === 'local' ? 'Локально' : $activeConsentRequest.privacyLevel === 'hybrid' ? 'Гибридно' : 'Внешний API'}
            </span>
          </div>
          <div class="modal-body">
            <strong>{$activeConsentRequest.title}</strong>
            <p>{$activeConsentRequest.description}</p>
            
            <div class="privacy-info-box">
              {#if $activeConsentRequest.privacyLevel === 'local'}
                <p class="green">✔ Данные не покидают ваше устройство.</p>
              {:else if $activeConsentRequest.privacyLevel === 'hybrid'}
                <p class="yellow">⚠ Эта операция может передавать агрегированные запросы или данные на локальный поисковый провайдер.</p>
              {:else}
                <p class="red">✖ Внимание! Данные будут отправлены внешним провайдерам или моделям API.</p>
              {/if}
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="secondary" on:click={$activeConsentRequest.onDeny}>Отклонить</button>
            <button type="button" class="approve-btn" on:click={$activeConsentRequest.onApprove}>Разрешить</button>
          </div>
        </div>
      </div>
    {/if}
    <ToastContainer />
    {#if $showOnboarding}
      <OnboardingWizard />
    {/if}
    {#if $showCommandPalette}
      <CommandPalette />
    {/if}
  </div>
{/if}

<style>
  .splashscreen-view {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 100vw;
    height: 100vh;
    background: #08080c;
    color: #f3f4f6;
    font-family: 'Outfit', sans-serif;
    user-select: none;
    position: relative;
    overflow: hidden;
  }

  .splash-logo {
    font-size: 64px;
    background: linear-gradient(135deg, #7c6dfa 0%, #a89eff 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 24px;
    animation: pulse 2s infinite ease-in-out;
  }

  .splash-title {
    font-size: 24px;
    font-weight: 700;
    letter-spacing: -0.03em;
    margin-bottom: 8px;
    background: linear-gradient(to right, #ffffff, #9ca3af);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .splash-subtitle {
    font-size: 13px;
    color: #9ca3af;
    margin-bottom: 32px;
  }

  .spinner {
    width: 28px;
    height: 28px;
    border: 2px solid rgba(124, 109, 250, 0.1);
    border-top: 2px solid #7c6dfa;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  @keyframes pulse {
    0%, 100% { transform: scale(1); opacity: 0.8; }
    50% { transform: scale(1.1); opacity: 1; }
  }

  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(8, 8, 12, 0.75);
    backdrop-filter: blur(12px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
  }

  .consent-modal {
    background: rgba(18, 18, 26, 0.85);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    width: 90%;
    max-width: 480px;
    padding: 24px;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
    font-family: inherit;
    animation: scaleUp 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  }

  @keyframes scaleUp {
    from { transform: scale(0.95); opacity: 0; }
    to { transform: scale(1); opacity: 1; }
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    border-bottom: 1px solid var(--border-color);
    padding-bottom: 12px;
  }

  .modal-header h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 700;
  }

  .privacy-badge {
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
  }

  .privacy-badge.local {
    background: rgba(39, 174, 96, 0.15);
    color: var(--color-green-text);
  }

  .privacy-badge.hybrid {
    background: rgba(242, 201, 76, 0.15);
    color: var(--color-yellow-text);
  }

  .privacy-badge.external {
    background: rgba(235, 87, 87, 0.15);
    color: var(--color-red-text);
  }

  .modal-body {
    font-size: 13.5px;
    line-height: 1.5;
    margin-bottom: 24px;
  }

  .modal-body strong {
    display: block;
    margin-bottom: 8px;
    color: var(--text-primary);
  }

  .modal-body p {
    color: var(--text-secondary);
    margin: 0 0 16px 0;
  }

  .privacy-info-box {
    background: var(--bg-input);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 12px;
  }

  .privacy-info-box p {
    margin: 0;
    font-size: 12px;
    line-height: 1.4;
  }

  .privacy-info-box p.green {
    color: var(--color-green-text);
  }

  .privacy-info-box p.yellow {
    color: var(--color-yellow-text);
  }

  .privacy-info-box p.red {
    color: var(--color-red-text);
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
  }

  .modal-footer button {
    font-size: 12.5px;
    padding: 8px 18px;
    min-height: 36px;
  }

  .modal-footer button.approve-btn {
    background: #27ae60;
    color: #fff;
    border: none;
  }

  .modal-footer button.approve-btn:hover {
    background: #219653;
  }
</style>
