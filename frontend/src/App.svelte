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
    void refreshAll();
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
    document.addEventListener('keydown', handleKeydown);
  });

  onDestroy(() => {
    document.removeEventListener('keydown', handleKeydown);
  });
</script>

<svelte:head>
  <title>Asterion AI Workspace</title>
</svelte:head>

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
