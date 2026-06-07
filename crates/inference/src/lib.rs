/// Asterion AI inference engine.
///
/// This crate will wrap llama-cpp-2 for local LLM inference,
/// whisper-rs for speech-to-text, and provide a unified
/// InferenceEngine trait that both desktop and cloud use.
///
/// Phase 2: Replace Python-side OllamaService + VllmService + VoiceService.

pub mod engine;

use serde::{Deserialize, Serialize};

/// Unified request format for any inference backend.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InferenceRequest {
    pub model: String,
    pub messages: Vec<InferenceMessage>,
    pub max_tokens: Option<u32>,
    pub temperature: Option<f32>,
    pub stream: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InferenceMessage {
    pub role: String,
    pub content: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InferenceResponse {
    pub text: String,
    pub model: String,
    pub usage: Option<InferenceUsage>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InferenceUsage {
    pub prompt_tokens: u32,
    pub completion_tokens: u32,
}

/// Trait for inference backends (local, cloud, hybrid).
pub trait InferenceEngine: Send + Sync {
    fn generate(&self, req: InferenceRequest) -> impl std::future::Future<Output = InferenceResponse> + Send;
}
