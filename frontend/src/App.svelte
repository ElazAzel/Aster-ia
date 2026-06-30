<script lang="ts">
  import SideRail from "./lib/SideRail.svelte";
  import { activeTab } from "./lib/stores";
  import CommandCenterTab from "./lib/CommandCenterTab.svelte";
  import StreamingChat from "./lib/StreamingChat.svelte";
  import VoiceTab from "./lib/VoiceTab.svelte";
  import AgentLabTab from "./lib/AgentLabTab.svelte";
  import AutomationTab from "./lib/AutomationTab.svelte";
  import VaultTab from "./lib/VaultTab.svelte";
  import ResearchTab from "./lib/ResearchTab.svelte";
  import DeepResearchTab from "./lib/DeepResearchTab.svelte";
  import ImageStudioTab from "./lib/ImageStudioTab.svelte";
  import ArtifactsTab from "./lib/ArtifactsTab.svelte";
  import SystemTab from "./lib/SystemTab.svelte";
  import PluginsTab from "./lib/PluginsTab.svelte";
  import BenchmarkTab from "./lib/BenchmarkTab.svelte";
  import AnalyticsTab from "./lib/AnalyticsTab.svelte";
</script>

<div class="app">
  <SideRail />

  <main class="content">
    {#if $activeTab === "command_center"}
      <CommandCenterTab />
    {:else if $activeTab === "chat"}
      <StreamingChat />
    {:else if $activeTab === "voice"}
      <VoiceTab />
    {:else if $activeTab === "agents"}
      <AgentLabTab />
    {:else if $activeTab === "automation"}
      <AutomationTab />
    {:else if $activeTab === "vault"}
      <VaultTab />
    {:else if $activeTab === "research"}
      <ResearchTab />
    {:else if $activeTab === "research_deep"}
      <DeepResearchTab />
    {:else if $activeTab === "images"}
      <ImageStudioTab />
    {:else if $activeTab === "artifacts_browser"}
      <ArtifactsTab />
    {:else if $activeTab === "system"}
      <SystemTab />
    {:else if $activeTab === "plugins"}
      <PluginsTab />
    {:else if $activeTab === "benchmark"}
      <BenchmarkTab />
    {:else if $activeTab === "analytics"}
      <AnalyticsTab />
    {/if}
  </main>
</div>

<style>
  :global(*) {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  :global(body) {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen,
      Ubuntu, Cantarell, sans-serif;
    background: #0f1117;
    color: #e1e4e8;
    height: 100vh;
    overflow: hidden;
  }

  .app {
    display: grid;
    grid-template-columns: 240px 1fr;
    height: 100vh;
    transition: grid-template-columns 0.2s ease;
  }

  .content {
    overflow-y: auto;
    padding: 24px;
  }
</style>
