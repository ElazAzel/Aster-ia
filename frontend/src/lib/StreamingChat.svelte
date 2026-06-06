<script lang="ts">
  import { onDestroy } from 'svelte';

  type ChatMessage = {
    role: 'user' | 'assistant';
    content: string;
  };

  export let apiBase = 'http://127.0.0.1:8000';
  export let roomId = 'default';
  export let model: string | null = 'llama3.2';

  let input = '';
  let messages: ChatMessage[] = [
    {
      role: 'assistant',
      content: 'Готов к локальному диалогу. Ответы приходят через SSE поток.'
    }
  ];
  let activeSource: EventSource | null = null;
  let streaming = false;
  let errorText = '';

  function appendAssistantToken(token: string) {
    const next = [...messages];
    const last = next[next.length - 1];
    if (!last || last.role !== 'assistant') {
      next.push({ role: 'assistant', content: token });
    } else {
      next[next.length - 1] = {
        role: 'assistant',
        content: `${last.content}${token}`
      };
    }
    messages = next;
  }

  function send() {
    const message = input.trim();
    if (!message || streaming) return;

    errorText = '';
    input = '';
    messages = [...messages, { role: 'user', content: message }, { role: 'assistant', content: '' }];
    streaming = true;

    const params = new URLSearchParams({
      message,
      room_id: roomId
    });
    if (model) params.set('model', model);

    activeSource?.close();
    activeSource = new EventSource(`${apiBase}/api/chat/stream?${params.toString()}`);

    activeSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as {
          type?: string;
          error?: string;
          response?: string;
          done?: boolean;
        };

        if (payload.type === 'error') {
          errorText = payload.error ?? 'Поток ответа завершился с ошибкой.';
          streaming = false;
          activeSource?.close();
          return;
        }

        if (payload.type === 'done' || payload.done) {
          streaming = false;
          activeSource?.close();
          return;
        }

        if (payload.response) appendAssistantToken(payload.response);
      } catch {
        errorText = 'Не удалось прочитать SSE событие.';
        streaming = false;
        activeSource?.close();
      }
    };

    activeSource.onerror = () => {
      errorText = 'Поток ответа прерван. Проверьте FastAPI sidecar и Ollama.';
      streaming = false;
      activeSource?.close();
    };
  }

  function stop() {
    activeSource?.close();
    streaming = false;
  }

  onDestroy(() => {
    activeSource?.close();
  });
</script>

<section class="streaming-chat" aria-label="Streaming chat">
  <div class="messages" aria-live="polite">
    {#each messages as message}
      <article class:assistant={message.role === 'assistant'} class="message">
        <strong>{message.role === 'user' ? 'Вы' : 'Asterion'}</strong>
        <p>{message.content}</p>
      </article>
    {/each}
  </div>

  {#if errorText}
    <p class="error">{errorText}</p>
  {/if}

  <form on:submit|preventDefault={send}>
    <textarea bind:value={input} placeholder="Введите запрос" rows="3"></textarea>
    <div class="actions">
      <button type="submit" disabled={streaming || !input.trim()}>
        {streaming ? 'Идет ответ' : 'Отправить'}
      </button>
      <button type="button" class="secondary" on:click={stop} disabled={!streaming}>Остановить</button>
    </div>
  </form>
</section>
