<script lang="ts">
  type ChatMessage = {
    role: 'user' | 'assistant';
    content: string;
  };

  export let apiBase = 'http://127.0.0.1:8000';
  export let roomId = 'default';
  export let model: string | null = 'llama3.2';

  let input = '';
  let messages: ChatMessage[] = [];
  let activeSource: EventSource | null = null;
  let streaming = false;
  let errorText = '';

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
      const payload = JSON.parse(event.data);
      if (payload.type === 'error') {
        errorText = payload.error;
        streaming = false;
        activeSource?.close();
        return;
      }
      if (payload.type === 'done') {
        streaming = false;
        activeSource?.close();
        return;
      }
      if (payload.response) {
        const next = [...messages];
        next[next.length - 1] = {
          role: 'assistant',
          content: `${next[next.length - 1].content}${payload.response}`
        };
        messages = next;
      }
    };

    activeSource.onerror = () => {
      errorText = 'Поток ответа прерван';
      streaming = false;
      activeSource?.close();
    };
  }

  function stop() {
    activeSource?.close();
    streaming = false;
  }
</script>

<section class="streaming-chat">
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
    <textarea bind:value={input} placeholder="Введите запрос" rows="3" />
    <div class="actions">
      <button type="submit" disabled={streaming || !input.trim()}>Отправить</button>
      <button type="button" on:click={stop} disabled={!streaming}>Остановить</button>
    </div>
  </form>
</section>

<style>
  .streaming-chat {
    display: grid;
    gap: 12px;
    width: 100%;
  }

  .messages {
    display: grid;
    gap: 8px;
  }

  .message {
    border: 1px solid #d7dce3;
    border-radius: 8px;
    padding: 10px 12px;
    background: #ffffff;
  }

  .message.assistant {
    background: #f7f8fa;
  }

  .message p {
    margin: 4px 0 0;
    white-space: pre-wrap;
  }

  textarea {
    width: 100%;
    resize: vertical;
    border: 1px solid #c9d0da;
    border-radius: 8px;
    padding: 10px 12px;
    font: inherit;
  }

  .actions {
    display: flex;
    gap: 8px;
    margin-top: 8px;
  }

  button {
    border: 0;
    border-radius: 8px;
    padding: 8px 12px;
    background: #111827;
    color: #ffffff;
    font: inherit;
  }

  button:disabled {
    opacity: 0.45;
  }

  .error {
    color: #b42318;
    margin: 0;
  }
</style>
