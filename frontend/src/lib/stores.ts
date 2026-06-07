import { writable, get, derived } from 'svelte/store';
import {
  DEFAULT_API_BASE,
  getHealth,
  getModels,
  getAgentCatalog,
  validateAgentCatalog,
  listRooms,
  listMemories,
  listRagDocuments,
  listRagFolderScopes,
  analyzePrivacy,
  selectModel,
  createMemory,
  createRoom,
  deleteMemory,
  searchRag,
  deleteRagDocument,
  createRagFolderScope,
  deleteRagFolderScope,
  exportResearchReport,
  simulateAgentTask,
  createAgentRun,
  listAgentRunLogs,
  generateImage,
  deepResearch,
  streamDeepResearch,
  findContradictions,
  listPlugins,
  runWorkflow,
  confirmWorkflow,
  createWorkflowEventsSocket,
  listArtifacts,
  listImageRecipes,
  validateImageRecipe,
  indexFile,
  indexFileByPath,
  recordAuditLog,
  listAuditLogs,
  exportSystemData,
  importSystemData,
  wipeSystemData,
  listChatConversations,
  updateChatConversation,
  deleteChatConversation,
  reportTelemetry,
  type HealthResponse,
  type ModelInfo,
  type PrivacyReport,
  type ModelSelection,
  type AgentCatalog,
  type CatalogValidation,
  type ContextRoom,
  type MemoryRecord,
  type RagDocumentRecord,
  type RagFolderScopeRecord,
  type RagChunk,
  type DeepResearchResponse,
  type ContradictionMatch,
  type PluginManifest,
  type WorkflowRunResponse,
  type ArtifactRecord,
  type AgentPlan,
  type AgentRun,
  type FlightRecorderEvent,
  type AuditLogRecord,
  type ImageRecipePreset,
  type ImageRecipeValidation
} from './api';
import {
  fastapiHealthCheck,
  startFastapiSidecar,
  shutdownFastapiSidecar,
  type BackendStatus
} from './tauri';

// Core State Writable Stores
export const apiBase = writable(DEFAULT_API_BASE);
export const roomId = writable('default');
export const selectedModel = writable('llama3.2');
export const taskDescription = writable('local coding assistant');
export const vramGb = writable(8);
export const ramGb = writable(32);

export const health = writable<HealthResponse | null>(null);
export const models = writable<ModelInfo[]>([]);
export const privacyReport = writable<PrivacyReport | null>(null);
export const modelSelection = writable<ModelSelection | null>(null);
export const catalog = writable<AgentCatalog | null>(null);
export const catalogValidation = writable<CatalogValidation | null>(null);
export const selectedAgentId = writable('chat-orchestrator');
export const rooms = writable<ContextRoom[]>([]);
export const roomDraft = writable('');
export const memories = writable<MemoryRecord[]>([]);
export const memoryDraft = writable('');
export const ragDocuments = writable<RagDocumentRecord[]>([]);
export const ragFolderScopes = writable<RagFolderScopeRecord[]>([]);
export const ragQuery = writable('');
export const ragResults = writable<RagChunk[]>([]);
export const researchQuery = writable('Сравнить приватность локального и API маршрута');
export const researchSourceTitle = writable('Manual source');
export const researchClaim = writable('Local-first routing reduces external data exposure.');
export const exportedReport = writable<any | null>(null);
export const agentTask = writable('Проверить локальный документ и найти противоречия');
export const agentPlan = writable<AgentPlan | null>(null);
export const agentRun = writable<AgentRun | null>(null);
export const flightLogs = writable<FlightRecorderEvent[]>([]);
export const desktopStatus = writable<BackendStatus | null>(null);
export const desktopAvailable = writable(false);
export const statusText = writable('Ожидание проверки');
export const busy = writable(false);
export const errorText = writable('');

// Image Studio
export const imagePrompt = writable('');
export const imageResult = writable<Record<string, any> | null>(null);
export const imageGenerating = writable(false);
export const imageRecipes = writable<ImageRecipePreset[]>([]);
export const selectedImageRecipeId = writable('sdxl-square');
export const imageRecipeValidation = writable<ImageRecipeValidation | null>(null);

// Deep Research
export const researchDeepQuery = writable('Сравнить приватность локального и облачного AI');
export const deepResearchResult = writable<DeepResearchResponse | null>(null);
export const deepResearchBusy = writable(false);

// Contradiction Finder
export const contradictionClaims = writable('Локальные модели безопаснее\nОблачные модели надёжнее');
export const contradictions = writable<ContradictionMatch[]>([]);

// Plugin Manager
export const plugins = writable<PluginManifest[]>([]);

// Automation Board
export const workflowName = writable('Мой рабочий процесс');
export const workflowSteps = writable('[{"name":"Проверить файлы","type":"action"},{"name":"Согласовать","type":"human_approval"},{"name":"Создать отчёт","type":"action"}]');
export const workflowResult = writable<WorkflowRunResponse | null>(null);
export const workflowPending = writable(false);

// Artifacts browser
export const allArtifacts = writable<ArtifactRecord[]>([]);
export const uploadFile = writable<File | null>(null);
export const uploadBusy = writable(false);
export const uploadResult = writable<any | null>(null);

// Analytics
export const analyticsStats = writable<Record<string, unknown> | null>(null);

// Security & Audit Logs
export type ConsentRequest = {
  title: string;
  description: string;
  privacyLevel: 'local' | 'hybrid' | 'external';
  onApprove: () => void;
  onDeny: () => void;
};
export const auditLogs = writable<AuditLogRecord[]>([]);
export const activeConsentRequest = writable<ConsentRequest | null>(null);

// Theme store & initialization
export const theme = writable<'dark' | 'light'>((typeof localStorage !== 'undefined' ? localStorage.getItem('theme') : 'dark') as 'dark' | 'light' || 'dark');
if (typeof document !== 'undefined') {
  const currentTheme = localStorage.getItem('theme') || 'dark';
  if (currentTheme === 'light') {
    document.documentElement.classList.add('light-theme');
  } else {
    document.documentElement.classList.remove('light-theme');
  }
}

export function toggleTheme() {
  theme.update(t => {
    const next = t === 'dark' ? 'light' : 'dark';
    localStorage.setItem('theme', next);
    if (typeof document !== 'undefined') {
      const html = document.documentElement;
      if (next === 'light') {
        html.classList.add('light-theme');
      } else {
        html.classList.remove('light-theme');
      }
    }
    return next;
  });
}

// Toast store & helper
export type ToastItem = {
  id: string;
  message: string;
  type: 'success' | 'warning' | 'error';
  duration: number;
};
export const toasts = writable<ToastItem[]>([]);

export function showToast(message: string, type: 'success' | 'warning' | 'error' = 'success', duration = 3500) {
  const id = Math.random().toString(36).substring(2, 9);
  toasts.update(t => [...t, { id, message, type, duration }]);
  setTimeout(() => {
    toasts.update(t => t.filter(item => item.id !== id));
  }, duration);
}

// Onboarding store & helper
export const showOnboarding = writable<boolean>(typeof localStorage !== 'undefined' ? localStorage.getItem('asterion_onboarding_completed') !== 'true' : true);

export function completeOnboarding() {
  localStorage.setItem('asterion_onboarding_completed', 'true');
  showOnboarding.set(false);
  showToast('Ознакомление завершено! Добро пожаловать в Asterion AI.', 'success');
}

// System prompt editor
export const systemPrompt = writable(localStorage.getItem('asterion_system_prompt') ?? '');
export const systemPromptSaved = writable(false);

// UI/Navigation States
export const activeTab = writable('command_center');
export const activeVaultTab = writable('memory');
export const privacyPopoverOpen = writable(false);
export const showLeftPanel = writable(true);
export const showRightPanel = writable(true);
export const activeWorkbenchTab = writable<'logs' | 'plan' | 'artifacts'>('plan');
export const showCommandPalette = writable(false);

// Chat conversations stores
export const conversationId = writable<string | null>(null);
export const conversations = writable<any[]>([]);
export const conversationSearchQuery = writable('');

// Telemetry store & reporter
export const telemetryOptIn = writable<boolean>(
  typeof localStorage !== 'undefined' ? localStorage.getItem('asterion_telemetry_opt_in') === 'true' : false
);
if (typeof localStorage !== 'undefined') {
  telemetryOptIn.subscribe(val => {
    localStorage.setItem('asterion_telemetry_opt_in', val ? 'true' : 'false');
  });
}

export async function reportTelemetryEvent(eventType: string, details: Record<string, unknown> = {}) {
  const base = get(apiBase);
  const optIn = get(telemetryOptIn);
  const vram = get(vramGb);
  const ram = get(ramGb);
  const os = typeof navigator !== 'undefined' ? navigator.platform : 'unknown';
  
  try {
    await reportTelemetry(base, {
      opt_in: optIn,
      event_type: eventType,
      details,
      vram_gb: vram,
      ram_gb: ram,
      os_platform: os
    });
  } catch {
    // telemetries are silent
  }
}

// Privacy Input (reactive combination)
export const privacyInput = writable({
  model_type: 'local' as 'local' | 'api',
  files_attached: false,
  memory_enabled: false,
  web_access: false
});

// Sockets and Event Sources
export const workflowSocket = writable<WebSocket | null>(null);
export const agentRunEventSource = writable<EventSource | null>(null);

// Derived States
export const selectedAgent = derived(
  [catalog, selectedAgentId],
  ([$catalog, $selectedAgentId]) => {
    return $catalog?.agents.find((agent) => agent.id === $selectedAgentId) ?? $catalog?.agents[0] ?? null;
  }
);

export const localAgents = derived(catalog, ($catalog) => {
  return $catalog?.agents.filter((agent) => agent.privacy_level === 'local') ?? [];
});

export const hybridAgents = derived(catalog, ($catalog) => {
  return $catalog?.agents.filter((agent) => agent.privacy_level === 'hybrid') ?? [];
});

export const externalAgents = derived(catalog, ($catalog) => {
  return $catalog?.agents.filter((agent) => agent.privacy_level === 'external') ?? [];
});

// Helper for UI labels
export function riskLabel(level: 'green' | 'yellow' | 'red' | undefined) {
  if (level === 'green') return 'Локально (Безопасно)';
  if (level === 'yellow') return 'Внимание (Гибридный)';
  if (level === 'red') return 'Предупреждение (Внешний)';
  return 'Нет данных';
}

export function formatUptime(seconds: number | undefined) {
  if (seconds === undefined) return 'нет данных';
  if (seconds < 60) return `${seconds.toFixed(0)} сек`;
  return `${(seconds / 60).toFixed(1)} мин`;
}

// Global runStep utility
export async function runStep<T>(label: string, action: () => Promise<T>): Promise<T | null> {
  try {
    statusText.set(label);
    errorText.set('');
    return await action();
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    errorText.set(msg);
    showToast(msg, 'error');
    return null;
  }
}

// State Mutators / API Actions
export async function refreshHealth() {
  const base = get(apiBase);
  const result = await runStep('Проверяю sidecar', () => getHealth(base));
  if (result) health.set(result);
}

export async function startDesktopBackend() {
  const result = await runStep('Запускаю FastAPI sidecar через Tauri', () => startFastapiSidecar());
  if (result) {
    desktopStatus.set(result);
    apiBase.set(`http://${result.host}:${result.port}`);
    if (result.health && typeof result.health === 'object') {
      health.set(result.health as HealthResponse);
    }
  }
}

export async function checkDesktopBackend() {
  const result = await runStep('Проверяю sidecar через Tauri IPC', () => fastapiHealthCheck());
  if (result) {
    desktopStatus.set(result);
    apiBase.set(`http://${result.host}:${result.port}`);
    if (result.health && typeof result.health === 'object') {
      health.set(result.health as HealthResponse);
    }
  }
}

export async function stopDesktopBackend() {
  const result = await runStep('Останавливаю FastAPI sidecar', () => shutdownFastapiSidecar());
  if (result) desktopStatus.set(result);
}

export async function refreshModels() {
  const base = get(apiBase);
  const result = await runStep('Читаю модели Ollama', () => getModels(base));
  if (result) {
    models.set(result.models);
    const selModel = get(selectedModel);
    if (!result.models.some((model) => model.name === selModel) && result.models[0]) {
      selectedModel.set(result.models[0].name);
    }
  }
}

export async function refreshCatalog() {
  const base = get(apiBase);
  const [catalogResult, validationResult] = await Promise.all([
    runStep('Загружаю каталог агентов', () => getAgentCatalog(base)),
    runStep('Проверяю каталог', () => validateAgentCatalog(base))
  ]);
  if (catalogResult) catalog.set(catalogResult);
  if (validationResult) catalogValidation.set(validationResult);
}

export async function refreshRooms() {
  const base = get(apiBase);
  const result = await runStep('Читаю Context Rooms', () => listRooms(base));
  if (result) {
    rooms.set(result);
    const curRoomId = get(roomId);
    if (!result.some((room) => room.id === curRoomId) && result[0]) {
      roomId.set(result[0].id);
    }
  }
}

export async function refreshMemories() {
  const base = get(apiBase);
  const rid = get(roomId);
  const result = await runStep('Читаю память комнаты', () => listMemories(base, rid));
  if (result) memories.set(result);
}

export async function refreshRagDocuments() {
  const base = get(apiBase);
  const rid = get(roomId);
  const result = await runStep('Читаю Vault документы', () => listRagDocuments(base, rid));
  if (result) ragDocuments.set(result);
}

export async function refreshRagFolderScopes() {
  const base = get(apiBase);
  const rid = get(roomId);
  const result = await runStep('Читаю разрешенные RAG папки', () => listRagFolderScopes(base, rid));
  if (result) ragFolderScopes.set(result);
}

export async function refreshImageRecipes() {
  const base = get(apiBase);
  const result = await runStep('Load ComfyUI presets', () => listImageRecipes(base));
  if (result) {
    imageRecipes.set(result.recipes);
    const selected = get(selectedImageRecipeId);
    if (!result.recipes.some((recipe) => recipe.id === selected) && result.recipes[0]) {
      selectedImageRecipeId.set(result.recipes[0].id);
    }
  }
}

export async function refreshConversations() {
  const base = get(apiBase);
  const rid = get(roomId);
  const result = await runStep('Читаю историю чатов', () => listChatConversations(base, rid));
  if (result) {
    conversations.set(result);
  }
}

export async function renameConversation(id: string, newTitle: string) {
  const base = get(apiBase);
  const result = await runStep('Переименовываю диалог', () => updateChatConversation(base, id, newTitle));
  if (result) {
    showToast('Диалог переименован', 'success');
    await refreshConversations();
  }
}

export async function removeConversation(id: string) {
  const base = get(apiBase);
  const result = await runStep('Удаляю диалог', () => deleteChatConversation(base, id));
  if (result) {
    showToast('Диалог удален', 'success');
    if (get(conversationId) === id) {
      conversationId.set(null);
    }
    await refreshConversations();
  }
}

export async function analyzeCurrentPrivacy() {
  const base = get(apiBase);
  const input = get(privacyInput);
  const result = await runStep('Считаю Privacy Radar', () => analyzePrivacy(base, input));
  if (result) privacyReport.set(result);
}

export async function routeModel() {
  const base = get(apiBase);
  const desc = get(taskDescription);
  const vram = get(vramGb);
  const ram = get(ramGb);
  const result = await runStep('Выбираю модель', () => selectModel(base, desc, vram, ram));
  if (result) {
    modelSelection.set(result);
    selectedModel.set(result.model);
    privacyInput.update(p => {
      p.model_type = result.mode === 'api' ? 'api' : 'local';
      return p;
    });
    await analyzeCurrentPrivacy();
  }
}

export async function addMemory() {
  const base = get(apiBase);
  const rid = get(roomId);
  const draft = get(memoryDraft);
  const content = draft.trim();
  if (!content) return;
  const result = await runStep('Добавляю память', () => createMemory(base, rid, content));
  if (result) {
    memoryDraft.set('');
    showToast('Память успешно сохранена', 'success');
    await refreshMemories();
    privacyInput.update(p => {
      p.memory_enabled = true;
      return p;
    });
    await analyzeCurrentPrivacy();
  }
}

export async function addRoom() {
  const base = get(apiBase);
  const draft = get(roomDraft);
  const name = draft.trim();
  if (!name) return;
  const result = await runStep('Создаю Context Room', () => createRoom(base, name));
  if (result) {
    roomDraft.set('');
    roomId.set(result.id);
    showToast(`Комната "${name}" создана`, 'success');
    await refreshRooms();
    await refreshMemories();
    await refreshRagDocuments();
  }
}

export async function removeMemory(memoryId: string) {
  const base = get(apiBase);
  const result = await runStep('Удаляю память', () => deleteMemory(base, memoryId));
  if (result) {
    showToast('Память удалена', 'success');
    await refreshMemories();
  }
}

export async function runRagSearch() {
  const base = get(apiBase);
  const rid = get(roomId);
  const q = get(ragQuery);
  const query = q.trim();
  if (!query) return;
  const result = await runStep('Ищу в RAG', () => searchRag(base, rid, query));
  if (result) ragResults.set(result);
}

export async function removeRagDocument(documentId: string) {
  const base = get(apiBase);
  const result = await runStep('Удаляю запись Vault', () => deleteRagDocument(base, documentId));
  if (result) {
    showToast('Документ удален из хранилища RAG', 'success');
    await refreshRagDocuments();
  }
}

export async function removeRagFolderScope(scopeId: string) {
  const base = get(apiBase);
  const result = await runStep('Отзываю доступ к RAG папке', () => deleteRagFolderScope(base, scopeId));
  if (result) {
    showToast('Доступ к RAG папке отозван', 'success');
    await refreshRagFolderScopes();
  }
}

export async function exportResearchArtifact() {
  const base = get(apiBase);
  const rid = get(roomId);
  const q = get(researchQuery);
  const cl = get(researchClaim);
  const title = get(researchSourceTitle);
  const query = q.trim();
  const claim = cl.trim();
  if (!query || !claim) return;
  const result = await runStep('Экспортирую Research Receipt', () =>
    exportResearchReport(base, {
      room_id: rid,
      query,
      title: 'Research Receipt',
      receipts: [
        {
          source_title: title.trim() || 'Manual source',
          claim,
          quote: claim,
          confidence: 'medium'
        }
      ]
    })
  );
  if (result) {
    showToast('Отчет успешно экспортирован в артефакты', 'success');
    exportedReport.set(result);
    activeWorkbenchTab.set('artifacts');
    showRightPanel.set(true);
  }
}

export async function simulatePlan() {
  const base = get(apiBase);
  const t = get(agentTask);
  const task = t.trim();
  if (!task) return;
  const result = await runStep('Генерирую AgentPlan', () => simulateAgentTask(base, task));
  if (result) {
    agentPlan.set(result);
    activeWorkbenchTab.set('plan');
    showRightPanel.set(true);
  }
}

export function startAgentRunEvents(runId: string) {
  const base = get(apiBase);
  let es = get(agentRunEventSource);
  es?.close();
  es = new EventSource(`${base}/api/agents/runs/${runId}/events`);
  es.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.id && data.action) {
        const eventRow = data as FlightRecorderEvent;
        flightLogs.update(logs => [...logs.filter(l => l.id !== eventRow.id), eventRow]);
      }
    } catch { /* ignore */ }
  };
  agentRunEventSource.set(es);
}

export async function refreshAuditLogs() {
  const base = get(apiBase);
  const result = await runStep('Читаю журнал аудита', () => listAuditLogs(base));
  if (result) auditLogs.set(result);
}

export function requestUserConsent(
  title: string,
  description: string,
  privacyLevel: 'local' | 'hybrid' | 'external',
  onApprove: () => void,
  onDeny?: () => void,
) {
  activeConsentRequest.set({
    title,
    description,
    privacyLevel,
    onApprove: async () => {
      activeConsentRequest.set(null);
      const base = get(apiBase);
      await recordAuditLog(base, 'approve', title, description);
      await refreshAuditLogs();
      onApprove();
    },
    onDeny: async () => {
      activeConsentRequest.set(null);
      const base = get(apiBase);
      await recordAuditLog(base, 'deny', title, description);
      await refreshAuditLogs();
      if (onDeny) onDeny();
    }
  });
}

export async function createPlannedAgentRun(permissions?: { allowed_folders: string[]; network: boolean; shell: boolean }) {
  const base = get(apiBase);
  const rid = get(roomId);
  const t = get(agentTask);
  const task = t.trim();
  if (!task) return;
  const agent = get(selectedAgent);
  const plan = get(agentPlan);
  const perms = permissions || { allowed_folders: [], network: false, shell: false };
  
  const run = async () => {
    const result = await runStep('Создаю AgentRun', () =>
      createAgentRun(base, {
        agent_id: agent?.id ?? get(selectedAgentId),
        room_id: rid,
        task,
        plan: plan,
        permissions: perms
      })
    );
    if (result) {
      agentRun.set(result);
      activeWorkbenchTab.set('logs');
      showRightPanel.set(true);
      startAgentRunEvents(result.id);
      const logs = await runStep('Читаю Flight Recorder', () => listAgentRunLogs(base, result.id));
      if (logs) flightLogs.set(logs);
      void reportTelemetryEvent('agent_run_started', { agent_id: agent?.id ?? get(selectedAgentId) });
    }
  };

  if (perms.network || perms.shell || (perms.allowed_folders && perms.allowed_folders.length > 0)) {
    requestUserConsent(
      `Запуск Агента с повышенными привилегиями`,
      `Агент запрашивает доступ: ${perms.network ? 'Сеть ' : ''}${perms.shell ? 'Терминал ' : ''}${perms.allowed_folders.length > 0 ? 'Папки: ' + perms.allowed_folders.join(', ') : ''}`,
      perms.shell ? 'external' : 'hybrid',
      run
    );
  } else {
    await run();
  }
}

export async function validateSelectedImageRecipe() {
  const base = get(apiBase);
  const pr = get(imagePrompt);
  const presetId = get(selectedImageRecipeId);
  const result = await runStep('Validate ComfyUI recipe', () =>
    validateImageRecipe(base, {
      prompt: pr.trim() || '{{prompt}}',
      preset_id: presetId || undefined
    })
  );
  if (result) imageRecipeValidation.set(result);
  return result;
}

export async function runImageGeneration() {
  const base = get(apiBase);
  const pr = get(imagePrompt);
  const presetId = get(selectedImageRecipeId);
  if (!pr.trim()) return;
  imageGenerating.set(true);
  imageResult.set(null);
  void reportTelemetryEvent('image_generation_started');
  const validation = await validateSelectedImageRecipe();
  if (validation && !validation.ok) {
    imageResult.set({ error: 'ComfyUI recipe validation failed', validation });
    imageGenerating.set(false);
    return;
  }
  const result = await runStep('Генерирую изображение через ComfyUI', () =>
    generateImage(base, { prompt: pr, preset_id: presetId || undefined })
  );
  if (result) imageResult.set(result);
  imageGenerating.set(false);
}

export async function runDeepResearch() {
  const base = get(apiBase);
  const dq = get(researchDeepQuery);
  if (!dq.trim()) return;
  
  const run = async () => {
    deepResearchBusy.set(true);
    deepResearchResult.set(null);
    void reportTelemetryEvent('deep_research_started');
    const result = await runStep('Запускаю Deep Research', () =>
      deepResearch(base, { query: dq, max_subtasks: 5, web_access: true })
    );
    if (result) deepResearchResult.set(result);
    deepResearchBusy.set(false);
  };

  requestUserConsent(
    `Deep Research: ${dq}`,
    `Данная операция требует веб-доступа и сбора информации из внешних источников через SearXNG.`,
    'hybrid',
    run
  );
}

export async function runDeepResearchStreaming() {
  const base = get(apiBase);
  const dq = get(researchDeepQuery);
  if (!dq.trim()) return;

  const run = async () => {
    deepResearchBusy.set(true);
    deepResearchResult.set(null);
    const accumResults = [] as DeepResearchResponse['results'];
    void reportTelemetryEvent('deep_research_streaming_started');
    try {
      const gen = streamDeepResearch(base, { query: dq, max_subtasks: 5, web_access: true });
      while (true) {
        const { value, done } = await gen.next();
        if (done) break;
        if (value.type === 'subtask_start') {
          statusText.set(`Исследую: ${value.subtask}`);
        } else if (value.type === 'result_found') {
          accumResults.push(value.result);
        } else if (value.type === 'done') {
          deepResearchResult.set(value.response);
        }
      }
    } catch (error) {
      errorText.set(error instanceof Error ? error.message : String(error));
    }
    deepResearchBusy.set(false);
  };

  requestUserConsent(
    `Deep Research (Поток): ${dq}`,
    `Данная операция требует веб-доступа и сбора информации из внешних источников через SearXNG.`,
    'hybrid',
    run
  );
}

export async function runContradictionFinder() {
  const base = get(apiBase);
  const cc = get(contradictionClaims);
  const claims = cc.split('\n').map(s => s.trim()).filter(Boolean);
  if (claims.length < 2) return;
  void reportTelemetryEvent('contradiction_finder_started');
  const result = await runStep('Ищу противоречия', () =>
    findContradictions(base, claims, 0.75)
  );
  if (result) contradictions.set(result);
}

export async function refreshPlugins() {
  const base = get(apiBase);
  const result = await runStep('Читаю плагины', () => listPlugins(base));
  if (result) plugins.set(result);
}

export async function startWorkflow() {
  const base = get(apiBase);
  const name = get(workflowName);
  const stepsStr = get(workflowSteps);
  let steps;
  try { steps = JSON.parse(stepsStr); } catch { errorText.set('Неверный JSON шагов'); return; }

  const run = async () => {
    workflowResult.set(null);
    workflowPending.set(false);

    let socket = get(workflowSocket);
    if (!socket || socket.readyState > 1) {
      socket = createWorkflowEventsSocket(base);
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'approval_required') workflowPending.set(true);
      };
      workflowSocket.set(socket);
    }

    const result = await runStep('Запускаю workflow', () =>
      runWorkflow(base, { workflow: { name, steps } })
    );
    if (result) { workflowResult.set(result); workflowPending.set(false); }
  };

  requestUserConsent(
    `Запуск автоматизации: ${name}`,
    `Запуск автоматического рабочего процесса.`,
    'local',
    run
  );
}

export async function approveWorkflow(approved: boolean) {
  const base = get(apiBase);
  const res = get(workflowResult);
  if (!res?.run_id) return;
  const result = await runStep(approved ? 'Подтверждаю шаг' : 'Отклоняю шаг', () =>
    confirmWorkflow(base, res.run_id, approved)
  );
  if (result) workflowPending.set(false);
}

export async function refreshArtifacts() {
  const base = get(apiBase);
  const rid = get(roomId);
  const result = await runStep('Читаю артефакты', () => listArtifacts(base, rid));
  if (result) allArtifacts.set(result);
}

export async function uploadVaultFile() {
  const base = get(apiBase);
  const rid = get(roomId);
  const file = get(uploadFile);
  if (!file) return;
  uploadBusy.set(true);
  uploadResult.set(null);
  const result = await runStep('Индексирую файл в Vault', () =>
    indexFile(base, file, rid)
  );
  if (result) { uploadResult.set(result); await refreshRagDocuments(); }
  uploadBusy.set(false);
}

export const localFilePath = writable('');

function parentDirectory(path: string): string {
  const slash = Math.max(path.lastIndexOf('/'), path.lastIndexOf('\\'));
  if (slash < 0) return path;
  if (/^[A-Za-z]:[\\/]/.test(path) && slash <= 2) return path.slice(0, 3);
  if (slash === 0) return '/';
  return path.slice(0, slash);
}

export async function indexLocalVaultFile() {
  const base = get(apiBase);
  const rid = get(roomId);
  const path = get(localFilePath);
  if (!path) return;
  const folder = parentDirectory(path);
  const run = async () => {
    uploadBusy.set(true);
    uploadResult.set(null);
    const scope = await runStep('Разрешаю RAG папку', () =>
      createRagFolderScope(base, {
        room_id: rid,
        path: folder,
        label: 'Desktop file picker',
        recursive: true
      })
    );
    if (!scope) {
      uploadBusy.set(false);
      return;
    }
    await refreshRagFolderScopes();
    const result = await runStep('Индексирую локальный файл', () =>
      indexFileByPath(base, path, rid)
    );
    if (result) {
      localFilePath.set('');
      uploadResult.set(result);
      await refreshRagDocuments();
    }
    uploadBusy.set(false);
  };
  requestUserConsent(
    'RAG folder scope',
    `Asterion AI получит доступ к папке для локального индексирования: ${folder}`,
    'local',
    run
  );
}

export async function fetchAnalyticsStats() {
  const base = get(apiBase);
  const result = await runStep('Загружаю статистику', async () => {
    const response = await fetch(`${base}/api/analytics/research/stats`);
    if (!response.ok) throw new Error(await response.text());
    return response.json() as Promise<Record<string, unknown>>;
  });
  if (result) analyticsStats.set(result);
}

export async function refreshAll() {
  busy.set(true);
  await Promise.allSettled([
    refreshHealth(),
    refreshModels(),
    refreshCatalog(),
    refreshRooms(),
    refreshMemories(),
    refreshRagDocuments(),
    refreshRagFolderScopes(),
    refreshImageRecipes(),
    refreshConversations(),
    analyzeCurrentPrivacy(),
    refreshPlugins(),
    refreshArtifacts(),
    refreshAuditLogs()
  ]);
  statusText.set('Готово');
  busy.set(false);
}

export function saveSystemPrompt(promptVal: string) {
  localStorage.setItem('asterion_system_prompt', promptVal);
  systemPrompt.set(promptVal);
  systemPromptSaved.set(true);
  setTimeout(() => systemPromptSaved.set(false), 2000);
}

export function clearError() {
  errorText.set('');
}
