use crate::engine::InferenceEngine;
use crate::{InferenceRequest, InferenceResponse, EmbedRequest, EmbedResponse, InferenceUsage};
use reqwest::header::{HeaderMap, HeaderValue, AUTHORIZATION, CONTENT_TYPE};
use serde::{Deserialize, Serialize};

pub struct CloudClient {
    pub api_key: Option<String>,
    pub base_url: String,
}

impl CloudClient {
    pub fn new(api_key: Option<String>, base_url: &str) -> Self {
        Self {
            api_key,
            base_url: base_url.trim_end_matches('/').to_string(),
        }
    }

    fn headers(&self) -> HeaderMap {
        let mut headers = HeaderMap::new();
        headers.insert(CONTENT_TYPE, HeaderValue::from_static("application/json"));
        if let Some(ref key) = self.api_key {
            if let Ok(val) = HeaderValue::from_str(&format!("Bearer {}", key)) {
                headers.insert(AUTHORIZATION, val);
            }
        }
        headers
    }
}

// Structs to map to OpenAI completions endpoint format
#[derive(Serialize)]
struct OpenAiChatRequest {
    model: String,
    messages: Vec<OpenAiMessage>,
    #[serde(skip_serializing_if = "Option::is_none")]
    max_tokens: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    temperature: Option<f32>,
    stream: bool,
}

#[derive(Serialize, Deserialize)]
struct OpenAiMessage {
    role: String,
    content: String,
}

#[derive(Deserialize)]
struct OpenAiChatResponse {
    choices: Vec<OpenAiChoice>,
    usage: Option<OpenAiUsage>,
}

#[derive(Deserialize)]
struct OpenAiChoice {
    message: OpenAiMessage,
}

#[derive(Deserialize)]
struct OpenAiUsage {
    prompt_tokens: u32,
    completion_tokens: u32,
}

// Structs to map to OpenAI embeddings endpoint format
#[derive(Serialize)]
struct OpenAiEmbedRequest {
    model: String,
    input: Vec<String>,
}

#[derive(Deserialize)]
struct OpenAiEmbedResponse {
    data: Vec<OpenAiEmbedData>,
}

#[derive(Deserialize)]
struct OpenAiEmbedData {
    embedding: Vec<f32>,
}

impl InferenceEngine for CloudClient {
    async fn generate(&self, req: InferenceRequest) -> Result<InferenceResponse, String> {
        let client = reqwest::Client::new();
        let url = format!("{}/chat/completions", self.base_url);

        let openai_messages = req
            .messages
            .into_iter()
            .map(|m| OpenAiMessage {
                role: m.role,
                content: m.content,
            })
            .collect();

        let payload = OpenAiChatRequest {
            model: req.model.clone(),
            messages: openai_messages,
            max_tokens: req.max_tokens,
            temperature: req.temperature,
            stream: false, // We'll handle streaming when required by standard client logic
        };

        let res = client
            .post(&url)
            .headers(self.headers())
            .json(&payload)
            .send()
            .await
            .map_err(|e| format!("Request failed: {}", e))?;

        if !res.status().is_success() {
            let status = res.status();
            let err_text = res.text().await.unwrap_or_default();
            return Err(format!("Cloud API error ({}): {}", status, err_text));
        }

        let resp: OpenAiChatResponse = res
            .json()
            .await
            .map_err(|e| format!("Failed to parse JSON response: {}", e))?;

        let choice = resp.choices.first().ok_or("No choices returned from Cloud API")?;

        Ok(InferenceResponse {
            text: choice.message.content.clone(),
            model: req.model,
            usage: resp.usage.map(|u| InferenceUsage {
                prompt_tokens: u.prompt_tokens,
                completion_tokens: u.completion_tokens,
            }),
        })
    }

    async fn embed(&self, req: EmbedRequest) -> Result<EmbedResponse, String> {
        let client = reqwest::Client::new();
        let url = format!("{}/embeddings", self.base_url);

        let payload = OpenAiEmbedRequest {
            model: req.model.clone(),
            input: req.input,
        };

        let res = client
            .post(&url)
            .headers(self.headers())
            .json(&payload)
            .send()
            .await
            .map_err(|e| format!("Request failed: {}", e))?;

        if !res.status().is_success() {
            let status = res.status();
            let err_text = res.text().await.unwrap_or_default();
            return Err(format!("Cloud API error ({}): {}", status, err_text));
        }

        let resp: OpenAiEmbedResponse = res
            .json()
            .await
            .map_err(|e| format!("Failed to parse JSON response: {}", e))?;

        let mut embeddings = Vec::new();
        for item in resp.data {
            embeddings.push(item.embedding);
        }

        Ok(EmbedResponse {
            model: req.model,
            embeddings,
        })
    }
}
