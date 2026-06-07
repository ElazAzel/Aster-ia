use serde::{Deserialize, Serialize};

/// Hardware profile describing available GPU/CPU resources.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HardwareProfile {
    pub vram_gb: f64,
    pub ram_gb: Option<f64>,
}

/// Result of model selection routing.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelSelection {
    pub model: String,
    pub mode: String,
    pub reason: String,
}

/// Entry in the local model catalog.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelEntry {
    pub model: String,
    pub required_vram_gb: f64,
    pub ram_gb: f64,
    pub tags: Vec<String>,
    pub reason: String,
}

/// Benchmark result for a model.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenchmarkResult {
    pub model: String,
    pub tokens_per_second: f64,
    pub latency_ms: f64,
    pub vram_gb: f64,
    pub cache_hit: bool,
    pub ts: String,
}

/// Plugin manifest loaded from a plugin directory.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PluginManifest {
    pub name: String,
    pub trust_level: String,
    pub path: String,
    pub description: Option<String>,
}

// ── Privacy ─────────────────────────────────────────────────────────────────

/// Single privacy item in a report.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PrivacyItem {
    pub what: String,
    pub destination: String,
    pub risk: String,
}

/// Full privacy analysis report.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PrivacyReport {
    pub level: String,
    pub items: Vec<PrivacyItem>,
}

/// Input parameters for privacy analysis.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PrivacyAnalyzeRequest {
    pub model_type: String,
    pub files_attached: bool,
    pub memory_enabled: bool,
    pub web_access: bool,
    pub prompt: Option<String>,
}

/// Runtime skill manifest — mirrors Python RuntimeSkillManifest.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RuntimeSkillManifest {
    pub id: String,
    pub name: String,
    #[serde(default = "default_version")]
    pub version: String,
    #[serde(default = "default_owner")]
    pub owner: String,
    pub category: String,
    pub description: String,
    pub privacy_level: String,
    #[serde(default)]
    pub triggers: Vec<String>,
    #[serde(default)]
    pub inputs: Vec<String>,
    #[serde(default)]
    pub outputs: Vec<String>,
    #[serde(default)]
    pub tools: Vec<String>,
    #[serde(default)]
    pub guardrails: Vec<String>,
    #[serde(default)]
    pub requires_consent: Vec<String>,
    #[serde(default)]
    pub failure_modes: Vec<String>,
    #[serde(default)]
    pub acceptance_checks: Vec<String>,
}

/// Agent manifest — mirrors Python AgentManifest.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentManifest {
    pub id: String,
    pub name: String,
    #[serde(default = "default_version")]
    pub version: String,
    pub role: String,
    pub description: String,
    pub privacy_level: String,
    pub default_model: String,
    #[serde(default)]
    pub triggers: Vec<String>,
    #[serde(default)]
    pub skills: Vec<String>,
    #[serde(default)]
    pub permissions: AgentPermissions,
    #[serde(default)]
    pub lifecycle: Vec<String>,
    #[serde(default)]
    pub outputs: Vec<String>,
    #[serde(default)]
    pub handoff_targets: Vec<String>,
    #[serde(default)]
    pub acceptance_checks: Vec<String>,
    pub system_prompt: String,
    pub escalation_policy: String,
}

/// Full agent catalog.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentCatalog {
    pub agents: Vec<AgentManifest>,
    pub skills: Vec<RuntimeSkillManifest>,
}

fn default_version() -> String {
    "0.1.0".into()
}

fn default_owner() -> String {
    "asterion".into()
}

/// Result of catalog validation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationResult {
    pub ok: bool,
    pub agents_count: usize,
    pub skills_count: usize,
    pub errors: Vec<String>,
    pub warnings: Vec<String>,
}

/// A single research result from web search.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResearchResult {
    pub subtask: String,
    pub title: String,
    pub url: Option<String>,
    pub snippet: Option<String>,
}

/// A single chunk from RAG indexing with relevance score.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RagChunk {
    pub id: String,
    pub room_id: String,
    pub content: String,
    pub source: String,
    pub score: f64,
}

/// Deep research response with query decomposition + results.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeepResearchResponse {
    pub query: String,
    pub subtasks: Vec<String>,
    pub results: Vec<ResearchResult>,
    pub privacy: Option<crate::schemas::PrivacyReport>,
}

/// Agent permissions for sandbox execution.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentPermissions {
    #[serde(default)]
    pub allowed_folders: Vec<String>,
    #[serde(default)]
    pub network: bool,
    #[serde(default)]
    pub shell: bool,
}

/// Agent plan generated by the task simulator.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentPlan {
    pub steps: Vec<String>,
    pub required_permissions: Vec<String>,
    pub estimated_tokens: u64,
}

/// Memory record stored in the ledger.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryRecord {
    pub id: String,
    pub room_id: String,
    pub content: String,
    pub source: String,
    pub created_at: String,
    pub expires_at: Option<String>,
    pub privacy: Option<PrivacyReport>,
}

/// Request to create a new memory entry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryCreateRequest {
    pub room_id: String,
    pub content: String,
    pub source: Option<String>,
    pub expires_at: Option<String>,
    pub privacy: Option<PrivacyAnalyzeRequest>,
}

/// A contradiction match between two claims.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContradictionMatch {
    pub left: String,
    pub right: String,
    pub similarity: f64,
    pub sentiment_left: String,
    pub sentiment_right: String,
}

// ── Benchmark ────────────────────────────────────────────────────────────────

/// Single benchmark run result for a model.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenchmarkRunResult {
    pub model: String,
    pub runs: usize,
    pub avg_tokens_per_second: f64,
    pub avg_time_to_first_token_ms: f64,
    pub avg_total_time_ms: f64,
    pub min_tps: f64,
    pub max_tps: f64,
    pub stddev_tps: f64,
    pub vram_estimate_gb: f64,
    pub privacy_level: String,
    pub error: Option<String>,
    pub cached_at: Option<f64>,
}
