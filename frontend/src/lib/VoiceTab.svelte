<script lang="ts">
  import { onMount } from 'svelte';
  import {
    getVoiceStatus,
    structureVoiceText,
    transcribeVoice,
    type VoiceStatus,
    type VoiceTranscriptResponse
  } from './api';
  import { apiBase, runStep, showToast } from './stores';

  let status: VoiceStatus | null = null;
  let selectedFile: File | null = null;
  let transcript: VoiceTranscriptResponse | null = null;
  let mode = 'note';
  let language = '';
  let textDraft = '';
  let recording = false;
  let busy = false;
  let mediaRecorder: MediaRecorder | null = null;
  let chunks: BlobPart[] = [];
  let audioUrl = '';

  $: meeting = transcript?.meeting as Record<string, unknown> | undefined;
  $: summary = listFrom(transcript?.summary ?? meeting?.summary);
  $: actionItems = listFrom(transcript?.action_items ?? meeting?.action_items);
  $: decisions = listFrom(transcript?.decisions ?? meeting?.decisions);
  $: questions = listFrom(transcript?.questions ?? meeting?.questions);

  onMount(() => {
    void refreshStatus();
  });

  function listFrom(value: unknown): string[] {
    if (!Array.isArray(value)) return [];
    return value.map((item) => String(item)).filter(Boolean);
  }

  async function refreshStatus() {
    const result = await runStep('Проверяю Voice Mode', () => getVoiceStatus($apiBase));
    if (result) status = result;
  }

  function handleFile(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    selectedFile = input.files?.[0] ?? null;
    transcript = null;
  }

  async function startRecording() {
    if (!navigator.mediaDevices?.getUserMedia) {
      showToast('Запись с микрофона недоступна в этом окружении', 'warning');
      return;
    }
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    chunks = [];
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = (event: BlobEvent) => {
      if (event.data.size > 0) chunks = [...chunks, event.data];
    };
    mediaRecorder.onstop = () => {
      const blob = new Blob(chunks, { type: 'audio/webm' });
      selectedFile = new File([blob], 'voice-note.webm', { type: 'audio/webm' });
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      audioUrl = URL.createObjectURL(blob);
      stream.getTracks().forEach((track) => track.stop());
      recording = false;
    };
    mediaRecorder.start();
    recording = true;
  }

  function stopRecording() {
    mediaRecorder?.stop();
  }

  async function runTranscription() {
    if (!selectedFile) return;
    busy = true;
    const result = await runStep('Расшифровываю локальное аудио', () =>
      transcribeVoice($apiBase, selectedFile as File, mode, language)
    );
    busy = false;
    if (result) {
      transcript = result;
      if (result.error) {
        showToast(result.error, 'warning', 7000);
      } else {
        showToast('Расшифровка готова', 'success');
      }
    }
  }

  async function structureText() {
    if (!textDraft.trim()) return;
    busy = true;
    const result = await runStep('Структурирую голосовую заметку', () =>
      structureVoiceText($apiBase, textDraft, mode === 'meeting' ? 'meeting' : 'notes')
    );
    busy = false;
    if (result) transcript = result;
  }
</script>

<div class="tab-content">
  <div class="secondary-grid">
    <section class="panel">
      <div class="panel-heading compact">
        <h2>Voice Mode</h2>
        <span class:ok={status?.ok} class:warn={!status?.ok} class="status-dot"></span>
      </div>

      {#if status}
        <div class="voice-status">
          <strong>{status.engine}</strong>
          <span>{status.whisper_available ? 'Локальная транскрибация активна' : 'Fallback без Whisper'}</span>
          <small>{status.note}</small>
        </div>
      {:else}
        <p class="empty">Статус Voice Mode ещё не загружен.</p>
      {/if}

      <div class="split-controls">
        <label style="display:flex;flex-direction:column;gap:4px">
          <span style="font-size:11px;font-weight:600;color:var(--text-secondary)">Режим</span>
          <select bind:value={mode}>
            <option value="note">Заметка</option>
            <option value="meeting">Встреча</option>
          </select>
        </label>
        <label style="display:flex;flex-direction:column;gap:4px">
          <span style="font-size:11px;font-weight:600;color:var(--text-secondary)">Язык</span>
          <input bind:value={language} placeholder="ru, en или авто" />
        </label>
      </div>

      <div class="button-grid">
        <button type="button" on:click={startRecording} disabled={recording || busy}>
          Начать запись
        </button>
        <button type="button" class="secondary" on:click={stopRecording} disabled={!recording}>
          Остановить
        </button>
      </div>

      <label class="voice-file">
        <span>Аудиофайл</span>
        <input type="file" accept=".mp3,.wav,.m4a,.webm,.ogg,.flac,audio/*" on:change={handleFile} />
      </label>

      {#if audioUrl}
        <audio src={audioUrl} controls style="width: 100%;"></audio>
      {/if}

      {#if selectedFile}
        <div class="plan-box" style="margin-top: 0;">
          <strong>{selectedFile.name}</strong>
          <small>{(selectedFile.size / 1024 / 1024).toFixed(2)} MB · local upload</small>
        </div>
      {/if}

      <button type="button" on:click={runTranscription} disabled={!selectedFile || busy}>
        {busy ? 'Обработка...' : 'Расшифровать локально'}
      </button>
    </section>

    <section class="panel">
      <div class="panel-heading compact">
        <h2>Text-to-Notes</h2>
      </div>
      <textarea
        bind:value={textDraft}
        rows="7"
        placeholder="Вставьте расшифровку или заметку для структурирования..."
      ></textarea>
      <button type="button" on:click={structureText} disabled={!textDraft.trim() || busy}>
        Собрать summary / actions / questions
      </button>
    </section>

    <section class="panel" style="grid-column: span 2;">
      <div class="panel-heading compact">
        <h2>Результат</h2>
        {#if transcript}
          <span class="count">{transcript.privacy_level}</span>
        {/if}
      </div>

      {#if transcript}
        {#if transcript.error}
          <div class="plan-box" style="margin-top: 0;">
            <strong>Нужна локальная установка Whisper</strong>
            <small>{transcript.error}</small>
          </div>
        {/if}

        <div class="voice-result-grid">
          <div>
            <span class="voice-label">Summary</span>
            {#each summary as item}
              <p>{item}</p>
            {:else}
              <p class="empty">Summary пока пустой.</p>
            {/each}
          </div>
          <div>
            <span class="voice-label">Actions</span>
            {#each actionItems as item}
              <p>{item}</p>
            {:else}
              <p class="empty">Action items не найдены.</p>
            {/each}
          </div>
          <div>
            <span class="voice-label">Decisions</span>
            {#each decisions as item}
              <p>{item}</p>
            {:else}
              <p class="empty">Решения не найдены.</p>
            {/each}
          </div>
          <div>
            <span class="voice-label">Questions</span>
            {#each questions as item}
              <p>{item}</p>
            {:else}
              <p class="empty">Вопросы не найдены.</p>
            {/each}
          </div>
        </div>

        <div class="transcript-box">
          <span class="voice-label">Transcript</span>
          <p>{transcript.text || transcript.markdown || 'Текст отсутствует.'}</p>
        </div>
      {:else}
        <p class="empty">Запишите аудио, выберите файл или вставьте текст для структурирования.</p>
      {/if}
    </section>
  </div>
</div>

<style>
  .voice-status,
  .voice-file,
  .transcript-box,
  .voice-result-grid > div {
    background: var(--bg-input);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 12px;
  }

  .voice-status,
  .voice-file {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  .voice-status span,
  .voice-status small,
  .voice-file span,
  .voice-result-grid p,
  .transcript-box p {
    color: var(--text-secondary);
    font-size: 12px;
    line-height: 1.45;
    margin: 0;
    overflow-wrap: anywhere;
  }

  .voice-result-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
  }

  .voice-label {
    color: var(--text-muted);
    display: block;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    margin-bottom: 8px;
    text-transform: uppercase;
  }

  .transcript-box {
    margin-top: 12px;
    max-height: 260px;
    overflow-y: auto;
  }

  @media (max-width: 1000px) {
    .voice-result-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 640px) {
    .voice-result-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
