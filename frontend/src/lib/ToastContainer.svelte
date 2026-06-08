<script lang="ts">
  import { toasts } from './stores';
</script>

<div class="toast-container" id="toast-container">
  {#each $toasts as toast (toast.id)}
    <div class="toast {toast.type}" id="toast-{toast.id}">
      <span class="toast-icon">
        {#if toast.type === 'success'}
          ✓
        {:else if toast.type === 'warning'}
          ⚠
        {:else}
          ✕
        {/if}
      </span>
      <span class="toast-message">{toast.message}</span>
    </div>
  {/each}
</div>

<style>
  .toast-container {
    position: fixed;
    top: 24px;
    right: 24px;
    z-index: 10000;
    display: flex;
    flex-direction: column;
    gap: 10px;
    pointer-events: none;
    max-width: 380px;
    width: calc(100% - 48px);
  }

  .toast {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 18px;
    border-radius: 10px;
    font-size: 13.5px;
    font-weight: 500;
    color: var(--text-primary);
    background: var(--bg-glass);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--border-color);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
    pointer-events: auto;
    animation: toastSlideIn 0.35s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  }

  @keyframes toastSlideIn {
    from {
      opacity: 0;
      transform: translateX(100%) translateY(-10px) scale(0.9);
    }
    to {
      opacity: 1;
      transform: translateX(0) translateY(0) scale(1);
    }
  }

  .toast-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    font-size: 11px;
    font-weight: 700;
    color: #ffffff;
    flex-shrink: 0;
  }

  .toast.success {
    border-left: 4px solid var(--color-green);
  }
  .toast.success .toast-icon {
    background: var(--color-green);
  }

  .toast.warning {
    border-left: 4px solid var(--color-yellow);
  }
  .toast.warning .toast-icon {
    background: var(--color-yellow);
    color: #000;
  }

  .toast.error {
    border-left: 4px solid var(--color-red);
  }
  .toast.error .toast-icon {
    background: var(--color-red);
  }

  .toast-message {
    line-height: 1.4;
  }
</style>
