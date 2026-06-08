<script lang="ts">
  const API_BASE = "http://127.0.0.1:8000";

  type Agent = {
    id: string;
    name: string;
    description: string;
    tools: string[];
    privacy_level: string;
  };

  type Skill = {
    id: string;
    name: string;
    description: string;
    tools: string[];
  };

  let agents: Agent[] = [];
  let skills: Skill[] = [];
  let loading = false;
  let activeTab: "agents" | "skills" = "agents";

  async function loadCatalog() {
    loading = true;
    try {
      const [agentsRes, skillsRes] = await Promise.all([
        fetch(`${API_BASE}/api/agents/catalog/agents`),
        fetch(`${API_BASE}/api/agents/catalog/skills`),
      ]);
      agents = await agentsRes.json();
      skills = await skillsRes.json();
    } catch (e) {
      agents = [];
      skills = [];
    } finally {
      loading = false;
    }
  }

  loadCatalog();
</script>

<div class="agent-lab">
  <h2>Лаборатория агентов</h2>

  <div class="tabs">
    <button class:active={activeTab === "agents"} on:click={() => (activeTab = "agents")}>
      Агенты ({agents.length})
    </button>
    <button class:active={activeTab === "skills"} on:click={() => (activeTab = "skills")}>
      Навыки ({skills.length})
    </button>
  </div>

  {#if loading}
    <p class="loading">Загрузка каталога...</p>
  {:else if activeTab === "agents"}
    <div class="grid">
      {#each agents as agent}
        <div class="card">
          <h3>{agent.name}</h3>
          <p class="desc">{agent.description}</p>
          <div class="meta">
            <span class="badge">{agent.privacy_level}</span>
            {#each agent.tools.slice(0, 3) as tool}
              <span class="tool-tag">{tool}</span>
            {/each}
          </div>
        </div>
      {/each}
    </div>
  {:else}
    <div class="grid">
      {#each skills as skill}
        <div class="card">
          <h3>{skill.name}</h3>
          <p class="desc">{skill.description}</p>
          <div class="meta">
            {#each skill.tools.slice(0, 3) as tool}
              <span class="tool-tag">{tool}</span>
            {/each}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .agent-lab { max-width: 800px; }
  h2 { font-size: 22px; margin-bottom: 16px; }

  .tabs {
    display: flex;
    gap: 4px;
    margin-bottom: 16px;
    border-bottom: 1px solid #21262d;
    padding-bottom: 4px;
  }

  .tabs button {
    background: none;
    border: none;
    color: #8b949e;
    padding: 8px 16px;
    cursor: pointer;
    font: inherit;
    font-size: 14px;
    border-radius: 6px 6px 0 0;
  }

  .tabs button.active {
    color: #58a6ff;
    background: #1f6feb22;
  }

  .tabs button:hover {
    color: #e1e4e8;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 12px;
  }

  .card {
    padding: 16px;
    border: 1px solid #21262d;
    border-radius: 8px;
    background: #161b22;
  }

  .card h3 {
    font-size: 15px;
    margin-bottom: 6px;
    color: #e1e4e8;
  }

  .desc {
    font-size: 13px;
    color: #8b949e;
    line-height: 1.4;
    margin-bottom: 10px;
  }

  .meta {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .badge {
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 12px;
    background: #23863622;
    color: #2ea043;
    font-weight: 600;
  }

  .tool-tag {
    font-size: 11px;
    padding: 2px 6px;
    border-radius: 4px;
    background: #1c2128;
    color: #8b949e;
  }

  .loading { color: #8b949e; }
</style>
