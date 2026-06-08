<script lang="ts">
  import { privacyReport, privacyInput, analyzeCurrentPrivacy, riskLabel } from './stores';
</script>

<div class="panel-heading compact">
  <h2>Радар конфиденциальности</h2>
  <span class={`risk-pill ${$privacyReport?.level ? `risk-${$privacyReport.level}` : ''}`}>
    {riskLabel($privacyReport?.level)}
  </span>
</div>
<div class="toggle-grid">
  <label>
    <span>API модель</span>
    <input
      type="checkbox"
      checked={$privacyInput.model_type === 'api'}
      on:change={(event) => {
        $privacyInput.model_type = event.currentTarget.checked ? 'api' : 'local';
        void analyzeCurrentPrivacy();
      }}
    />
  </label>
  <label>
    <span>Файлы</span>
    <input
      type="checkbox"
      bind:checked={$privacyInput.files_attached}
      on:change={() => void analyzeCurrentPrivacy()}
    />
  </label>
  <label>
    <span>Память</span>
    <input
      type="checkbox"
      bind:checked={$privacyInput.memory_enabled}
      on:change={() => void analyzeCurrentPrivacy()}
    />
  </label>
  <label>
    <span>Веб</span>
    <input
      type="checkbox"
      bind:checked={$privacyInput.web_access}
      on:change={() => void analyzeCurrentPrivacy()}
    />
  </label>
</div>
<ul class="risk-list">
  {#each $privacyReport?.items ?? [] as item}
    <li>
      <span class={`status-dot risk-${item.risk}`}></span>
      <strong>{item.what}</strong>
      <small>{item.destination}</small>
    </li>
  {:else}
    <p class="empty" style="text-align: center; margin-top: 8px;">Нет активных рисков.</p>
  {/each}
</ul>
