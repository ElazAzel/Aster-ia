<script lang="ts">
  import { onMount, onDestroy, tick } from 'svelte';
  import { listChatConversations, listChatMessages } from './api';
  import MarkdownRenderer from './MarkdownRenderer.svelte';
  import { conversationId, conversations, refreshConversations } from './stores';

  type ChatMessage = {
    role: 'user' | 'assistant';
    content: string;
  };

  type AutocompleteItem = {
    label: string;
    value: string;
    description: string;
    icon: string;
  };

  type ContextRoom = {
    id: string;
    name: string;
    color?: string;
    allowed_models?: string[];
    memory_policy?: string;
    retention_days?: number;
    created_at?: string;
    updated_at?: string;
  };

  export let apiBase = 'http://127.0.0.1:8000';
  export let roomId = 'default';
  export let model: string | null = 'llama3.2';
  export let rooms: ContextRoom[] = [];
  export let modelNames: string[] = [];

  const COMMANDS: AutocompleteItem[] = [
    { label: 'simulate', value: '/simulate ', description: 'Симулировать задачу агента', icon: '⚡' },
    { label: 'search', value: '/search ', description: 'Поиск по RAG базе знаний', icon: '🔍' },
    { label: 'privacy', value: '/privacy ', description: 'Переключить параметры приватности', icon: '🛡️' },
    { label: 'clear', value: '/clear', description: 'Очистить историю диалога', icon: '🗑️' }
  ];

  let input = '';
  let messages: ChatMessage[] = [
    {
      role: 'assistant',
      content: 'Привет! Я Asterion. Готов к локальному диалогу. Ответы приходят через SSE поток в реальном времени. Чем я могу помочь?'
    }
  ];
  let activeSource: EventSource | null = null;
  let streaming = false;
  let errorText = '';
  let loadingHistory = false;
  let messagesEl: HTMLDivElement;
  let textareaEl: HTMLTextAreaElement;

  let loadedConversationId: string | null = null;

  $: if ($conversationId) {
    void loadMessages($conversationId);
  } else {
    messages = [
      {
        role: 'assistant',
        content: 'Привет! Я Asterion. Готов к локальному диалогу. Ответы приходят через SSE поток в реальном времени. Чем я могу помочь?'
      }
    ];
    loadedConversationId = null;
  }

  $: if (roomId) {
    newChat();
    void loadHistory();
  }

  // Autocomplete state
  let autocompleteType: '/' | '@' | null = null;
  let autocompleteQuery = '';
  let autocompleteItems: AutocompleteItem[] = [];
  let autocompleteIndex = 0;
  let autocompleteVisible = false;

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
    scrollToBottom();
  }

  async function scrollToBottom() {
    await tick();
    if (messagesEl) {
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }
  }

  function adjustHeight() {
    if (!textareaEl) return;
    textareaEl.style.height = 'auto';
    textareaEl.style.height = `${Math.min(textareaEl.scrollHeight, 200)}px`;
  }

  async function loadHistory() {
    await refreshConversations();
    if ($conversations.length > 0 && !$conversationId) {
      $conversationId = $conversations[0].id;
    }
  }

  async function loadMessages(convId: string) {
    if (convId === loadedConversationId) return;
    loadingHistory = true;
    try {
      const records = await listChatMessages(apiBase, convId);
      messages = records.map(r => ({ role: r.role === 'user' ? 'user' as const : 'assistant' as const, content: r.content }));
      if (messages.length === 0) {
        messages = [{ role: 'assistant', content: 'Привет! Я Asterion. Готов к локальному диалогу.' }];
      }
      loadedConversationId = convId;
    } catch {
      messages = [{ role: 'assistant', content: 'Привет! Я Asterion. Готов к локальному диалогу.' }];
    }
    loadingHistory = false;
    scrollToBottom();
  }

  function newChat() {
    messages = [{ role: 'assistant', content: 'Привет! Я Asterion. Готов к локальному диалогу.' }];
    $conversationId = null;
    loadedConversationId = null;
    errorText = '';
    activeSource?.close();
    streaming = false;
  }

  function updateAutocomplete() {
    const cursorPos = textareaEl.selectionStart;
    const beforeCursor = input.slice(0, cursorPos);
    const lastSpace = Math.max(beforeCursor.lastIndexOf(' '), beforeCursor.lastIndexOf('\n'));
    const wordStart = lastSpace + 1;
    const currentWord = beforeCursor.slice(wordStart);

    if (currentWord.startsWith('/')) {
      autocompleteType = '/';
      autocompleteQuery = currentWord.slice(1);
      autocompleteItems = COMMANDS.filter(cmd =>
        cmd.label.toLowerCase().startsWith(autocompleteQuery.toLowerCase())
      );
      autocompleteVisible = autocompleteItems.length > 0;
    } else if (currentWord.startsWith('@')) {
      autocompleteType = '@';
      autocompleteQuery = currentWord.slice(1);

      const roomItems: AutocompleteItem[] = rooms.map(r => ({
        label: r.name,
        value: `@${r.name} `,
        description: 'Комната контекста',
        icon: '🏠'
      }));

      const modelItems: AutocompleteItem[] = modelNames.map(m => ({
        label: m,
        value: `@${m} `,
        description: 'Модель',
        icon: '🤖'
      }));

      autocompleteItems = [...roomItems, { label: '---', value: '', description: '', icon: '' }, ...modelItems]
        .filter(item =>
          !item.label.startsWith('---') &&
          item.label.toLowerCase().startsWith(autocompleteQuery.toLowerCase())
        );
      autocompleteVisible = autocompleteItems.length > 0;
    } else {
      autocompleteVisible = false;
      autocompleteType = null;
    }

    autocompleteIndex = 0;
  }

  function applyAutocomplete() {
    if (!autocompleteVisible || autocompleteItems.length === 0) return;

    const selected = autocompleteItems[autocompleteIndex];
    if (!selected.value) return;

    const cursorPos = textareaEl.selectionStart;
    const beforeCursor = input.slice(0, cursorPos);
    const lastSpace = Math.max(beforeCursor.lastIndexOf(' '), beforeCursor.lastIndexOf('\n'));
    const wordStart = lastSpace + 1;

    const newInput = input.slice(0, wordStart) + selected.value + input.slice(cursorPos);
    input = newInput;
    autocompleteVisible = false;
    autocompleteType = null;

    tick().then(() => {
      adjustHeight();
      if (textareaEl) {
        const newPos = wordStart + selected.value.length;
        textareaEl.selectionStart = newPos;
        textareaEl.selectionEnd = newPos;
        textareaEl.focus();
      }
    });
  }

  function handleInput() {
    adjustHeight();
    updateAutocomplete();
  }

  function handleKeydown(event: KeyboardEvent) {
    if (autocompleteVisible) {
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        autocompleteIndex = (autocompleteIndex + 1) % autocompleteItems.length;
        return;
      }
      if (event.key === 'ArrowUp') {
        event.preventDefault();
        autocompleteIndex = (autocompleteIndex - 1 + autocompleteItems.length) % autocompleteItems.length;
        return;
      }
      if (event.key === 'Enter' || event.key === 'Tab') {
        event.preventDefault();
        applyAutocomplete();
        return;
      }
      if (event.key === 'Escape') {
        autocompleteVisible = false;
        autocompleteType = null;
        event.preventDefault();
        return;
      }
    }

    if (event.key === 'Enter' && !event.shiftKey && !autocompleteVisible) {
      event.preventDefault();
      send();
    }
  }

  function send() {
    const message = input.trim();
    if (!message || streaming) return;

    if (message === '/clear') {
      newChat();
      return;
    }

    errorText = '';
    input = '';
    autocompleteVisible = false;
    if (textareaEl) {
      textareaEl.style.height = 'auto';
    }
    messages = [...messages, { role: 'user', content: message }, { role: 'assistant', content: '' }];
    streaming = true;
    scrollToBottom();

    const params = new URLSearchParams({
      message,
      room_id: roomId
    });
    if (model) params.set('model', model);
    if ($conversationId) params.set('conversation_id', $conversationId);

    activeSource?.close();
    activeSource = new EventSource(`${apiBase}/api/chat/stream?${params.toString()}`);

    activeSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as {
          type?: string;
          error?: string;
          response?: string;
          done?: boolean;
          conversation_id?: string;
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
          if (payload.conversation_id) {
            $conversationId = payload.conversation_id;
            loadedConversationId = payload.conversation_id;
          }
          void refreshConversations();
          return;
        }

        if (payload.response) {
          appendAssistantToken(payload.response);
        }
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

  function parseAssistantMessage(content: string) {
    const codeBlocks: Array<{ lang: string; filename: string; code: string }> = [];
    const parts = content.split(/(```[\s\S]*?```)/g);
    let summaryText = '';
    
    for (const part of parts) {
      if (part.startsWith('```')) {
        const match = part.match(/```(\w*)(?:\(([^)]+)\))?\n([\s\S]*?)```/);
        if (match) {
          codeBlocks.push({
            lang: match[1] || 'txt',
            filename: match[2] || '',
            code: match[3] || ''
          });
        } else {
          const lines = part.split('\n');
          const lang = lines[0].replace('```', '').trim();
          const code = lines.slice(1, -1).join('\n');
          codeBlocks.push({
            lang: lang || 'txt',
            filename: '',
            code: code
          });
        }
      } else {
        summaryText += part;
      }
    }

    const sources: Array<{ name: string; info: string; icon: string }> = [];
    const seenSources = new Set<string>();
    const fileRegex = /`([\w\-]+\.(?:log|py|json|yml|yaml|csv|md|txt|html|js|ts|sh|rs|toml))`|(\b[\w\-]+\.(?:log|py|json|yml|yaml|csv|md|txt|html|js|ts|sh|rs|toml))\b/gi;
    let fileMatch;
    while ((fileMatch = fileRegex.exec(content)) !== null) {
      const name = fileMatch[1] || fileMatch[2];
      if (name && !seenSources.has(name.toLowerCase())) {
        seenSources.add(name.toLowerCase());
        let info = 'Локальный файл';
        let icon = 'description';
        if (name.endsWith('.log')) {
          info = 'Лог-файл анализирован';
          icon = 'receipt_long';
        } else if (name.endsWith('.db') || name.includes('sql')) {
          info = 'База данных';
          icon = 'database';
        } else if (name.includes('config') || name.endsWith('.yml') || name.endsWith('.yaml') || name.endsWith('.toml')) {
          info = 'Настройки конфигурации';
          icon = 'settings';
        }
        sources.push({ name, info, icon });
      }
    }

    const urlRegex = /(https?:\/\/[^\s\)]+)/gi;
    let urlMatch;
    while ((urlMatch = urlRegex.exec(content)) !== null) {
      const url = urlMatch[1];
      try {
        const hostname = new URL(url).hostname;
        if (!seenSources.has(url.toLowerCase())) {
          seenSources.add(url.toLowerCase());
          sources.push({ name: hostname, info: 'Внешний веб-ресурс', icon: 'language' });
        }
      } catch {}
    }

    return {
      summary: summaryText.trim(),
      sources,
      codeBlocks
    };
  }

  onMount(() => {
    loadHistory();
  });

  onDestroy(() => {
    activeSource?.close();
  });
</script>

<div class="chat-container">
  <div class="chat-messages" bind:this={messagesEl}>
    {#each messages as message}
      <div class="chat-bubble-row {message.role}">
        <div class="chat-avatar">
          {message.role === 'user' ? 'Вы' : 'AI'}
        </div>
        <div class="chat-bubble">
          <div class="bubble-meta">
            {message.role === 'user' ? 'Пользователь' : 'Asterion'}
          </div>
          {#if message.role === 'assistant'}
            {@const parsed = parseAssistantMessage(message.content)}
            <div class="split-response">
              <!-- SUMMARY Block -->
              {#if parsed.summary || (streaming && message === messages[messages.length - 1] && !parsed.summary)}
                <div class="summary-block">
                  <div class="block-header">
                    <div class="block-header-left">
                      <span class="material-symbols-outlined" style="font-size: 16px;">short_text</span>
                      <span>АННОТАЦИЯ (SUMMARY)</span>
                    </div>
                    <div class="block-header-privacy local">
                      <span class="status-dot-mini"></span>
                      <span>ЛОКАЛЬНО</span>
                    </div>
                  </div>
                  <div class="summary-block-text">
                    <MarkdownRenderer text={parsed.summary || 'Обработка запроса...'} />
                    {#if streaming && message === messages[messages.length - 1] && !parsed.summary}
                      <div class="streaming-indicator" style="margin-top: 8px;">
                        <span class="streaming-dot"></span>
                        <span class="streaming-dot"></span>
                        <span class="streaming-dot"></span>
                      </div>
                    {/if}
                  </div>
                </div>
              {/if}

              <!-- SOURCE Block -->
              {#if parsed.sources.length > 0}
                <div class="source-block">
                  <div class="block-header">
                    <div class="block-header-left">
                      <span class="material-symbols-outlined" style="font-size: 16px;">source</span>
                      <span>ИСТОЧНИКИ (SOURCE)</span>
                    </div>
                    <div class="block-header-privacy local">
                      <span class="status-dot-mini"></span>
                      <span>ЛОКАЛЬНО</span>
                    </div>
                  </div>
                  <div class="sources-grid">
                    {#each parsed.sources as src}
                      <div class="source-card">
                        <span class="material-symbols-outlined source-card-icon">{src.icon}</span>
                        <div>
                          <div class="source-card-name">{src.name}</div>
                          <div class="source-card-info">{src.info}</div>
                        </div>
                      </div>
                    {/each}
                  </div>
                </div>
              {/if}

              <!-- CODE Block(s) -->
              {#each parsed.codeBlocks as block}
                <div class="code-block-wrapper">
                  <div class="block-header">
                    <div class="block-header-left">
                      <span class="material-symbols-outlined" style="font-size: 16px;">code</span>
                      <span class="code-block-filename">КОД {block.filename ? `(${block.filename})` : ''}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 12px;">
                      <div class="block-header-privacy local">
                        <span class="status-dot-mini"></span>
                        <span>ЛОКАЛЬНО</span>
                      </div>
                      <button type="button" class="copy-code-btn" on:click={() => {
                        if (navigator.clipboard) {
                          navigator.clipboard.writeText(block.code);
                          alert('Код скопирован в буфер обмена');
                        }
                      }}>
                        <span class="material-symbols-outlined" style="font-size: 14px;">content_copy</span>
                        <span>Копировать</span>
                      </button>
                    </div>
                  </div>
                  <div class="code-block-container">
                    <MarkdownRenderer text={"```" + block.lang + "\n" + block.code + "\n```"} />
                  </div>
                </div>
              {/each}
            </div>
          {:else}
            <div class="bubble-content">
              <MarkdownRenderer text={message.content} />
            </div>
          {/if}
        </div>
      </div>
    {/each}

    {#if errorText}
      <div class="chat-error-alert">
        <span class="status-dot warn"></span>
        <p>{errorText}</p>
      </div>
    {/if}

    {#if loadingHistory}
      <div style="text-align:center;padding:20px;color:var(--text-muted);font-size:13px">Загрузка истории...</div>
    {/if}
  </div>

  <div class="chat-input-wrapper">
    <form on:submit|preventDefault={send} class="chat-composer">
      <div class="composer-autocomplete-area">
        <!-- Autocomplete Popover -->
        <div class="autocomplete-popover" class:visible={autocompleteVisible}>
          {#if autocompleteType === '/'}
            <div class="autocomplete-group-label">Команды</div>
            {#each autocompleteItems as item, i}
              <button
                type="button"
                class="autocomplete-item"
                class:active={i === autocompleteIndex}
                on:mousedown={(e) => { e.preventDefault(); autocompleteIndex = i; applyAutocomplete(); }}
              >
                <span class="ac-icon">{item.icon}</span>
                <div class="ac-content">
                  <span class="ac-label">/{item.label}</span>
                  <span class="ac-desc">{item.description}</span>
                </div>
                <span class="ac-shortcut">{i === 0 ? '↵' : ''}</span>
              </button>
            {/each}

          {:else if autocompleteType === '@'}
            <div class="autocomplete-group-label">Комнаты и Модели</div>
            {#each autocompleteItems as item, i}
              <button
                type="button"
                class="autocomplete-item"
                class:active={i === autocompleteIndex}
                on:mousedown={(e) => { e.preventDefault(); autocompleteIndex = i; applyAutocomplete(); }}
              >
                <span class="ac-icon">{item.icon}</span>
                <div class="ac-content">
                  <span class="ac-label">{item.label}</span>
                  <span class="ac-desc">{item.description}</span>
                </div>
                <span class="ac-shortcut">{i === 0 ? '↵' : ''}</span>
              </button>
            {/each}
          {/if}
        </div>

        <textarea
          bind:this={textareaEl}
          bind:value={input}
          on:input={handleInput}
          on:keydown={handleKeydown}
          placeholder="Спросите Asterion или введите запрос... (/ для команд, @ для контекста)"
          rows="1"
        ></textarea>
      </div>

      <div class="composer-actions">
        <div class="composer-status-pills">
          <span class="status-pill-local">Ollama</span>
          {#if model}
            <span class="status-pill-model">{model}</span>
          {/if}
          <span class="status-pill-model">{roomId}</span>
        </div>

        <div class="composer-buttons">
          {#if streaming}
            <button type="button" class="stop-btn" on:click={stop}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="4" y="4" width="16" height="16" rx="2"/></svg>
              <span>Остановить</span>
            </button>
          {:else}
            <button type="submit" class="send-btn" disabled={!input.trim()}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
              <span>Отправить</span>
            </button>
          {/if}
        </div>
      </div>
    </form>
  </div>
</div>

<style>
  .chat-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    width: 100%;
    position: relative;
    overflow: hidden;
  }

  .chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 24px 32px 140px;
    display: flex;
    flex-direction: column;
    gap: 24px;
    scroll-behavior: smooth;
  }

  .chat-bubble-row {
    display: flex;
    gap: 16px;
    width: 100%;
    max-width: 800px;
    margin: 0 auto;
  }

  .chat-avatar {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
    flex-shrink: 0;
    margin-top: 2px;
  }

  .chat-bubble-row.user .chat-avatar {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    color: var(--text-secondary);
  }

  .chat-bubble-row.assistant .chat-avatar {
    background: linear-gradient(135deg, var(--color-brand) 0%, #a89eff 100%);
    color: #ffffff;
    box-shadow: 0 4px 10px rgba(124, 109, 250, 0.25);
  }

  .chat-bubble {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .bubble-meta {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .bubble-content {
    background: var(--bg-glass);
    border: 1px solid var(--border-color);
    padding: 16px 20px;
    border-radius: 12px;
    font-size: 14.5px;
    line-height: 1.6;
    color: var(--text-primary);
    box-shadow: var(--shadow-premium);
    backdrop-filter: blur(12px);
  }

  .chat-bubble-row.user .bubble-content {
    background: rgba(255, 255, 255, 0.02);
    border-color: rgba(255, 255, 255, 0.05);
  }

  .chat-error-alert {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 18px;
    background: var(--color-red-glow);
    border: 1px solid var(--color-red-border);
    border-radius: 8px;
    max-width: 800px;
    width: 100%;
    margin: 0 auto;
    color: var(--color-red-text);
    font-size: 13.5px;
  }

  .chat-input-wrapper {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    background: linear-gradient(to top, var(--bg-app) 70%, transparent 100%);
    padding: 24px 32px;
    z-index: 10;
  }

  .chat-composer {
    background: var(--bg-sidebar);
    border: 1px solid var(--border-color);
    border-radius: 14px;
    padding: 8px 12px;
    max-width: 800px;
    margin: 0 auto;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
    display: flex;
    flex-direction: column;
    transition: var(--transition-smooth);
  }

  .chat-composer:focus-within {
    border-color: var(--color-brand);
    box-shadow: 0 0 0 3px rgba(124, 109, 250, 0.15), 0 10px 40px rgba(0, 0, 0, 0.5);
  }

  .chat-composer textarea {
    background: transparent;
    border: none;
    resize: none;
    padding: 10px 8px;
    font-size: 14.5px;
    line-height: 1.5;
    color: var(--text-primary);
    width: 100%;
    outline: none;
    max-height: 200px;
  }

  .chat-composer textarea::placeholder {
    color: var(--text-muted);
  }

  .composer-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid var(--border-color);
    padding-top: 8px;
    margin-top: 4px;
  }

  .composer-status-pills {
    display: flex;
    gap: 6px;
  }

  .status-pill-local {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    background: var(--color-green-glow);
    border: 1px solid var(--color-green-border);
    color: var(--color-green-text);
    padding: 3px 8px;
    border-radius: 5px;
  }

  .status-pill-model {
    font-size: 10px;
    font-weight: 600;
    background: var(--bg-input);
    border: 1px solid var(--border-color);
    color: var(--text-secondary);
    padding: 3px 8px;
    border-radius: 5px;
  }

  .composer-buttons {
    display: flex;
    gap: 8px;
  }

  .composer-buttons button {
    min-height: 32px;
    padding: 0 14px;
    font-size: 12px;
    border-radius: 6px;
    gap: 6px;
  }

  .send-btn {
    background: var(--color-brand);
    color: #ffffff;
  }

  .stop-btn {
    background: var(--color-red-glow);
    border: 1px solid var(--color-red-border);
    color: var(--color-red-text);
  }

  .stop-btn:hover {
    background: rgba(239, 68, 68, 0.25) !important;
  }
</style>
