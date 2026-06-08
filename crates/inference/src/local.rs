use crate::engine::InferenceEngine;
use crate::{InferenceRequest, InferenceResponse, EmbedRequest, EmbedResponse, InferenceUsage};

pub struct LocalEngine {
    pub model_path: String,
    pub n_gpu_layers: u32,
    pub context_size: u32,
}

impl LocalEngine {
    pub fn new(model_path: &str, n_gpu_layers: u32, context_size: u32) -> Self {
        Self {
            model_path: model_path.to_string(),
            n_gpu_layers,
            context_size,
        }
    }
}

impl InferenceEngine for LocalEngine {
    async fn generate(&self, req: InferenceRequest) -> Result<InferenceResponse, String> {
        #[cfg(feature = "native")]
        {
            use llama_cpp_2::llama_backend::LlamaBackend;
            use llama_cpp_2::model::params::LlamaModelParams;
            use llama_cpp_2::model::LlamaModel;
            use llama_cpp_2::context::params::LlamaContextParams;
            use llama_cpp_2::sampling::LlamaSampler;

            // 1. Initialize backend
            let backend = LlamaBackend::init().map_err(|e| e.to_string())?;

            // 2. Set model params and load model
            let mut m_params = LlamaModelParams::default();
            m_params = m_params.with_n_gpu_layers(self.n_gpu_layers);
            
            let model = LlamaModel::load_from_file(&backend, &self.model_path, &m_params)
                .map_err(|e| e.to_string())?;

            // 3. Setup context params and create context
            let mut c_params = LlamaContextParams::default();
            c_params = c_params.with_n_ctx(std::num::NonZeroU32::new(self.context_size));
            
            let mut ctx = model.new_context(&backend, c_params)
                .map_err(|e| e.to_string())?;

            // 4. Extract prompt from request
            let prompt = req.messages.last().map(|m| m.content.as_str()).unwrap_or("");
            
            // 5. Tokenize
            let tokens = model.str_to_token(prompt, true)
                .map_err(|e| e.to_string())?;

            // 6. Decode prompt tokens
            let mut batch = llama_cpp_2::batch::LlamaBatch::new(self.context_size as usize, 1);
            for (i, token) in tokens.iter().enumerate() {
                batch.add(*token, i as i32, &[0], i == tokens.len() - 1);
            }
            ctx.decode(&mut batch).map_err(|e| e.to_string())?;

            // 7. Simple sampling loop (limit to 100 tokens for safety/latency)
            let mut sampler = LlamaSampler::chain_simple(vec![]);
            let mut generated_text = String::new();
            let mut n_predict = 0;
            let mut last_token = tokens.last().copied().unwrap_or(0);

            while n_predict < 100 {
                let token_id = sampler.sample(&ctx, batch.n_tokens() - 1);
                if model.is_eog(token_id) {
                    break;
                }
                
                let token_str = model.token_to_str(token_id).map_err(|e| e.to_string())?;
                generated_text.push_str(&token_str);

                // Prepare next batch
                batch.clear();
                batch.add(token_id, (tokens.len() + n_predict) as i32, &[0], true);
                ctx.decode(&mut batch).map_err(|e| e.to_string())?;

                n_predict += 1;
            }

            Ok(InferenceResponse {
                text: generated_text,
                model: req.model,
                usage: Some(InferenceUsage {
                    prompt_tokens: tokens.len() as u32,
                    completion_tokens: n_predict,
                }),
            })
        }

        #[cfg(not(feature = "native"))]
        {
            // Simulate generation delay or mock response
            let prompt = req.messages.last().map(|m| m.content.as_str()).unwrap_or("");
            let text = format!("Mock LocalEngine response to '{}' from model '{}'.", prompt, self.model_path);
            
            Ok(InferenceResponse {
                text,
                model: req.model,
                usage: Some(InferenceUsage {
                    prompt_tokens: (prompt.len() / 4) as u32,
                    completion_tokens: 25,
                }),
            })
        }
    }

    async fn embed(&self, req: EmbedRequest) -> Result<EmbedResponse, String> {
        #[cfg(feature = "native")]
        {
            use llama_cpp_2::llama_backend::LlamaBackend;
            use llama_cpp_2::model::params::LlamaModelParams;
            use llama_cpp_2::model::LlamaModel;
            use llama_cpp_2::context::params::LlamaContextParams;

            // Initialize and load
            let backend = LlamaBackend::init().map_err(|e| e.to_string())?;
            let mut m_params = LlamaModelParams::default();
            m_params = m_params.with_n_gpu_layers(self.n_gpu_layers);
            
            let model = LlamaModel::load_from_file(&backend, &self.model_path, &m_params)
                .map_err(|e| e.to_string())?;

            let mut c_params = LlamaContextParams::default();
            c_params = c_params.with_n_ctx(std::num::NonZeroU32::new(self.context_size));
            c_params = c_params.with_embeddings(true); // Enable embeddings

            let mut ctx = model.new_context(&backend, c_params)
                .map_err(|e| e.to_string())?;

            let mut embeddings = Vec::new();

            for text in &req.input {
                let tokens = model.str_to_token(text, true).map_err(|e| e.to_string())?;
                let mut batch = llama_cpp_2::batch::LlamaBatch::new(tokens.len(), 1);
                for (i, token) in tokens.iter().enumerate() {
                    batch.add(*token, i as i32, &[0], i == tokens.len() - 1);
                }

                ctx.decode(&mut batch).map_err(|e| e.to_string())?;
                
                // Get embedding vector from context
                let embedding_slice = ctx.embeddings_seq(0)
                    .map_err(|e| e.to_string())?;
                embeddings.push(embedding_slice.to_vec());
            }

            Ok(EmbedResponse {
                model: req.model,
                embeddings,
            })
        }

        #[cfg(not(feature = "native"))]
        {
            let mut embeddings = Vec::new();
            for text in &req.input {
                // Generate a dummy 384-dim normalized vector based on string hash
                let mut vec = vec![0.0f32; 384];
                let hash = text.chars().map(|c| c as u32).sum::<u32>();
                for (i, val) in vec.iter_mut().enumerate() {
                    *val = (((hash + i as u32) % 100) as f32 / 100.0) * 0.1;
                }
                embeddings.push(vec);
            }
            Ok(EmbedResponse {
                model: req.model,
                embeddings,
            })
        }
    }
}
