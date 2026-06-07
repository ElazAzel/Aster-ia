use crate::{InferenceEngine, InferenceRequest, InferenceResponse};

/// Local inference engine using llama-cpp-2.
/// (Stub — Phase 2 implementation)
pub struct LocalEngine {
    pub model_path: String,
    pub n_gpu_layers: u32,
    pub context_size: u32,
}

impl InferenceEngine for LocalEngine {
    async fn generate(&self, _req: InferenceRequest) -> InferenceResponse {
        // TODO: implement with llama-cpp-2 crate
        InferenceResponse {
            text: String::new(),
            model: "local".into(),
            usage: None,
        }
    }
}
