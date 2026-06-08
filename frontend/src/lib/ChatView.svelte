<script lang="ts">
  type ChatMessage = {
    role: "user" | "assistant";
    content: string;
  };

  const API_BASE = "http://127.0.0.1:8000";

  let input = "";
  let messages: ChatMessage[] = [];
  let activeSource: EventSource | null = null;
  let streaming = false;
  let errorText = "";

  function send() {
    const message = input.trim();
    if (!message || streaming) return;

    errorText = "";
    input = "";
    messages = [
      ...messages,
      { role: "user", content: message },
      { role: "assistant", content: "" },
    ];
    streaming = true;

    const params = new URLSearchParams({ message, room_id: "default" });

    activeSource?.close();
    activeSource = new EventSource(`${API_BASE}/api/chat/stream?${params.toString()}`);

    activeSource.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload.type === "error") {
        errorText = payload.error;
        streaming = false;
        activeSource?.close();
        return;
      }
      if (payload.type === "done") {
        streaming = false;
        activeSource?.close();
        return;
      }
      if (payload.response) {
        const next = [...messages];
        next[next.length - 1] = {
          role: "assistant",
          content: `${next[next.length - 1].content}${payload.response}`,
        };
        messages = next;
      }
    };

    activeSource.onerror = () => {
      errorText = "Поток ответа прерван";
      streaming = false;
      activeSource?.close();
    };
  }

  function stop() {
    activeSource?.close();
    streaming = false;
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }
</script>

<div class="chat-view">
  <div class="messages" aria-live="polite">
    {#if messages.length === 0}
      <div class="empty-state">
        <div class="empty-icon">💬</div>
        <h2>Asterion AI</h2>
        <p>Задайте вопрос или начните диалог</p>
      </div>
    {/if}
    {#each messages as message}
      <article class="message" class:assistant={message.role === "assistant"}>
        <div class="message-role">
          {message.role === "user" ? "Вы" : "Asterion"}
        </div>
        <div class="message-content">{message.content}</div>
      </article>
    {/each}
  </div>

  {#if errorText}
    <p class="error">{errorText}</p>
  {/if}

  <form class="input-area" on:submit|preventDefault={send}>
    <textarea
      bind:value={input}
      on:keydown={handleKeydown}
      placeholder="Введите запрос..."
      rows="3"
      disabled={streaming}
    />
    <div class="actions">
      <button type="submit" disabled={streaming || !input.trim()}>Отправить</button>
      <button type="button" class="stop-btn" on:click={stop} disabled={!streaming}>Остановить</button>
    </div>
  </form>
</div>

<style>
  .chat-view {
    display: flex;
    flex-direction: column;
    height: calc(100vh - 48px);
  }

  .messages {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding-bottom: 16px;
  }

  .empty-state {
    margin: auto;
    text-align: center;
    color: #484f58;
  }

  .empty-icon {
    font-size: 48px;
    margin-bottom: 12px;
  }

  .empty-state h2 {
    font-size: 20px;
    color: #8b949e;
    margin-bottom: 4px;
  }

  .empty-state p {
    font-size: 14px;
  }

  .message {
    padding: 12px 16px;
    border-radius: 12px;
    max-width: 80%;
    background: #1c2128;
    border: 1px solid #21262d;
  }

  .message.assistant {
    background: #1f6feb11;
    border-color: #1f6feb33;
    align-self: flex-start;
  }

  .message:not(.assistant) {
    align-self: flex-end;
  }

  .message-role {
    font-size: 12px;
    font-weight: 600;
    color: #58a6ff;
    margin-bottom: 4px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .message-content {
    white-space: pre-wrap;
    line-height: 1.5;
    font-size: 14px;
  }

  .input-area {
    border-top: 1px solid #21262d;
    padding-top: 12px;
  }

  textarea {
    width: 100%;
    resize: none;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px;
    background: #0d1117;
    color: #e1e4e8;
    font: inherit;
    font-size: 14px;
  }

  textarea:focus {
    outline: none;
    border-color: #58a6ff;
  }

  textarea:disabled {
    opacity: 0.6;
  }

  .actions {
    display: flex;
    gap: 8px;
    margin-top: 8px;
  }

  button {
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font: inherit;
    font-size: 14px;
    cursor: pointer;
    transition: background 0.15s;
  }

  button[type="submit"] {
    background: #238636;
    color: #ffffff;
  }

  button[type="submit"]:hover:not(:disabled) {
    background: #2ea043;
  }

  .stop-btn {
    background: #30363d;
    color: #e1e4e8;
  }

  .stop-btn:hover:not(:disabled) {
    background: #484f58;
  }

  button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .error {
    color: #f85149;
    font-size: 13px;
    margin: 4px 0;
  }
</style>
