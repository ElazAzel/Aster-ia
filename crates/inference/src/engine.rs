use crate::{InferenceRequest, InferenceResponse, EmbedRequest, EmbedResponse, TranscriptionRequest, TranscriptionResponse};

/// Trait for inference backends (local, cloud, hybrid).
pub trait InferenceEngine: Send + Sync {
    async fn generate(&self, req: InferenceRequest) -> Result<InferenceResponse, String>;
    async fn embed(&self, req: EmbedRequest) -> Result<EmbedResponse, String>;
}

/// Trait for audio transcription services (local whisper, cloud).
pub trait AudioTranscriber: Send + Sync {
    async fn transcribe(&self, req: TranscriptionRequest) -> Result<TranscriptionResponse, String>;
}
