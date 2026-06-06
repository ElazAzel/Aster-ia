from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    app: str
    uptime_seconds: float
    database: dict[str, Any]
    ollama: dict[str, Any]
    schema_version: int
    privacy: dict[str, Any]


class ModelInfo(BaseModel):
    name: str
    modified_at: str | None = None
    size: int | None = None
    digest: str | None = None


class ModelsResponse(BaseModel):
    models: list[ModelInfo]
    privacy_level: Literal["local"] = "local"


class ModelPullRequest(BaseModel):
    model: str = Field(min_length=1, max_length=256)


class ModelEnsureResponse(BaseModel):
    results: dict[str, str]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=64_000)
    room_id: str = Field(default="default", min_length=1, max_length=256)
    conversation_id: str | None = None
    model: str | None = None
    files_attached: bool = False
    memory_enabled: bool = False
    web_access: bool = False


class ChatResponse(BaseModel):
    conversation_id: str
    room_id: str
    model: str
    response: str
    latency_ms: float
    artifact_id: str | None = None
    privacy_level: Literal["local"] = "local"
    ts: datetime


class ChatConversationRecord(BaseModel):
    id: str
    room_id: str
    title: str | None = None
    created_at: datetime
    message_count: int = 0
    latest_ts: datetime | None = None


class ChatConversationUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=256)


class ChatMessageRecord(BaseModel):
    id: str
    conv_id: str
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    model: str | None = None
    artifact_id: str | None = None
    ts: datetime


class PrivacyItem(BaseModel):
    what: str
    destination: str
    risk: Literal["green", "yellow", "red"]


class PrivacyReport(BaseModel):
    level: Literal["green", "yellow", "red"]
    items: list[PrivacyItem]


class PrivacyAnalyzeRequest(BaseModel):
    model_type: Literal["local", "api"] = "local"
    files_attached: bool = False
    memory_enabled: bool = False
    web_access: bool = False
    prompt: str | None = None


class HardwareProfile(BaseModel):
    vram_gb: float = 0
    ram_gb: float | None = None
    gpu_name: str | None = None


class ModelSelectRequest(BaseModel):
    task_description: str
    hw_profile: HardwareProfile


class ModelSelection(BaseModel):
    model: str
    mode: Literal["local", "api"]
    reason: str


class MemoryCreateRequest(BaseModel):
    room_id: str = Field(min_length=1, max_length=256)
    content: str = Field(min_length=1, max_length=64_000)
    source: str = Field(default="manual", min_length=1, max_length=256)
    expires_at: datetime | None = None
    privacy: PrivacyAnalyzeRequest = Field(default_factory=PrivacyAnalyzeRequest)


class MemoryUpdateRequest(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=64_000)
    source: str | None = Field(default=None, min_length=1, max_length=256)
    expires_at: datetime | None = None


class MemoryRecord(BaseModel):
    id: str
    room_id: str
    content: str
    source: str
    created_at: datetime
    expires_at: datetime | None = None
    privacy: PrivacyReport | None = None


class ContextRoomCreateRequest(BaseModel):
    id: str | None = Field(default=None, min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=128)
    color: str = Field(default="#2f80ed", min_length=3, max_length=32)
    allowed_models: list[str] = Field(default_factory=list)
    memory_policy: Literal["off", "session", "persistent"] = "session"
    retention_days: int = Field(default=30, ge=1, le=3650)
    system_prompt: str = ""


class ContextRoomUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    color: str | None = Field(default=None, min_length=3, max_length=32)
    allowed_models: list[str] | None = None
    memory_policy: Literal["off", "session", "persistent"] | None = None
    retention_days: int | None = Field(default=None, ge=1, le=3650)
    system_prompt: str | None = None


class ContextRoom(BaseModel):
    id: str
    name: str
    color: str
    allowed_models: list[str]
    memory_policy: Literal["off", "session", "persistent"]
    retention_days: int
    system_prompt: str
    created_at: datetime
    updated_at: datetime


class RagIndexRequest(BaseModel):
    file_path: str
    room_id: str = "default"


class RagSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=16_000)
    room_id: str = "default"
    limit: int = Field(default=8, ge=1, le=50)
    source_filter: str | None = None


class RagChunk(BaseModel):
    id: str
    room_id: str
    content: str
    source: str
    score: float = 0


class RagDocumentRecord(BaseModel):
    id: str
    room_id: str
    source: str
    indexed_chunks: int
    created_at: datetime


class ArtifactBlock(BaseModel):
    type: Literal["text", "code", "table", "source", "action"]
    title: str | None = None
    content: str | None = None
    language: str | None = None
    rows: list[dict[str, Any]] = Field(default_factory=list)
    source: str | None = None
    action: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactCreateRequest(BaseModel):
    room_id: str = Field(default="default", min_length=1, max_length=256)
    kind: Literal["chat", "research_report", "code", "table", "image", "workflow"] = "chat"
    title: str = Field(min_length=1, max_length=256)
    blocks: list[ArtifactBlock] = Field(default_factory=list)
    source: str = Field(default="manual", min_length=1, max_length=256)


class ArtifactRecord(BaseModel):
    id: str
    room_id: str
    kind: str
    title: str
    blocks: list[ArtifactBlock]
    source: str
    created_at: datetime


class DeepResearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=16_000)
    max_subtasks: int = Field(default=5, ge=3, le=5)
    web_access: bool = True


class ResearchResult(BaseModel):
    subtask: str
    title: str
    url: str | None = None
    snippet: str | None = None


class DeepResearchResponse(BaseModel):
    query: str
    subtasks: list[str]
    results: list[ResearchResult]
    privacy: PrivacyReport


class ResearchReceipt(BaseModel):
    source_title: str
    url: str | None = None
    quote: str | None = None
    claim: str
    confidence: Literal["high", "medium", "low"] = "medium"
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ResearchReportExportRequest(BaseModel):
    room_id: str = Field(default="default", min_length=1, max_length=256)
    query: str = Field(min_length=1, max_length=16_000)
    title: str = Field(default="Research Report", min_length=1, max_length=256)
    receipts: list[ResearchReceipt] = Field(default_factory=list)


class ResearchReportExportResponse(BaseModel):
    artifact: ArtifactRecord
    receipts_count: int


class ContradictionRequest(BaseModel):
    claims: list[str] = Field(min_length=2)
    threshold: float = Field(default=0.85, ge=0, le=1)


class ContradictionMatch(BaseModel):
    left: str
    right: str
    similarity: float
    sentiment_left: str
    sentiment_right: str


class AgentPermissions(BaseModel):
    allowed_folders: list[str] = Field(default_factory=list)
    network: bool = False
    shell: bool = False


class RuntimeSkillManifest(BaseModel):
    id: str
    name: str
    version: str = "0.1.0"
    owner: str = "asterion"
    category: str
    description: str
    privacy_level: Literal["local", "hybrid", "external"]
    triggers: list[str] = Field(default_factory=list)
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)
    requires_consent: list[str] = Field(default_factory=list)
    failure_modes: list[str] = Field(default_factory=list)
    acceptance_checks: list[str] = Field(default_factory=list)


class AgentManifest(BaseModel):
    id: str
    name: str
    version: str = "0.1.0"
    role: str
    description: str
    privacy_level: Literal["local", "hybrid", "external"]
    default_model: str
    triggers: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    permissions: AgentPermissions = Field(default_factory=AgentPermissions)
    lifecycle: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    handoff_targets: list[str] = Field(default_factory=list)
    acceptance_checks: list[str] = Field(default_factory=list)
    system_prompt: str
    escalation_policy: str


class AgentCatalog(BaseModel):
    agents: list[AgentManifest]
    skills: list[RuntimeSkillManifest]


class AgentPlan(BaseModel):
    steps: list[str]
    required_permissions: list[str]
    estimated_tokens: int


class AgentRunCodeRequest(BaseModel):
    code: str = Field(min_length=1, max_length=32_000)
    permissions: AgentPermissions = Field(default_factory=AgentPermissions)


class AgentRunCreateRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=128)
    room_id: str = Field(default="default", min_length=1, max_length=256)
    task: str = Field(min_length=1, max_length=16_000)
    plan: AgentPlan | None = None
    permissions: AgentPermissions = Field(default_factory=AgentPermissions)


class AgentRunUpdateRequest(BaseModel):
    status: Literal["planned", "running", "paused", "completed", "failed", "cancelled"] | None = None
    agent_id: str | None = None


class AgentRun(BaseModel):
    id: str
    agent_id: str
    room_id: str
    status: Literal["planned", "running", "paused", "completed", "failed", "cancelled"]
    plan: AgentPlan
    permissions: AgentPermissions
    created_at: datetime
    updated_at: datetime


class FlightRecorderEvent(BaseModel):
    id: str
    run_id: str
    ts: datetime
    action: str
    tool: str
    privacy_level: Literal["local", "hybrid", "external"]
    input: str | None = None
    output: str | None = None
    model: str | None = None
    error: str | None = None


class ComfyGenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=16_000)
    recipe: dict[str, Any] = Field(default_factory=dict)


class WorkflowRunRequest(BaseModel):
    workflow: dict[str, Any]


class WorkflowConfirmRequest(BaseModel):
    run_id: str
    approved: bool = True
    payload: dict[str, Any] = Field(default_factory=dict)


class PluginManifest(BaseModel):
    name: str
    trust_level: Literal["verified", "local-only", "network", "file", "shell", "danger"]
    path: str
    description: str | None = None


class TelemetryReportRequest(BaseModel):
    opt_in: bool
    event_type: str
    details: dict[str, Any] = Field(default_factory=dict)
    vram_gb: float | None = None
    ram_gb: float | None = None
    os_platform: str | None = None

