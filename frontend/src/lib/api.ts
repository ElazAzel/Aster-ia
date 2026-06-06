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
  recipe?: Record<string, unknown>;
};

export type ImageGenerateResponse = {
  prompt_id: string;
  history: Record<string, unknown>;
};

export function generateImage(apiBase: string, payload: ImageGenerateRequest) {
  return request(apiBase, '/api/images/generate', {
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
