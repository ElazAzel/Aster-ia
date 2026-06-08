<script lang="ts">
  import { createEventDispatcher } from "svelte";

  type View = "chat" | "models" | "privacy" | "knowledge" | "agents" | "workflows" | "status";

  export let currentView: View;
  export let collapsed = false;

  const dispatch = createEventDispatcher<{ navigate: View; "toggle-collapse": void }>();

  const navItems: { id: View; label: string; icon: string }[] = [
    { id: "chat", label: "Чат", icon: "💬" },
    { id: "models", label: "Модели", icon: "🧠" },
    { id: "privacy", label: "Приватность", icon: "🔒" },
    { id: "knowledge", label: "Знания", icon: "📚" },
    { id: "agents", label: "Агенты", icon: "🤖" },
    { id: "workflows", label: "Рабочие процессы", icon: "⚡" },
    { id: "status", label: "Система", icon: "📊" },
  ];
</script>

<nav class="sidebar" class:collapsed>
  <header class="sidebar-header">
    {#if !collapsed}
      <h1 class="logo">Asterion</h1>
    {/if}
    <button class="collapse-btn" on:click={() => dispatch("toggle-collapse")} title={collapsed ? "Развернуть" : "Свернуть"}>
      {collapsed ? "»" : "«"}
    </button>
  </header>

  <ul class="nav-list">
    {#each navItems as item}
      <li>
        <button
          class="nav-item"
          class:active={currentView === item.id}
          on:click={() => dispatch("navigate", item.id)}
          title={collapsed ? item.label : undefined}
        >
          <span class="icon">{item.icon}</span>
          {#if !collapsed}
            <span class="label">{item.label}</span>
          {/if}
        </button>
      </li>
    {/each}
  </ul>
</nav>

<style>
  .sidebar {
    background: #161b22;
    border-right: 1px solid #21262d;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    transition: width 0.2s ease;
  }

  .sidebar-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px;
    border-bottom: 1px solid #21262d;
    min-height: 56px;
  }

  .logo {
    font-size: 18px;
    font-weight: 700;
    color: #58a6ff;
    white-space: nowrap;
  }

  .collapse-btn {
    background: none;
    border: 1px solid #30363d;
    color: #8b949e;
    border-radius: 6px;
    padding: 4px 8px;
    cursor: pointer;
    font-size: 12px;
  }

  .collapse-btn:hover {
    color: #e1e4e8;
    border-color: #58a6ff;
  }

  .nav-list {
    list-style: none;
    padding: 8px;
    flex: 1;
    overflow-y: auto;
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 10px 12px;
    border: none;
    border-radius: 8px;
    background: transparent;
    color: #8b949e;
    font-size: 14px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
    text-align: left;
    white-space: nowrap;
  }

  .nav-item:hover {
    background: #1c2128;
    color: #e1e4e8;
  }

  .nav-item.active {
    background: #1f6feb22;
    color: #58a6ff;
  }

  .icon {
    font-size: 18px;
    min-width: 24px;
    text-align: center;
  }

  .label {
    overflow: hidden;
    text-overflow: ellipsis;
  }
</style>
