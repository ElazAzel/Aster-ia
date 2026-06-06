<script lang="ts">
  import {
    catalogValidation,
    selectedAgentId,
    selectedAgent,
    localAgents,
    hybridAgents,
    externalAgents
  } from './stores';
  import type { AgentManifest } from './api';

  function agentGroupTitle(agent: AgentManifest) {
    if (agent.privacy_level === 'hybrid') return 'hybrid';
    if (agent.privacy_level === 'external') return 'external';
    return 'local';
  }
</script>

<div class="tab-content">
  <section class="panel" style="flex: 1; overflow: hidden;">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">Библиотека системы</p>
        <h2>Зарегистрированные агенты</h2>
      </div>
      <div class="catalog-state">
        <span class:ok={$catalogValidation?.ok} class:warn={!$catalogValidation?.ok} class="status-dot"></span>
        <strong style="margin-left: 8px;">{$catalogValidation?.agents_count ?? 0} агентов</strong>
        <strong style="margin-left: 8px;">{$catalogValidation?.skills_count ?? 0} навыков</strong>
      </div>
    </div>

    <div class="agent-layout">
      <div class="agent-list" aria-label="Список агентов">
        {#each [...$localAgents, ...$hybridAgents, ...$externalAgents] as agent}
          <button
            type="button"
            class:active={$selectedAgent?.id === agent.id}
            on:click={() => ($selectedAgentId = agent.id)}
          >
            <strong>{agent.name}</strong>
            <small>{agentGroupTitle(agent)} · {agent.skills.length} навыков</small>
          </button>
        {/each}
      </div>

      {#if $selectedAgent}
        <article class="agent-detail">
          <div>
            <p class="eyebrow" style="margin: 0;">ID манифеста: {$selectedAgent.id}</p>
            <h3>{$selectedAgent.name}</h3>
            <p>{$selectedAgent.description}</p>
          </div>
          <dl>
            <div>
              <dt>Приватность</dt>
              <dd>{$selectedAgent.privacy_level}</dd>
            </div>
            <div>
              <dt>Модель по умолчанию</dt>
              <dd>{$selectedAgent.default_model}</dd>
            </div>
            <div>
              <dt>Сеть</dt>
              <dd>{$selectedAgent.permissions.network ? 'Разрешена' : 'Блокирована'}</dd>
            </div>
            <div>
              <dt>Терминал</dt>
              <dd>{$selectedAgent.permissions.shell ? 'Разрешен' : 'Блокирован'}</dd>
            </div>
          </dl>
          <div>
            <dt style="margin-bottom: 8px;">Поддерживаемые навыки</dt>
            <div class="chip-row">
              {#each $selectedAgent.skills as skill}
                <span>{skill}</span>
              {/each}
            </div>
          </div>
          <div>
            <dt style="margin-bottom: 8px;">Критерии приемки задачи</dt>
            <ol>
              {#each $selectedAgent.acceptance_checks as check}
                <li>{check}</li>
              {/each}
            </ol>
          </div>
        </article>
      {/if}
    </div>
  </section>
</div>
