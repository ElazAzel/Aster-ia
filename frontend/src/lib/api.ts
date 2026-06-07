export const DEFAULT_API_BASE =
  import.meta.env.VITE_ASTERION_API_BASE?.replace(/\/$/, '') ?? 'http://127.0.0.1:8000';

export type PrivacyLevel = 'local' | 'hybrid' | 'external';
export type RiskLevel = 'green' | 'yellow' | 'red';

export type HealthResponse = {
  status: 'ok' | 'degraded';
  app: string;
  uptime_seconds: number;
  database: Record<string, unknown>;
  privacy: Record<string, unknown>;
};

export type ModelInfo = {
  name: string;
  modified_at?: string | null;
  size?: number | null;
  digest?: string | null;
};

export type ModelsResponse = {
  models: ModelInfo[];
  privacy_level: 'local';
};

export type VoiceStatus = {
  ok: boolean;
  privacy_level: 'local';
  engine: string;
  whisper_available: boolean;
  model_name: string;
  device: string;
  supported_formats: string[];
  note: string;
};

export type VoiceTranscriptResponse = {
  text: string;
  segments: Array<{ start: number; end: number; text: string }>;
  language?: string | null;
  duration?: number | null;
  diarization?: string | null;
  privacy_level: 'local';
  engine: string;
  error?: string | null;
  meeting?: Record<string, unknown>;
  summary?: string[];
  action_items?: string[];
  decisions?: string[];
  questions?: string[];
  markdown?: string;
};

export type PrivacyReport = {
  level: RiskLevel;
  items: Array<{
    what: string;
    destination: string;
    risk: RiskLevel;
  }>;
};

export type ModelSelection = {
  model: string;
  mode: 'local' | 'api';
  reason: string;
};

export type AgentManifest = {
  id: string;
  name: string;
  version: string;
  role: string;
  description: string;
  privacy_level: PrivacyLevel;
  default_model: string;
  triggers: string[];
  skills: string[];
  permissions: {
    allowed_folders: string[];
    network: boolean;
    shell: boolean;
  };
  lifecycle: string[];
  outputs: string[];
  handoff_targets: string[];
  acceptance_checks: string[];
  system_prompt: string;
  escalation_policy: string;
};

export type SkillManifest = {
  id: string;
  name: string;
  version: string;
  owner: string;
  category: string;
  description: string;
  privacy_level: PrivacyLevel;
  triggers: string[];
  inputs: string[];
  outputs: string[];
  tools: string[];
  guardrails: string[];
  requires_consent: string[];
  failure_modes: string[];
  acceptance_checks: string[];
};

export type AgentCatalog = {
  agents: AgentManifest[];
  skills: SkillManifest[];
};

export type CatalogValidation = {
  ok: boolean;
  agents_count: number;
  skills_count: number;
  errors: string[];
  warnings: string[];
};

export type MemoryRecord = {
  id: string;
  room_id: string;
  content: string;
  source: string;
  created_at: string;
  expires_at?: string | null;
  privacy?: PrivacyReport | null;
};

export type ContextRoom = {
  id: string;
  name: string;
  color: string;
  allowed_models: string[];
  memory_policy: 'off' | 'session' | 'persistent';
  retention_days: number;
  created_at: string;
  updated_at: string;
};

export type AgentPlan = {
  steps: string[];
  required_permissions: string[];
  estimated_tokens: number;
};

export type RagChunk = {
  id: string;
  room_id: string;
  content: string;
  source: string;
  score: number;
};

export type RagDocumentRecord = {
  id: string;
  room_id: string;
  source: string;
  indexed_chunks: number;
  created_at: string;
};

export type RagFolderScopeRecord = {
  id: string;
  room_id: string;
  path: string;
  label?: string | null;
  recursive: boolean;
  created_at: string;
};

export type ArtifactBlock = {
  type: 'text' | 'code' | 'table' | 'source' | 'action';
  title?: string | null;
  content?: string | null;
  language?: string | null;
  rows?: Array<Record<string, unknown>>;
  source?: string | null;
  action?: string | null;
  metadata?: Record<string, unknown>;
};

export type ArtifactRecord = {
  id: string;
  room_id: string;
  kind: string;
  title: string;
  blocks: ArtifactBlock[];
  source: string;
  created_at: string;
};

export type ChatConversationRecord = {
  id: string;
  room_id: string;
  created_at: string;
  message_count: number;
  latest_ts?: string | null;
};

export type ChatMessageRecord = {
  id: string;
  conv_id: string;
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  model?: string | null;
  artifact_id?: string | null;
  ts: string;
};

export type ResearchReceipt = {
  source_title: string;
  url?: string | null;
  quote?: string | null;
  claim: string;
  confidence: 'high' | 'medium' | 'low';
  ts?: string;
};

export type ResearchReportExportResponse = {
  artifact: ArtifactRecord;
  receipts_count: number;
};

export type AgentRun = {
  id: string;
  agent_id: string;
  room_id: string;
  status: 'planned' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';
  plan: AgentPlan;
  permissions: {
    allowed_folders: string[];
    network: boolean;
    shell: boolean;
  };
  created_at: string;
  updated_at: string;
};

export type FlightRecorderEvent = {
  id: string;
  run_id: string;
  ts: string;
  action: string;
  tool: string;
  privacy_level: PrivacyLevel;
  input?: string | null;
  output?: string | null;
  model?: string | null;
  error?: string | null;
};

type RequestOptions = {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
};

async function request<T>(apiBase: string, path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    method: options.method ?? 'GET',
    headers: options.body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: options.body === undefined ? undefined : JSON.stringify(options.body)
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) detail = payload.detail;
    } catch {
      detail = await response.text();
    }
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

export function getHealth(apiBase: string) {
  return request<HealthResponse>(apiBase, '/api/health');
}

export function getModels(apiBase: string) {
  return request<ModelsResponse>(apiBase, '/api/models');
}

export function getVoiceStatus(apiBase: string) {
  return request<VoiceStatus>(apiBase, '/api/voice/status');
}

export async function transcribeVoice(
  apiBase: string,
  file: File,
  mode = 'note',
  language = '',
  diarize = false
) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('mode', mode);
  formData.append('diarize', diarize ? 'true' : 'false');
  if (language.trim()) formData.append('language', language.trim());

  const response = await fetch(`${apiBase}/api/voice/transcribe`, {
    method: 'POST',
    body: formData
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<VoiceTranscriptResponse>;
}

export async function structureVoiceText(apiBase: string, text: string, mode = 'notes') {
  const formData = new FormData();
  formData.append('text', text);
  formData.append('mode', mode);
  const response = await fetch(`${apiBase}/api/voice/transcribe/text`, {
    method: 'POST',
    body: formData
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<VoiceTranscriptResponse>;
}

export async function* pullModel(
  apiBase: string,
  model: string
): AsyncGenerator<Record<string, unknown>, void> {
  const response = await fetch(`${apiBase}/api/models/pull`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model })
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `${response.status} ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) return;
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const raw = line.slice(6).trim();
      if (!raw) continue;
      yield JSON.parse(raw) as Record<string, unknown>;
    }
  }
}

export function listChatConversations(apiBase: string, roomId?: string) {
  const query = roomId ? `?room_id=${encodeURIComponent(roomId)}` : '';
  return request<ChatConversationRecord[]>(apiBase, `/api/chat/conversations${query}`);
}

export function listChatMessages(apiBase: string, conversationId: string) {
  return request<ChatMessageRecord[]>(
    apiBase,
    `/api/chat/conversations/${encodeURIComponent(conversationId)}/messages`
  );
}

export function selectModel(apiBase: string, taskDescription: string, vramGb: number, ramGb: number) {
  return request<ModelSelection>(apiBase, '/api/models/select', {
    method: 'POST',
    body: {
      task_description: taskDescription,
      hw_profile: {
        vram_gb: vramGb,
        ram_gb: ramGb,
        gpu_name: 'manual'
      }
    }
  });
}

export function analyzePrivacy(
  apiBase: string,
  payload: {
    model_type: 'local' | 'api';
    files_attached: boolean;
    memory_enabled: boolean;
    web_access: boolean;
  }
) {
  return request<PrivacyReport>(apiBase, '/api/privacy/analyze', {
    method: 'POST',
    body: payload
  });
}

export function getAgentCatalog(apiBase: string) {
  return request<AgentCatalog>(apiBase, '/api/agents/catalog');
}

export function validateAgentCatalog(apiBase: string) {
  return request<CatalogValidation>(apiBase, '/api/agents/catalog/validate');
}

export function simulateAgentTask(apiBase: string, task: string) {
  return request<AgentPlan>(apiBase, '/api/agents/simulate', {
    method: 'POST',
    body: { task }
  });
}

export function listMemories(apiBase: string, roomId: string) {
  return request<MemoryRecord[]>(apiBase, `/api/memory/${encodeURIComponent(roomId)}`);
}

export function listRooms(apiBase: string) {
  return request<ContextRoom[]>(apiBase, '/api/rooms');
}

export function createRoom(apiBase: string, name: string, color = '#2f80ed') {
  return request<ContextRoom>(apiBase, '/api/rooms', {
    method: 'POST',
    body: {
      name,
      color,
      allowed_models: [],
      memory_policy: 'session',
      retention_days: 30
    }
  });
}

export function createMemory(apiBase: string, roomId: string, content: string, source = 'manual') {
  return request<MemoryRecord>(apiBase, '/api/memory', {
    method: 'POST',
    body: {
      room_id: roomId,
      content,
      source,
      expires_at: null,
      privacy: {
        model_type: 'local',
        files_attached: false,
        memory_enabled: true,
        web_access: false
      }
    }
  });
}

export function deleteMemory(apiBase: string, memoryId: string) {
  return request<{ deleted: boolean }>(apiBase, `/api/memory/${encodeURIComponent(memoryId)}`, {
    method: 'DELETE'
  });
}

export function searchRag(apiBase: string, roomId: string, query: string, limit = 5) {
  return request<RagChunk[]>(apiBase, '/api/rag/search', {
    method: 'POST',
    body: {
      room_id: roomId,
      query,
      limit
    }
  });
}

export function listRagDocuments(apiBase: string, roomId?: string) {
  const query = roomId ? `?room_id=${encodeURIComponent(roomId)}` : '';
  return request<RagDocumentRecord[]>(apiBase, `/api/rag/documents${query}`);
}

export function deleteRagDocument(apiBase: string, documentId: string) {
  return request<{ deleted: boolean }>(
    apiBase,
    `/api/rag/documents/${encodeURIComponent(documentId)}`,
    {
      method: 'DELETE'
    }
  );
}

export function listRagFolderScopes(apiBase: string, roomId?: string) {
  const query = roomId ? `?room_id=${encodeURIComponent(roomId)}` : '';
  return request<RagFolderScopeRecord[]>(apiBase, `/api/rag/folder-scopes${query}`);
}

export function createRagFolderScope(
  apiBase: string,
  payload: {
    room_id: string;
    path: string;
    label?: string | null;
    recursive?: boolean;
  },
) {
  return request<RagFolderScopeRecord>(apiBase, '/api/rag/folder-scopes', {
    method: 'POST',
    body: {
      ...payload,
      recursive: payload.recursive ?? true,
    },
  });
}

export function deleteRagFolderScope(apiBase: string, scopeId: string) {
  return request<{ deleted: boolean }>(
    apiBase,
    `/api/rag/folder-scopes/${encodeURIComponent(scopeId)}`,
    {
      method: 'DELETE'
    }
  );
}

export function createArtifact(
  apiBase: string,
  payload: {
    room_id: string;
    kind: 'chat' | 'research_report' | 'code' | 'table' | 'image' | 'workflow';
    title: string;
    blocks: ArtifactBlock[];
    source?: string;
  }
) {
  return request<ArtifactRecord>(apiBase, '/api/artifacts', {
    method: 'POST',
    body: {
      ...payload,
      source: payload.source ?? 'ui'
    }
  });
}

export function exportResearchReport(
  apiBase: string,
  payload: {
    room_id: string;
    query: string;
    title: string;
    receipts: ResearchReceipt[];
  }
) {
  return request<ResearchReportExportResponse>(apiBase, '/api/research/report/export', {
    method: 'POST',
    body: payload
  });
}

export function createAgentRun(
  apiBase: string,
  payload: {
    agent_id: string;
    room_id: string;
    task: string;
    plan?: AgentPlan | null;
    permissions?: { allowed_folders: string[]; network: boolean; shell: boolean };
  }
) {
  return request<AgentRun>(apiBase, '/api/agents/runs', {
    method: 'POST',
    body: {
      ...payload,
      permissions: payload.permissions ?? {
        allowed_folders: [],
        network: false,
        shell: false
      }
    }
  });
}

export function listAgentRunLogs(apiBase: string, runId: string) {
  return request<FlightRecorderEvent[]>(
    apiBase,
    `/api/agents/runs/${encodeURIComponent(runId)}/logs`
  );
}

// ─── Image Studio ────────────────────────────────────────────────────────────

export type ImageGenerateRequest = {
  prompt: string;
  preset_id?: string;
  recipe?: Record<string, unknown>;
};

export type ImageGenerateResponse = {
  prompt_id: string;
  history: Record<string, unknown>;
};

export type ImageRecipeValidation = {
  ok: boolean;
  errors: string[];
  warnings: string[];
  nodes_count: number;
  privacy_level: 'local';
};

export type ImageRecipePreset = {
  id: string;
  title: string;
  description: string;
  tags: string[];
  estimated_vram_gb: number;
  recipe: Record<string, unknown>;
  validation: ImageRecipeValidation;
  privacy_level: 'local';
};

export type ImageRecipeListResponse = {
  recipes: ImageRecipePreset[];
  privacy_level: 'local';
};

export type ImageRecipeValidateRequest = {
  prompt?: string;
  preset_id?: string;
  recipe?: Record<string, unknown>;
};

export function listImageRecipes(apiBase: string): Promise<ImageRecipeListResponse> {
  return request<ImageRecipeListResponse>(apiBase, '/api/images/recipes');
}

export function validateImageRecipe(
  apiBase: string,
  payload: ImageRecipeValidateRequest
): Promise<ImageRecipeValidation> {
  return request<ImageRecipeValidation>(apiBase, '/api/images/validate', {
    method: 'POST',
    body: payload
  });
}

export function generateImage(apiBase: string, payload: ImageGenerateRequest): Promise<Record<string, any>> {
  return request<Record<string, any>>(apiBase, '/api/images/generate', {
    method: 'POST',
    body: payload
  });
}

// ─── Plugin Manager ──────────────────────────────────────────────────────────

export type PluginManifest = {
  name: string;
  trust_level: 'verified' | 'local-only' | 'network' | 'file' | 'shell' | 'danger';
  path: string;
  description?: string | null;
};

export function listPlugins(apiBase: string) {
  return request<PluginManifest[]>(apiBase, '/api/plugins');
}

// ─── Automation / Workflow ───────────────────────────────────────────────────

export type WorkflowStep = {
  name: string;
  type: 'action' | 'human_approval' | 'condition';
  config?: Record<string, unknown>;
};

export type WorkflowRunRequest = {
  workflow: {
    name?: string;
    steps: WorkflowStep[];
  };
};

export type WorkflowRunResponse = {
  run_id: string;
  status: 'completed' | 'rejected' | 'pending';
  results: Array<Record<string, unknown>>;
};

export function runWorkflow(apiBase: string, payload: WorkflowRunRequest) {
  return request<WorkflowRunResponse>(apiBase, '/api/workflows/run', {
    method: 'POST',
    body: payload
  });
}

export function confirmWorkflow(apiBase: string, runId: string, approved: boolean, extra: Record<string, unknown> = {}) {
  return request<WorkflowRunResponse>(apiBase, '/api/workflows/confirm', {
    method: 'POST',
    body: { run_id: runId, approved, payload: extra }
  });
}

export function createWorkflowEventsSocket(apiBase: string): WebSocket {
  const wsBase = apiBase.replace(/^http/, 'ws');
  return new WebSocket(`${wsBase}/api/workflows/events`);
}

// ─── Deep Research ───────────────────────────────────────────────────────────

export type DeepResearchRequest = {
  query: string;
  max_subtasks?: number;
  web_access?: boolean;
};

export type ResearchResult = {
  subtask: string;
  title: string;
  url?: string | null;
  snippet?: string | null;
};

export type DeepResearchResponse = {
  query: string;
  subtasks: string[];
  results: ResearchResult[];
  privacy: PrivacyReport;
};

export function deepResearch(apiBase: string, payload: DeepResearchRequest) {
  return request<DeepResearchResponse>(apiBase, '/api/research/deep', {
    method: 'POST',
    body: {
      query: payload.query,
      max_subtasks: payload.max_subtasks ?? 5,
      web_access: payload.web_access ?? true
    }
  });
}

// ─── Deep Research Streaming ─────────────────────────────────────────────────

export type DeepResearchStreamEvent =
  | { type: 'subtask_start'; subtask: string }
  | { type: 'result_found'; result: ResearchResult }
  | { type: 'done'; response: DeepResearchResponse };

export async function* streamDeepResearch(
  apiBase: string,
  payload: DeepResearchRequest,
): AsyncGenerator<DeepResearchStreamEvent, DeepResearchResponse> {
  const response = await fetch(`${apiBase}/api/research/deep/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: payload.query,
      max_subtasks: payload.max_subtasks ?? 5,
      web_access: payload.web_access ?? true,
    }),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `${response.status} ${response.statusText}`);
  }
  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';
    let eventType = '';
    let data = '';
    for (const line of lines) {
      if (line.startsWith('event: ')) eventType = line.slice(7);
      else if (line.startsWith('data: ')) data = line.slice(6);
      else if (line === '' && eventType) {
        const parsed = JSON.parse(data);
        if (eventType === 'subtask_start') yield { type: 'subtask_start', subtask: parsed.subtask };
        else if (eventType === 'result_found') yield { type: 'result_found', result: parsed as ResearchResult };
        else if (eventType === 'done') {
          yield { type: 'done', response: parsed as DeepResearchResponse };
          return parsed as DeepResearchResponse;
        }
      }
    }
  }
  throw new Error('Stream ended without done event');
}

// ─── Contradiction Finder ────────────────────────────────────────────────────

export type ContradictionMatch = {
  left: string;
  right: string;
  similarity: number;
  sentiment_left: string;
  sentiment_right: string;
};

export function findContradictions(apiBase: string, claims: string[], threshold = 0.85) {
  return request<ContradictionMatch[]>(apiBase, '/api/research/contradictions', {
    method: 'POST',
    body: { claims, threshold }
  });
}

// ─── Artifacts ───────────────────────────────────────────────────────────────

export function listArtifacts(apiBase: string, roomId?: string) {
  const query = roomId ? `?room_id=${encodeURIComponent(roomId)}` : '';
  return request<ArtifactRecord[]>(apiBase, `/api/artifacts${query}`);
}

export function getArtifact(apiBase: string, artifactId: string) {
  return request<ArtifactRecord>(apiBase, `/api/artifacts/${encodeURIComponent(artifactId)}`);
}

// ─── RAG File Upload ─────────────────────────────────────────────────────────

export type RagIndexResponse = {
  indexed_chunks: number;
  source: string;
  room_id: string;
  document: RagDocumentRecord;
};

export async function indexFile(apiBase: string, file: File, roomId: string): Promise<RagIndexResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('room_id', roomId);

  const response = await fetch(`${apiBase}/api/rag/index/upload`, {
    method: 'POST',
    body: formData
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<RagIndexResponse>;
}

export function indexFileByPath(apiBase: string, filePath: string, roomId: string): Promise<RagIndexResponse> {
  return request<RagIndexResponse>(apiBase, '/api/rag/index', {
    method: 'POST',
    body: { file_path: filePath, room_id: roomId }
  });
}

// ─── Agent Run detail ────────────────────────────────────────────────────────

export function getAgentRun(apiBase: string, runId: string) {
  return request<AgentRun>(apiBase, `/api/agents/runs/${encodeURIComponent(runId)}`);
}

export function runAgentCode(apiBase: string, runId: string, code: string, permissions?: { allowed_folders: string[]; network: boolean; shell: boolean }) {
  return request<Record<string, unknown>>(
    apiBase,
    `/api/agents/runs/${encodeURIComponent(runId)}/code`,
    {
      method: 'POST',
      body: {
        code,
        permissions: permissions ?? { allowed_folders: [], network: false, shell: false }
      }
    }
  );
}

// ─── Audit Logs ──────────────────────────────────────────────────────────────

export type AuditLogRecord = {
  id: string;
  action: string;
  resource: string;
  details?: string | null;
  ts: string;
};

export function recordAuditLog(
  apiBase: string,
  action: string,
  resource: string,
  details?: string | null,
) {
  return request<AuditLogRecord>(apiBase, '/api/audit/logs', {
    method: 'POST',
    body: { action, resource, details },
  });
}

export function listAuditLogs(apiBase: string) {
  return request<AuditLogRecord[]>(apiBase, '/api/audit/logs');
}

// ─── Export Operations ────────────────────────────────────────────────────────

export type ExportScope = 'all' | 'artifacts' | 'research' | 'memories' | 'conversations' | 'audit_logs';
export type ExportFormat = 'json' | 'markdown' | 'csv';

export async function exportData(
  apiBase: string,
  scope: ExportScope = 'all',
  format: ExportFormat = 'json',
  roomId?: string
): Promise<void> {
  const res = await fetch(`${apiBase}/api/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scope, format, room_id: roomId ?? null }),
  });
  if (!res.ok) throw new Error(await res.text());
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  const cd = res.headers.get('Content-Disposition') ?? '';
  const match = cd.match(/filename="([^"]+)"/);
  a.href = url; a.download = match?.[1] ?? `asterion_export.${format}`;
  a.click(); URL.revokeObjectURL(url);
}

export async function runBenchmark(
  apiBase: string,
  models?: string[],
  runsPerModel = 3,
  maxTokens = 128
) {
  return request<{ results: BenchmarkModelResult[]; benchmark_prompt: string; runs_per_model: number }>(
    apiBase, '/api/benchmark/run', {
      method: 'POST',
      body: { models: models ?? null, runs_per_model: runsPerModel, max_tokens: maxTokens }
    }
  );
}

export type BenchmarkModelResult = {
  model: string; runs: number;
  avg_tokens_per_second: number; avg_time_to_first_token_ms: number;
  avg_total_time_ms: number; min_tps: number; max_tps: number; stddev_tps: number;
  vram_estimate_gb: number; privacy_level: string; error: string | null;
};

export async function getVllmStatus(apiBase: string) {
  return request<{ available: boolean; base_url: string; models: string[]; privacy_level: string }>(
    apiBase, '/api/models/vllm/status'
  );
}

// ─── System Operations ───────────────────────────────────────────────────────

export function exportSystemData(apiBase: string, passphrase?: string) {
  return request<{ backup: string }>(apiBase, '/api/system/export', {
    method: 'POST',
    body: { passphrase },
  });
}

export function importSystemData(apiBase: string, backup: string, passphrase?: string) {
  return request<{ ok: boolean }>(apiBase, '/api/system/import', {
    method: 'POST',
    body: { backup, passphrase },
  });
}

export function wipeSystemData(apiBase: string) {
  return request<{ ok: boolean }>(apiBase, '/api/system/wipe', {
    method: 'POST',
  });
}

// ─── Chat Conversations Operations ──────────────────────────────────────────

export function updateChatConversation(apiBase: string, id: string, title: string) {
  return request<ChatConversationRecord>(apiBase, `/api/chat/conversations/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: { title }
  });
}

export function deleteChatConversation(apiBase: string, id: string) {
  return request<{ deleted: boolean }>(apiBase, `/api/chat/conversations/${encodeURIComponent(id)}`, {
    method: 'DELETE'
  });
}

// ─── Telemetry Operations ───────────────────────────────────────────────────

export function reportTelemetry(
  apiBase: string,
  payload: {
    opt_in: boolean;
    event_type: string;
    details?: Record<string, unknown>;
    vram_gb?: number;
    ram_gb?: number;
    os_platform?: string;
  }
) {
  return request<{ status: string; reason?: string }>(apiBase, '/api/telemetry/report', {
    method: 'POST',
    body: payload
  });
}


