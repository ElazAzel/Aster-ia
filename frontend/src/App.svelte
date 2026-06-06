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
    privacyPopoverOpen
  } from './lib/stores';

  // Import Svelte Components
  import SideRail from './lib/SideRail.svelte';
  import TopBar from './lib/TopBar.svelte';
  import ContextPanel from './lib/ContextPanel.svelte';
  import Workbench from './lib/Workbench.svelte';
  import StreamingChat from './lib/StreamingChat.svelte';

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

  import { isTauriRuntime } from './lib/tauri';

  const isSplash = typeof window !== 'undefined' && window.location.search.includes('splash=true');

  const TAB_TABS = [
    'chat',
    'agents',
    'vault',
    'research',
    'system',
    'research_deep',
    'images',
    'automation',
    'artifacts_browser',
    'plugins'
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
      const tabIndex = TAB_TABS.indexOf($activeTab as typeof TAB_TABS[number]);
      const nextTab = TAB_TABS[(tabIndex + 1) % TAB_TABS.length];
      $activeTab = nextTab;
    }
    if ((event.metaKey || event.ctrlKey) && event.key >= '1' && event.key <= '9') {
      event.preventDefault();
      const idx = parseInt(event.key) - 1;
      if (idx < TAB_TABS.length) $activeTab = TAB_TABS[idx];
    }
    if (event.key === 'Escape') {
      $privacyPopoverOpen = false;
    }
  }

  onMount(() => {
    $desktopAvailable = isTauriRuntime();
    if (!isSplash) {
      void refreshAll();
      if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
      }
      document.addEventListener('keydown', handleKeydown);
    }
  });

  onDestroy(() => {
    if (!isSplash) {
      document.removeEventListener('keydown', handleKeydown);
    }
  });
</script>

<svelte:head>
  <title>Asterion AI Workspace</title>
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
      {#if $activeTab === 'chat'}
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
      {/if}
    </main>
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
</style>
