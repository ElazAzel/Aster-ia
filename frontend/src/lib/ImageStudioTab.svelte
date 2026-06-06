<script lang="ts">
  import {
    imagePrompt,
    imageGenerating,
    imageResult,
    runImageGeneration
  } from './stores';
</script>

<div class="tab-content">
  <div class="secondary-grid">
    <section class="panel">
      <div class="panel-heading compact"><h2>Image Studio (ComfyUI)</h2></div>
      <form on:submit|preventDefault={runImageGeneration} class="stack-form">
        <label style="display:flex;flex-direction:column;gap:4px">
          <span style="font-size:11px;font-weight:600;color:var(--text-secondary)">Промпт</span>
          <textarea bind:value={$imagePrompt} rows="4" placeholder="a photorealistic spaceship cockpit, cinematic lighting, ultra-detailed..."></textarea>
        </label>
        <button type="submit" disabled={$imageGenerating || !$imagePrompt.trim()}>
          {$imageGenerating ? '⏳ Генерирую...' : '✨ Сгенерировать'}
        </button>
      </form>
      <div class="plan-box" style="margin-top:0;background:var(--bg-input)">
        <p style="font-size:12px;color:var(--text-secondary)">Требуется локальный <strong style="color:var(--text-primary)">ComfyUI</strong> на порту 8188.</p>
        <p style="font-size:11px;color:var(--text-muted);margin-top:4px">Запустите: <code style="background:var(--bg-card);padding:2px 6px;border-radius:4px;font-family:var(--font-mono)">python main.py --listen 127.0.0.1</code></p>
      </div>
    </section>
    <section class="panel">
      <div class="panel-heading compact"><h2>Результат</h2></div>
      {#if $imageResult}
        <div style="background:var(--bg-input);border-radius:8px;padding:16px;font-family:var(--font-mono);font-size:11px;color:var(--text-secondary);overflow-x:auto">
          {#if $imageResult.images && Array.isArray($imageResult.images) && $imageResult.images.length > 0}
            <img src={$imageResult.images[0]} alt={$imagePrompt} style="max-width:100%;border-radius:6px;margin-bottom:8px" />
          {:else if $imageResult.image}
            <img src={String($imageResult.image)} alt={$imagePrompt} style="max-width:100%;border-radius:6px;margin-bottom:8px" />
          {/if}
          <pre style="margin:0;white-space:pre-wrap">{JSON.stringify($imageResult, null, 2)}</pre>
        </div>
      {:else}
        <p class="empty">Результат генерации появится здесь.</p>
      {/if}
    </section>
  </div>
</div>
