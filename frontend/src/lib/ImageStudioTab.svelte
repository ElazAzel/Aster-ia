<script lang="ts">
  import { onMount } from 'svelte';
  import {
    imagePrompt,
    imageGenerating,
    imageResult,
    imageRecipes,
    selectedImageRecipeId,
    imageRecipeValidation,
    refreshImageRecipes,
    runImageGeneration,
    validateSelectedImageRecipe
  } from './stores';

  $: selectedRecipe = $imageRecipes.find((recipe) => recipe.id === $selectedImageRecipeId) ?? null;

  onMount(() => {
    void refreshImageRecipes();
  });
</script>

<svelte:head>
  <title>Image Studio - Asterion AI</title>
</svelte:head>

<div class="tab-content">
  <div class="secondary-grid">
    <section class="panel image-panel">
      <div class="panel-heading compact">
        <h2>Image Studio</h2>
        <span class="local-pill">local ComfyUI</span>
      </div>

      <form on:submit|preventDefault={runImageGeneration} class="stack-form">
        <label class="field">
          <span>Рецепт</span>
          <select bind:value={$selectedImageRecipeId} on:change={validateSelectedImageRecipe}>
            {#each $imageRecipes as recipe}
              <option value={recipe.id}>{recipe.title}</option>
            {/each}
          </select>
        </label>

        {#if selectedRecipe}
          <div class="recipe-summary">
            <div>
              <strong>{selectedRecipe.title}</strong>
              <small>{selectedRecipe.estimated_vram_gb} GB VRAM · {selectedRecipe.tags.join(', ')}</small>
            </div>
            <p>{selectedRecipe.description}</p>
            <dl>
              <div><dt>Size</dt><dd>{selectedRecipe.recipe.width}x{selectedRecipe.recipe.height}</dd></div>
              <div><dt>Steps</dt><dd>{selectedRecipe.recipe.steps}</dd></div>
              <div><dt>CFG</dt><dd>{selectedRecipe.recipe.cfg}</dd></div>
            </dl>
          </div>
        {/if}

        <label class="field">
          <span>Промпт</span>
          <textarea
            bind:value={$imagePrompt}
            rows="5"
            placeholder="a clean local-first AI control room, precise interface, realistic lighting"
          ></textarea>
        </label>

        {#if $imageRecipeValidation}
          <div class:ok={$imageRecipeValidation.ok} class:error={!$imageRecipeValidation.ok} class="validation">
            <strong>{$imageRecipeValidation.ok ? 'Recipe OK' : 'Recipe blocked'}</strong>
            <small>{$imageRecipeValidation.nodes_count} nodes · {$imageRecipeValidation.privacy_level}</small>
            {#if $imageRecipeValidation.errors.length}
              <ul>
                {#each $imageRecipeValidation.errors as error}
                  <li>{error}</li>
                {/each}
              </ul>
            {/if}
          </div>
        {/if}

        <button type="submit" disabled={$imageGenerating || !$imagePrompt.trim()}>
          {$imageGenerating ? 'Генерация...' : 'Сгенерировать'}
        </button>
      </form>

      <div class="local-note">
        <span>Endpoint</span>
        <code>127.0.0.1:8188</code>
      </div>
    </section>

    <section class="panel result-panel">
      <div class="panel-heading compact"><h2>Результат</h2></div>
      {#if $imageResult}
        <div class="result-box">
          {#if $imageResult.images && Array.isArray($imageResult.images) && $imageResult.images.length > 0}
            <img src={$imageResult.images[0]} alt={$imagePrompt} />
          {:else if $imageResult.image}
            <img src={String($imageResult.image)} alt={$imagePrompt} />
          {/if}
          <pre>{JSON.stringify($imageResult, null, 2)}</pre>
        </div>
      {:else}
        <p class="empty">Результат генерации появится здесь.</p>
      {/if}
    </section>
  </div>
</div>

<style>
  .image-panel,
  .result-panel {
    min-width: 0;
  }

  .local-pill {
    border: 1px solid var(--border-soft);
    border-radius: 999px;
    color: var(--text-secondary);
    font-size: 11px;
    font-weight: 700;
    padding: 4px 8px;
    white-space: nowrap;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .field span {
    color: var(--text-secondary);
    font-size: 11px;
    font-weight: 700;
  }

  .field select,
  .field textarea {
    background: var(--bg-input);
    border: 1px solid var(--border-soft);
    border-radius: 8px;
    color: var(--text-primary);
    font: inherit;
    min-width: 0;
    padding: 10px 12px;
    resize: vertical;
  }

  .recipe-summary,
  .validation,
  .local-note,
  .result-box {
    background: var(--bg-input);
    border: 1px solid var(--border-soft);
    border-radius: 8px;
  }

  .recipe-summary {
    display: grid;
    gap: 10px;
    padding: 12px;
  }

  .recipe-summary strong,
  .recipe-summary small,
  .recipe-summary p {
    display: block;
    min-width: 0;
    overflow-wrap: anywhere;
  }

  .recipe-summary small,
  .recipe-summary p,
  .validation small {
    color: var(--text-secondary);
    font-size: 12px;
  }

  .recipe-summary p {
    margin: 0;
  }

  .recipe-summary dl {
    display: grid;
    gap: 8px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin: 0;
  }

  .recipe-summary dl div {
    min-width: 0;
  }

  .recipe-summary dt {
    color: var(--text-muted);
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
  }

  .recipe-summary dd {
    color: var(--text-primary);
    font-size: 12px;
    margin: 2px 0 0;
    overflow-wrap: anywhere;
  }

  .validation {
    display: grid;
    gap: 4px;
    padding: 10px 12px;
  }

  .validation.ok {
    border-color: rgba(34, 197, 94, 0.45);
  }

  .validation.error {
    border-color: rgba(239, 68, 68, 0.55);
  }

  .validation ul {
    margin: 4px 0 0;
    padding-left: 18px;
  }

  .validation li {
    overflow-wrap: anywhere;
  }

  .local-note {
    align-items: center;
    color: var(--text-secondary);
    display: flex;
    font-size: 12px;
    gap: 8px;
    justify-content: space-between;
    margin-top: 12px;
    padding: 10px 12px;
  }

  .local-note code {
    background: var(--bg-card);
    border-radius: 6px;
    color: var(--text-primary);
    font-family: var(--font-mono);
    padding: 3px 6px;
  }

  .result-box {
    color: var(--text-secondary);
    font-family: var(--font-mono);
    font-size: 11px;
    overflow-x: auto;
    padding: 16px;
  }

  .result-box img {
    border-radius: 8px;
    display: block;
    margin-bottom: 10px;
    max-width: 100%;
  }

  .result-box pre {
    margin: 0;
    white-space: pre-wrap;
  }
</style>
