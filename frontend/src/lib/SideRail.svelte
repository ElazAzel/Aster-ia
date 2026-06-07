<script lang="ts">
  import { activeTab, health, formatUptime, refreshArtifacts, refreshPlugins } from './stores';
</script>

<aside class="side-rail" aria-label="Навигация Asterion">
  <div class="brand">
    <span class="brand-mark">A</span>
    <div>
      <strong>Asterion AI</strong>
      <small>Локальный AI Воркспейс</small>
    </div>
  </div>

  <nav>
    <button class:active={$activeTab === 'command_center'} on:click={() => $activeTab = 'command_center'}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>
      <span>Command Center</span>
    </button>
    <button class:active={$activeTab === 'chat'} on:click={() => $activeTab = 'chat'}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
      <span>Умный Чат</span>
    </button>
    <button class:active={$activeTab === 'agents'} on:click={() => $activeTab = 'agents'}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
      <span>Агенты и Навыки</span>
    </button>
    <button class:active={$activeTab === 'voice'} on:click={() => $activeTab = 'voice'}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/><path d="M19 10v1a7 7 0 0 1-14 0v-1"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="8" y1="22" x2="16" y2="22"/></svg>
      <span>Voice Mode</span>
    </button>
    <button class:active={$activeTab === 'vault'} on:click={() => $activeTab = 'vault'}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"></path><path d="M2 17l10 5 10-5"></path><path d="M2 12l10 5 10-5"></path></svg>
      <span>База Знаний (Vault)</span>
    </button>
    <button class:active={$activeTab === 'research'} on:click={() => $activeTab = 'research'}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 3a3 3 0 0 0-3 3v12a3 3 0 0 0 3 3 3 3 0 0 0 3-3V6a3 3 0 0 0-3-3z"></path><path d="M9 3a3 3 0 0 0-3 3v12a3 3 0 0 0 3 3 3 3 0 0 0 3-3V6a3 3 0 0 0-3-3z"></path><path d="M9 18H3a3 3 0 0 0-3 3 3 3 0 0 0 3-3V6a3 3 0 0 0 3 3h3"></path></svg>
      <span>Исследования</span>
    </button>
    <button class:active={$activeTab === 'system'} on:click={() => $activeTab = 'system'}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
      <span>Система</span>
    </button>
    <button class:active={$activeTab === 'research_deep'} on:click={() => $activeTab = 'research_deep'}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/><path d="M11 8v6"/><path d="M8 11h6"/></svg>
      <span>Deep Research</span>
    </button>
    <button class:active={$activeTab === 'images'} on:click={() => $activeTab = 'images'}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/></svg>
      <span>Image Studio</span>
    </button>
    <button class:active={$activeTab === 'automation'} on:click={() => $activeTab = 'automation'}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
      <span>Automation</span>
    </button>
    <button class:active={$activeTab === 'artifacts_browser'} on:click={() => { $activeTab = 'artifacts_browser'; void refreshArtifacts(); }}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
      <span>Артефакты</span>
    </button>
    <button class:active={$activeTab === 'plugins'} on:click={() => { $activeTab = 'plugins'; void refreshPlugins(); }}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z"/><line x1="16" y1="8" x2="2" y2="22"/><line x1="17.5" y1="15" x2="9" y2="15"/></svg>
      <span>Плагины</span>
    </button>
    <button class:active={$activeTab === 'benchmark'} on:click={() => $activeTab = 'benchmark'} aria-label="Benchmark">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
      <span>Benchmark</span>
    </button>
    <button class:active={$activeTab === 'analytics'} on:click={() => $activeTab = 'analytics'} aria-label="Аналитика">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
      <span>Аналитика</span>
    </button>
  </nav>

  <div class="system-meter">
    <span class:ok={$health?.status === 'ok'} class:warn={$health?.status !== 'ok'} class="status-dot"></span>
    <div>
      <strong>Sidecar: {$health?.status ?? 'offline'}</strong>
      <small>аптайм {formatUptime($health?.uptime_seconds)}</small>
    </div>
  </div>
</aside>
