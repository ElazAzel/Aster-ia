<script lang="ts">
  import Sidebar from "./lib/Sidebar.svelte";
  import ChatView from "./lib/ChatView.svelte";
  import ModelSettings from "./lib/ModelSettings.svelte";
  import PrivacyPanel from "./lib/PrivacyPanel.svelte";
  import KnowledgeVault from "./lib/KnowledgeVault.svelte";
  import AgentLab from "./lib/AgentLab.svelte";
  import WorkflowViewer from "./lib/WorkflowViewer.svelte";
  import SystemStatus from "./lib/SystemStatus.svelte";

  type View = "chat" | "models" | "privacy" | "knowledge" | "agents" | "workflows" | "status";

  let currentView: View = "chat";
  let sidebarCollapsed = false;

  function navigate(view: View) {
    currentView = view;
  }
</script>

<div class="app" class:collapsed={sidebarCollapsed}>
  <Sidebar
    {currentView}
    collapsed={sidebarCollapsed}
    on:navigate={(e) => navigate(e.detail)}
    on:toggle-collapse={() => (sidebarCollapsed = !sidebarCollapsed)}
  />

  <main class="content">
    {#if currentView === "chat"}
      <ChatView />
    {:else if currentView === "models"}
      <ModelSettings />
    {:else if currentView === "privacy"}
      <PrivacyPanel />
    {:else if currentView === "knowledge"}
      <KnowledgeVault />
    {:else if currentView === "agents"}
      <AgentLab />
    {:else if currentView === "workflows"}
      <WorkflowViewer />
    {:else if currentView === "status"}
      <SystemStatus />
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

  .app.collapsed {
    grid-template-columns: 60px 1fr;
  }

  .content {
    overflow-y: auto;
    padding: 24px;
  }
</style>
