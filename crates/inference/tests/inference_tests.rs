use asterion_inference::local::LocalEngine;
use asterion_inference::whisper::WhisperEngine;
use asterion_inference::cloud::CloudClient;
use asterion_inference::benchmark::BenchmarkEngine;
use asterion_inference::engine::{InferenceEngine, AudioTranscriber};
use asterion_inference::{InferenceRequest, InferenceMessage, EmbedRequest, TranscriptionRequest};

// A dummy InferenceEngine for benchmarking tests
struct DummyEngine {
    response_text: String,
}

impl InferenceEngine for DummyEngine {
    async fn generate(&self, req: InferenceRequest) -> Result<asterion_inference::InferenceResponse, String> {
        Ok(asterion_inference::InferenceResponse {
            text: self.response_text.clone(),
            model: req.model,
            usage: Some(asterion_inference::InferenceUsage {
                prompt_tokens: 5,
                completion_tokens: 10,
            }),
        })
    }

    async fn embed(&self, req: EmbedRequest) -> Result<asterion_inference::EmbedResponse, String> {
        Ok(asterion_inference::EmbedResponse {
            model: req.model,
            embeddings: vec![vec![0.5; 384]],
        })
    }
}

#[tokio::test]
async fn test_local_engine_mock() {
    let engine = LocalEngine::new("llama3.2:3b", 0, 2048);
    
    let req = InferenceRequest {
        model: "llama3.2:3b".to_string(),
        messages: vec![InferenceMessage {
            role: "user".to_string(),
            content: "Hello".to_string(),
        }],
        max_tokens: None,
        temperature: None,
        stream: false,
    };
    
    let res = engine.generate(req).await.unwrap();
    assert!(res.text.contains("Mock LocalEngine response"));
    assert_eq!(res.model, "llama3.2:3b");
    assert!(res.usage.is_some());

    let embed_req = EmbedRequest {
        model: "nomic-embed-text".to_string(),
        input: vec!["Hello world".to_string()],
    };
    let embed_res = engine.embed(embed_req).await.unwrap();
    assert_eq!(embed_res.model, "nomic-embed-text");
    assert_eq!(embed_res.embeddings.len(), 1);
    assert_eq!(embed_res.embeddings[0].len(), 384);
}

#[tokio::test]
async fn test_whisper_engine_mock() {
    let transcriber = WhisperEngine::new("whisper-base");
    
    let req = TranscriptionRequest {
        file_path: "dummy.wav".to_string(),
        language: Some("ru".to_string()),
    };
    
    let res = transcriber.transcribe(req).await.unwrap();
    assert!(res.text.contains("Тестовая запись голоса"));
    assert_eq!(res.language, "ru");
    assert_eq!(res.segments.len(), 2);
    assert!(res.duration > 0.0);
}

#[test]
fn test_cloud_client_headers() {
    let client_no_auth = CloudClient::new(None, "https://api.openai.com");
    let headers_no_auth = client_no_auth.headers();
    assert!(headers_no_auth.contains_key("content-type"));
    assert!(!headers_no_auth.contains_key("authorization"));

    let client_auth = CloudClient::new(Some("secret-key".to_string()), "https://api.openai.com");
    let headers_auth = client_auth.headers();
    assert!(headers_auth.contains_key("content-type"));
    assert!(headers_auth.contains_key("authorization"));
}

#[tokio::test]
async fn test_benchmark_engine() {
    let dummy = DummyEngine {
        response_text: "Word Word Word Word Word Word Word Word Word Word".to_string(),
    };
    let bench = BenchmarkEngine::new(3);
    
    let res = bench.run_benchmark(&dummy, "llama3.2:3b", "Test prompt").await.unwrap();
    assert_eq!(res.model, "llama3.2:3b");
    assert_eq!(res.runs, 3);
    assert!(res.avg_tokens_per_second >= 0.0);
    assert!(res.avg_time_to_first_token_ms >= 0.0);
    assert!(res.avg_total_time_ms >= 0.0);
    assert!(res.error.is_none());
}
