<script lang="ts">
  import {
    catalogValidation,
    selectedAgentId,
    selectedAgent,
    localAgents,
    hybridAgents,
    externalAgents,
    agentTask,
    agentPlan,
    agentRun,
    flightLogs,
    simulatePlan,
    createPlannedAgentRun,
    health,
    ramGb,
    vramGb
  } from './stores';
  import type { AgentManifest } from './api';

  let allowedFolders = ['~/documents'];
  let networkAccess = false;
  let shellAccess = false;

  function agentGroupTitle(agent: AgentManifest) {
    if (agent.privacy_level === 'hybrid') return 'гибридный';
    if (agent.privacy_level === 'external') return 'внешний';
    return 'локальный';
  }

  function handleApproveRun() {
    const permissions = {
      allowed_folders: allowedFolders,
      network: networkAccess,
      shell: shellAccess
    };
    void createPlannedAgentRun(permissions);
  }

  function formatTs(ts: string) {
    try {
      return new Date(ts).toLocaleTimeString('ru', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch {
      return ts;
    }
  }

  function handleReset() {
    agentPlan.set(null);
    agentRun.set(null);
  }

  // Set default settings when selected agent changes
  $: if ($selectedAgent) {
    networkAccess = $selectedAgent.permissions.network;
    shellAccess = $selectedAgent.permissions.shell;
    allowedFolders = [...$selectedAgent.permissions.allowed_folders];
  }
</script>

<div class="tab-content" style="padding: 16px 24px; overflow: hidden; height: 100%;">
  <div class="agent-layout" style="display: grid; grid-template-columns: repeat(12, 1fr); gap: 16px; height: 100%; overflow: hidden; width: 100%;">
    
    <!-- Column 1: Agent Registry & Info (3 Cols) -->
    <div style="grid-column: span 3; display: flex; flex-direction: column; gap: 12px; height: 100%; overflow: hidden;">
      <section class="panel" style="flex: 1; display: flex; flex-direction: column; overflow: hidden; padding: 16px; gap: 12px;">
        <div class="panel-heading" style="border-bottom: 1px solid var(--border-color); padding-bottom: 10px;">
          <div>
            <p class="eyebrow" style="margin: 0; font-size: 10px;">Библиотека</p>
            <h2 style="font-size: 15px; font-weight: 600; margin: 2px 0 0 0;">Реестр Агентов</h2>
          </div>
          <span style="font-size: 11px; font-weight: 600; color: var(--text-secondary);">
            {$catalogValidation?.agents_count ?? 0}
          </span>
        </div>

        <!-- Agent List -->
        <div class="agent-list" style="flex: 1; overflow-y: auto; padding-right: 4px; display: flex; flex-direction: column; gap: 6px;">
          {#each [...$localAgents, ...$hybridAgents, ...$externalAgents] as agent}
            <button
              type="button"
              class:active={$selectedAgent?.id === agent.id}
              style="padding: 10px 12px; border-radius: 6px; text-align: left; width: 100%; display: flex; flex-direction: column; gap: 2px;"
              on:click={() => ($selectedAgentId = agent.id)}
            >
              <strong style="font-size: 13.5px; font-weight: 600;">{agent.name}</strong>
              <small style="font-size: 11px; opacity: 0.8; text-transform: uppercase;">
                {agentGroupTitle(agent)} · {agent.skills.length} навыков
              </small>
            </button>
          {/each}
        </div>

        <!-- Selected Agent Details Info -->
        {#if $selectedAgent}
          <div style="border-top: 1px solid var(--border-color); padding-top: 12px; display: flex; flex-direction: column; gap: 8px; overflow-y: auto; max-height: 220px;" class="terminal-scroll">
            <h3 style="font-size: 13px; font-weight: 600; color: var(--text-primary); margin: 0;">{$selectedAgent.name}</h3>
            <p style="font-size: 12px; color: var(--text-secondary); line-height: 1.4; margin: 0;">{$selectedAgent.description}</p>
            
            <div style="font-size: 11px; display: flex; flex-direction: column; gap: 4px; margin-top: 4px;">
              <div><span style="color: var(--text-muted);">Модель:</span> <span style="font-family: var(--font-mono); color: var(--text-primary);">{$selectedAgent.default_model}</span></div>
              <div><span style="color: var(--text-muted);">Права Сети:</span> <span style="color: {$selectedAgent.permissions.network ? 'var(--color-green)' : 'var(--text-muted)'}">{$selectedAgent.permissions.network ? 'Разрешено' : 'Блокировано'}</span></div>
              <div><span style="color: var(--text-muted);">Терминал:</span> <span style="color: {$selectedAgent.permissions.shell ? 'var(--color-green)' : 'var(--text-muted)'}">{$selectedAgent.permissions.shell ? 'Разрешено' : 'Блокировано'}</span></div>
            </div>
          </div>
        {/if}
      </section>
    </div>

    <!-- Column 2: Task Simulator (5 Cols) -->
    <div style="grid-column: span 5; display: flex; flex-direction: column; height: 100%; overflow: hidden;">
      <section class="flat-panel" style="flex: 1; display: flex; flex-direction: column; overflow: hidden; padding: 20px; border-radius: 12px; height: 100%;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color); padding-bottom: 12px; margin-bottom: 16px;">
          <h2 style="font-family: var(--font-sans); font-size: 18px; font-weight: 600; color: var(--text-primary); display: flex; align-items: center; gap: 8px; margin: 0;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="9" rx="1"></rect><rect x="14" y="3" width="7" height="5" rx="1"></rect><rect x="14" y="12" width="7" height="9" rx="1"></rect><rect x="3" y="16" width="7" height="5" rx="1"></rect></svg>
            Task Simulator
          </h2>
          {#if $agentPlan}
            <button type="button" class="text-button" style="font-family: var(--font-mono); font-size: 11px; text-transform: uppercase;" on:click={handleReset}>Сбросить</button>
          {/if}
        </div>

        {#if !$agentPlan}
          <!-- Input Form for Task Simulation -->
          <div style="display: flex; flex-direction: column; gap: 16px; flex: 1; justify-content: center; max-width: 440px; margin: 0 auto; width: 100%;">
            <div style="text-align: center; margin-bottom: 8px;">
              <p style="font-size: 13.5px; color: var(--text-secondary); line-height: 1.5;">Смоделируйте выполнение задачи агентом. Система построит шаги планирования и оценит требуемые привилегии доступа.</p>
            </div>
            
            <div style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 11px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase;">Описание задачи</span>
              <textarea
                bind:value={$agentTask}
                rows="4"
                placeholder="Например: Проверить локальный репозиторий на файлы авторизации и предложить рефакторинг..."
                style="padding: 12px; font-size: 13.5px; resize: none;"
              ></textarea>
            </div>

            <button
              type="button"
              disabled={!$agentTask.trim()}
              style="width: 100%; min-height: 40px; font-weight: 600;"
              on:click={simulatePlan}
            >
              Сгенерировать AgentPlan
            </button>
          </div>
        {:else}
          <!-- Display Simulated Steps Stepper -->
          <div style="flex: 1; overflow-y: auto; padding-right: 4px; display: flex; flex-direction: column; gap: 16px;" class="terminal-scroll">
            <div style="position: relative; padding-left: 8px; display: flex; flex-direction: column; gap: 16px;">
              <!-- Vertical Line connector -->
              <div style="position: absolute; left: 23px; top: 16px; bottom: 16px; width: 1px; background: var(--border-color); z-index: 0;"></div>

              {#each $agentPlan.steps as step, idx}
                {@const isLast = idx === $agentPlan.steps.length - 1}
                {@const isPending = $agentRun ? $agentRun.status === 'running' && idx >= $flightLogs.length : true}
                {@const isDone = $agentRun ? $agentRun.status === 'completed' || idx < $flightLogs.length : false}
                <div style="position: relative; padding-left: 40px; display: flex; flex-direction: column; gap: 4px;" class="group">
                  <!-- Number Node indicator -->
                  <div style="position: absolute; left: 8px; top: 2px; width: 30px; height: 30px; border-radius: 50%; background: var(--bg-app); border: 1px solid {isDone ? 'var(--color-green)' : isPending && !isLast ? 'var(--border-color)' : 'var(--color-brand)'}; display: flex; align-items: center; justify-content: center; z-index: 10;">
                    <span style="font-family: var(--font-mono); font-size: 12px; font-weight: 600; color: {isDone ? 'var(--color-green)' : isPending && !isLast ? 'var(--text-secondary)' : 'var(--color-brand-hover)'}">{idx + 1}</span>
                  </div>

                  <!-- Step Card -->
                  <div class="bento-card" class:flat-panel-active={!isPending && !isDone} style="padding: 12px; display: flex; flex-direction: column; gap: 6px; background: rgba(31, 31, 35, 0.4);">
                    <div style="display: flex; justify-content: space-between; align-items: start; gap: 8px;">
                      <h4 style="font-family: var(--font-mono); font-size: 13px; font-weight: 500; color: var(--text-primary); margin: 0; line-height: 1.4;">{step}</h4>
                      <span style="font-family: var(--font-mono); font-size: 9px; padding: 2px 6px; border-radius: 3px; border: 1px solid var(--border-color); background: var(--bg-app); color: var(--text-muted); text-transform: uppercase; white-space: nowrap;">
                        {idx === 0 ? 'ФАЙЛЫ' : idx === 1 ? 'ПОИСК' : 'РАБОТА'}
                      </span>
                    </div>

                    <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px;">
                      <span style="color: var(--text-muted); text-transform: uppercase; font-size: 9px; font-weight: 600;">Безопасность: Локально</span>
                      <span style="font-family: var(--font-mono); font-size: 9px; font-weight: 700; color: {isDone ? 'var(--color-green)' : isPending ? 'var(--color-yellow)' : 'var(--color-brand-hover)'}; text-transform: uppercase;">
                        {isDone ? 'ВЫПОЛНЕНО' : isPending ? 'В ОЖИДАНИИ' : 'АКТИВНО'}
                      </span>
                    </div>
                  </div>
                </div>
              {/each}
            </div>

            <!-- Permissions Required Section -->
            <div style="border-top: 1px solid var(--border-color); padding-top: 16px; margin-top: 8px;">
              <h3 style="font-family: var(--font-sans); font-size: 12px; font-weight: 600; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 12px;">Требуемые разрешения</h3>
              
              <div style="background: var(--bg-app); border: 1px solid var(--border-color); border-radius: 6px; overflow: hidden; margin-bottom: 16px;">
                <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 12.5px;">
                  <tbody>
                    <tr style="border-bottom: 1px solid var(--border-color);">
                      <td style="padding: 10px 12px; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
                        Доступ к файловой системе
                      </td>
                      <td style="padding: 10px 12px; text-align: right;">
                        <div class="toggle-switch-container">
                          <input type="checkbox" id="perm-fs" class="toggle-checkbox" checked>
                          <label for="perm-fs" class="toggle-label"></label>
                        </div>
                      </td>
                    </tr>
                    <tr style="border-bottom: 1px solid var(--border-color);">
                      <td style="padding: 10px 12px; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/><circle cx="12" cy="20" r="1"/></svg>
                        Сетевой доступ (Интернет)
                      </td>
                      <td style="padding: 10px 12px; text-align: right;">
                        <div class="toggle-switch-container">
                          <input type="checkbox" id="perm-net" class="toggle-checkbox" bind:checked={networkAccess}>
                          <label for="perm-net" class="toggle-label"></label>
                        </div>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding: 10px 12px; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>
                        Выполнение команд в терминале
                      </td>
                      <td style="padding: 10px 12px; text-align: right;">
                        <div class="toggle-switch-container">
                          <input type="checkbox" id="perm-shell" class="toggle-checkbox" bind:checked={shellAccess}>
                          <label for="perm-shell" class="toggle-label"></label>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- Simulator approval buttons -->
              <div style="display: flex; gap: 12px; justify-content: end;">
                <button type="button" class="secondary" style="min-height: 34px; padding: 0 16px; font-size: 12.5px;" on:click={handleReset}>Отмена</button>
                <button type="button" style="min-height: 34px; padding: 0 16px; font-size: 12.5px;" on:click={handleApproveRun}>Запустить выполнение</button>
              </div>
            </div>
          </div>
        {/if}
      </section>
    </div>

    <!-- Column 3: Flight Recorder Terminal (4 Cols) -->
    <div style="grid-column: span 4; display: flex; flex-direction: column; height: 100%; overflow: hidden;">
      <section class="flat-panel" style="flex: 1; display: flex; flex-direction: column; overflow: hidden; padding: 0; background: #0a0a0e; border: 1px solid var(--border-color); border-radius: 12px; height: 100%;">
        
        <!-- Terminal Header -->
        <div style="padding: 10px 16px; border-bottom: 1px solid var(--border-color); background: #0e0e12; display: flex; justify-content: space-between; align-items: center;">
          <h3 style="font-family: var(--font-mono); font-size: 11px; font-weight: 700; color: var(--color-green); text-transform: uppercase; margin: 0; display: flex; align-items: center; gap: 6px;">
            <span style="width: 6px; height: 6px; border-radius: 50%; background: var(--color-green); display: inline-block;"></span>
            Flight Recorder logs
          </h3>
          <span style="font-family: var(--font-mono); font-size: 10px; color: var(--text-muted);">CONSOLE</span>
        </div>

        <!-- Terminal Logs Scrollable -->
        <div class="terminal-scroll" style="flex: 1; overflow-y: auto; padding: 16px; font-family: var(--font-mono); font-size: 12px; line-height: 1.5; color: var(--color-green); display: flex; flex-direction: column; gap: 8px;">
          {#if $agentRun}
            <div style="color: var(--text-secondary); border-bottom: 1px solid rgba(71, 69, 84, 0.3); padding-bottom: 8px; margin-bottom: 4px;">
              <div>Task: <span style="color: var(--text-primary);">{$agentRun.agent_id}</span></div>
              <div>Status: <span style="color: var(--color-yellow); font-weight: 600; text-transform: uppercase;">{$agentRun.status}</span></div>
            </div>
            
            {#each $flightLogs as log}
              <div style="display: flex; flex-direction: column; gap: 2px;">
                <div style="display: flex; gap: 8px;">
                  <span style="opacity: 0.5;">[{formatTs(log.ts)}]</span>
                  <span style="font-weight: 600;">{log.action.toUpperCase()}</span>
                  <span style="color: var(--text-muted);">({log.tool})</span>
                </div>
                {#if log.input}
                  <div style="padding-left: 16px; opacity: 0.8; color: var(--text-secondary);">in: {log.input}</div>
                {/if}
                {#if log.output}
                  <div style="padding-left: 16px; opacity: 0.9;">out: {log.output}</div>
                {/if}
                {#if log.error}
                  <div style="padding-left: 16px; color: var(--color-red); font-weight: 600;">err: {log.error}</div>
                {/if}
              </div>
            {:else}
              <div style="opacity: 0.5; font-style: italic;">Подключение к потоку логов...</div>
            {/each}
          {:else}
            <div style="opacity: 0.5; font-style: italic; height: 100%; display: flex; align-items: center; justify-content: center; text-align: center; padding: 20px;">
              Настройте симулятор и нажмите «Запустить выполнение» для просмотра логов в реальном времени.
            </div>
          {/if}
        </div>

        <!-- Terminal Footer -->
        <div style="padding: 6px 12px; background: #0e0e12; border-top: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; font-family: var(--font-mono); font-size: 10px; color: var(--text-muted); text-transform: uppercase;">
          <div style="display: flex; align-items: center; gap: 4px;">
            <span style="width: 5px; height: 5px; border-radius: 50%; background: var(--color-green);"></span>
            Nominal
          </div>
          <div>Mem: 42MB / 512MB</div>
        </div>
      </section>
    </div>

  </div>
</div>
