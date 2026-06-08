from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    app: str
    uptime_seconds: float
    database: dict[str, Any]
    privacy: dict[str, Any]


class ModelInfo(BaseModel):
    name: str
    modified_at: str | None = None
    size: int | None = None
    digest: str | None = None


class ModelsResponse(BaseModel):
    models: list[ModelInfo]
    privacy_level: Literal["local"] = "local"


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
    privacy_level: Literal["local"] = "local"
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


class RagIndexRequest(BaseModel):
    file_path: str
    room_id: str = "default"


class RagSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=16_000)
    room_id: str = "default"
    limit: int = Field(default=8, ge=1, le=50)


class RagChunk(BaseModel):
    id: str
    room_id: str
    content: str
    source: str
    score: float = 0


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
    category: str
    description: str
    privacy_level: Literal["local", "hybrid", "external"]
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)


class AgentManifest(BaseModel):
    id: str
    name: str
    role: str
    description: str
    privacy_level: Literal["local", "hybrid", "external"]
    default_model: str
    skills: list[str] = Field(default_factory=list)
    permissions: AgentPermissions = Field(default_factory=AgentPermissions)
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


class WorkflowRunStatus(BaseModel):
    id: str
    status: str
    workflow: dict[str, Any]
    results: list[dict[str, Any]]
    created_at: str
    updated_at: str
