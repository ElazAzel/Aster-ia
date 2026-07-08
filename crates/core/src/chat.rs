use std::collections::HashMap;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Mutex;

use regex::Regex;
use serde_json::Value;

use crate::harness::BaseHarness;
use crate::schemas::{
    ArtifactBlock, ChatConversationRecord, ChatMessageRecord, ChatRequest, ChatResponse,
};

static CONV_COUNTER: AtomicU64 = AtomicU64::new(1);
static MSG_COUNTER: AtomicU64 = AtomicU64::new(1000);

fn now_iso() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let d = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();
    let secs = d.as_secs();
    let h = (secs % 86400) / 3600;
    let m = (secs % 3600) / 60;
    let s = secs % 60;
    format!("2026-06-30T{:02}:{:02}:{:02}Z", h, m, s)
}

fn code_fence_re() -> Regex {
    Regex::new(r"(?s)```(?P<lang>[A-Za-z0-9_.+-]*)\s*\n(?P<code>.*?)```")
        .expect("valid regex")
}

pub struct ChatService {
    privacy_level: String,
    default_model: String,
    history_limit: usize,
    #[allow(dead_code)]
    max_tokens: usize,
    conversations: Mutex<Vec<Conversation>>,
}

struct Conversation {
    id: String,
    room_id: String,
    title: Option<String>,
    created_at: String,
    messages: Vec<ChatMessageRecord>,
}

impl Default for ChatService {
    fn default() -> Self {
        Self {
            privacy_level: "local".into(),
            default_model: "llama3.2".into(),
            history_limit: 20,
            max_tokens: 2048,
            conversations: Mutex::new(Vec::new()),
        }
    }
}

impl ChatService {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn with_config(default_model: &str, history_limit: usize, max_tokens: usize) -> Self {
        Self {
            default_model: default_model.into(),
            history_limit,
            max_tokens,
            ..Self::default()
        }
    }

    pub fn create_conversation(&self, room_id: &str, conv_id: Option<&str>) -> String {
        let mut convs = self.conversations.lock().unwrap();
        if let Some(cid) = conv_id {
            if convs.iter().any(|c| c.id == cid) {
                return cid.into();
            }
        }
        let id = conv_id
            .map(|s| s.to_string())
            .unwrap_or_else(|| format!("conv-{}", CONV_COUNTER.fetch_add(1, Ordering::SeqCst)));
        convs.push(Conversation {
            id: id.clone(),
            room_id: room_id.into(),
            title: None,
            created_at: now_iso(),
            messages: Vec::new(),
        });
        id
    }

    pub fn list_conversations(&self, room_id: Option<&str>) -> Vec<ChatConversationRecord> {
        let convs = self.conversations.lock().unwrap();
        convs
            .iter()
            .filter(|c| room_id.map_or(true, |rid| c.room_id == rid))
            .map(|c| ChatConversationRecord {
                id: c.id.clone(),
                room_id: c.room_id.clone(),
                title: c.title.clone(),
                created_at: c.created_at.clone(),
                message_count: c.messages.len() as u32,
            })
            .collect()
    }

    pub fn get_messages(&self, conv_id: &str) -> Vec<ChatMessageRecord> {
        let convs = self.conversations.lock().unwrap();
        convs
            .iter()
            .find(|c| c.id == conv_id)
            .map(|c| c.messages.clone())
            .unwrap_or_default()
    }

    pub fn delete_conversation(&self, conv_id: &str) -> bool {
        let mut convs = self.conversations.lock().unwrap();
        let len_before = convs.len();
        convs.retain(|c| c.id != conv_id);
        convs.len() < len_before
    }

    pub fn update_title(&self, conv_id: &str, title: &str) -> bool {
        let mut convs = self.conversations.lock().unwrap();
        if let Some(conv) = convs.iter_mut().find(|c| c.id == conv_id) {
            conv.title = Some(title.into());
            true
        } else {
            false
        }
    }

    fn append_message(
        &self,
        conv_id: &str,
        role: &str,
        content: &str,
        model: Option<&str>,
    ) {
        let mut convs = self.conversations.lock().unwrap();
        if let Some(conv) = convs.iter_mut().find(|c| c.id == conv_id) {
            conv.messages.push(ChatMessageRecord {
                id: format!("msg-{}", MSG_COUNTER.fetch_add(1, Ordering::SeqCst)),
                conv_id: conv_id.into(),
                role: role.into(),
                content: content.into(),
                model: model.map(|m| m.into()),
                ts: now_iso(),
            });
        }
    }

    pub fn build_history(&self, conv_id: &str) -> Vec<(String, String)> {
        let convs = self.conversations.lock().unwrap();
        if let Some(conv) = convs.iter().find(|c| c.id == conv_id) {
            let limit = self.history_limit;
            let start = conv.messages.len().saturating_sub(limit);
            conv.messages[start..]
                .iter()
                .map(|m| (m.role.clone(), m.content.clone()))
                .collect()
        } else {
            Vec::new()
        }
    }

    pub fn generate<F>(&self, request: ChatRequest, model_fn: F) -> ChatResponse
    where
        F: FnOnce(&str, &[(String, String)]) -> String,
    {
        let started = std::time::Instant::now();
        let model = request
            .model
            .clone()
            .unwrap_or_else(|| self.default_model.clone());

        let conv_id = self.create_conversation(&request.room_id, request.conversation_id.as_deref());

        self.append_message(&conv_id, "user", &request.message, Some(&model));

        let history = self.build_history(&conv_id);
        let text = model_fn(&model, &history);

        self.append_message(&conv_id, "assistant", &text, Some(&model));

        let latency_ms = started.elapsed().as_secs_f64() * 1000.0;

        ChatResponse {
            conversation_id: conv_id,
            room_id: request.room_id,
            model,
            response: text,
            latency_ms,
            artifact_id: None,
            privacy_level: self.privacy_level.clone(),
            ts: now_iso(),
        }
    }

    pub fn response_blocks(response: &str, model: &str) -> Vec<ArtifactBlock> {
        let stripped = response.trim();
        if stripped.is_empty() {
            return vec![ArtifactBlock {
                r#type: "text".into(),
                title: Some("Empty response".into()),
                content: Some(String::new()),
                language: None,
                metadata: {
                    let mut m = HashMap::new();
                    m.insert("model".into(), Value::String(model.into()));
                    m
                },
            }];
        }

        let re = code_fence_re();
        let mut blocks: Vec<ArtifactBlock> = Vec::new();
        let mut cursor = 0;

        for cap in re.captures_iter(stripped) {
            let match_start = cap.get(0).unwrap().start();
            let preface = stripped[cursor..match_start].trim();
            if !preface.is_empty() {
                blocks.push(ArtifactBlock {
                    r#type: "text".into(),
                    title: Some("Assistant response".into()),
                    content: Some(preface.into()),
                    language: None,
                    metadata: {
                        let mut m = HashMap::new();
                        m.insert("model".into(), Value::String(model.into()));
                        m
                    },
                });
            }

            let lang = cap.name("lang").and_then(|m| {
                let s = m.as_str().trim();
                if s.is_empty() { None } else { Some(s.to_string()) }
            });
            let code = cap.name("code").map(|m| m.as_str().trim().to_string());

            blocks.push(ArtifactBlock {
                r#type: "code".into(),
                title: Some("Code block".into()),
                content: code,
                language: lang,
                metadata: {
                    let mut m = HashMap::new();
                    m.insert("model".into(), Value::String(model.into()));
                    m
                },
            });

            cursor = cap.get(0).unwrap().end();
        }

        let tail = stripped[cursor..].trim();
        if !tail.is_empty() {
            blocks.push(ArtifactBlock {
                r#type: "text".into(),
                title: Some("Assistant response".into()),
                content: Some(tail.into()),
                language: None,
                metadata: {
                    let mut m = HashMap::new();
                    m.insert("model".into(), Value::String(model.into()));
                    m
                },
            });
        }

        if blocks.is_empty() {
            blocks.push(ArtifactBlock {
                r#type: "text".into(),
                title: Some("Assistant response".into()),
                content: Some(response.into()),
                language: None,
                metadata: {
                    let mut m = HashMap::new();
                    m.insert("model".into(), Value::String(model.into()));
                    m
                },
            });
        }

        blocks
    }
}

impl BaseHarness for ChatService {
    fn privacy_level(&self) -> &str {
        &self.privacy_level
    }

    fn execute(&self, payload: Option<HashMap<String, Value>>) -> Value {
        let p = payload.unwrap_or_default();
        let msg = p
            .get("message")
            .and_then(|v| v.as_str())
            .unwrap_or("ping");
        let room_id = p
            .get("room_id")
            .and_then(|v| v.as_str())
            .unwrap_or("harness");
        let model = p.get("model").and_then(|v| v.as_str());

        let request = ChatRequest {
            message: msg.into(),
            room_id: room_id.into(),
            conversation_id: None,
            model: model.map(|s| s.into()),
            memory_enabled: false,
            web_access: false,
        };

        let response = self.generate(request, |_model, _history| {
            format!("Echo: {}", msg)
        });

        serde_json::to_value(response).unwrap_or_default()
    }

    fn get_state(&self) -> HashMap<String, Value> {
        let mut state = HashMap::new();
        state.insert(
            "default_model".into(),
            Value::String(self.default_model.clone()),
        );
        state.insert(
            "privacy_level".into(),
            Value::String(self.privacy_level.clone()),
        );
        state
    }

    fn set_state(&self, state: HashMap<String, Value>) {
        let convs = self.conversations.lock().unwrap();
        if let Some(_model) = state.get("default_model").and_then(|v| v.as_str()) {
            // Can't modify Mutex-guarded field directly; handle via logic
            drop(convs);
            // We don't support changing default_model at runtime yet
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn mock_model(_model: &str, _history: &[(String, String)]) -> String {
        "Hello! I am a local AI assistant.".into()
    }

    fn mock_code_model(_model: &str, _history: &[(String, String)]) -> String {
        "Here is some code:\n```python\nprint('hello')\n```\nAnd that's it.".into()
    }

    fn make_req(message: &str) -> ChatRequest {
        ChatRequest {
            message: message.into(),
            room_id: "default".into(),
            conversation_id: None,
            model: None,
            memory_enabled: false,
            web_access: false,
        }
    }

    #[test]
    fn test_generate_creates_conversation_and_responds() {
        let svc = ChatService::new();
        let resp = svc.generate(make_req("hello"), mock_model);
        assert_eq!(resp.response, "Hello! I am a local AI assistant.");
        assert!(resp.conversation_id.starts_with("conv-"));
        assert_eq!(resp.room_id, "default");
        assert_eq!(resp.model, "llama3.2");
        assert_eq!(resp.privacy_level, "local");
    }

    #[test]
    fn test_generate_stores_user_and_assistant_messages() {
        let svc = ChatService::new();
        let resp = svc.generate(make_req("hi"), mock_model);
        let msgs = svc.get_messages(&resp.conversation_id);
        assert_eq!(msgs.len(), 2);
        assert_eq!(msgs[0].role, "user");
        assert_eq!(msgs[0].content, "hi");
        assert_eq!(msgs[1].role, "assistant");
        assert_eq!(msgs[1].content, "Hello! I am a local AI assistant.");
    }

    #[test]
    fn test_generate_with_custom_model() {
        let svc = ChatService::new();
        let req = ChatRequest {
            model: Some("codellama".into()),
            ..make_req("write code")
        };
        let resp = svc.generate(req, |m, _| {
            assert_eq!(m, "codellama");
            "fn main() {}".into()
        });
        assert_eq!(resp.model, "codellama");
        assert_eq!(resp.response, "fn main() {}");
    }

    #[test]
    fn test_conversation_reuses_existing_id() {
        let svc = ChatService::new();
        let cid = svc.create_conversation("room1", None);
        let req = ChatRequest {
            conversation_id: Some(cid.clone()),
            ..make_req("again")
        };
        let resp = svc.generate(req, mock_model);
        assert_eq!(resp.conversation_id, cid);
        assert_eq!(svc.get_messages(&cid).len(), 2);
    }

    #[test]
    fn test_list_conversations() {
        let svc = ChatService::new();
        svc.create_conversation("room1", None);
        svc.create_conversation("room1", None);
        svc.create_conversation("room2", None);
        assert_eq!(svc.list_conversations(Some("room1")).len(), 2);
        assert_eq!(svc.list_conversations(Some("room2")).len(), 1);
        assert_eq!(svc.list_conversations(None).len(), 3);
    }

    #[test]
    fn test_delete_conversation() {
        let svc = ChatService::new();
        let cid = svc.create_conversation("r", None);
        assert!(svc.delete_conversation(&cid));
        assert!(!svc.delete_conversation("nonexistent"));
    }

    #[test]
    fn test_update_title() {
        let svc = ChatService::new();
        let cid = svc.create_conversation("r", None);
        assert!(svc.update_title(&cid, "My Chat"));
        let convs = svc.list_conversations(None);
        assert_eq!(convs[0].title.as_deref(), Some("My Chat"));
    }

    #[test]
    fn test_build_history_respects_limit() {
        let svc = ChatService::with_config("llama3.2", 3, 2048);
        // Create a conversation and manually insert messages
        {
            let mut convs = svc.conversations.lock().unwrap();
            let mut msgs = Vec::new();
            for i in 0..10 {
                msgs.push(ChatMessageRecord {
                    id: format!("m{i}"),
                    conv_id: "test".into(),
                    role: if i % 2 == 0 { "user".into() } else { "assistant".into() },
                    content: format!("message {i}"),
                    model: None,
                    ts: now_iso(),
                });
            }
            convs.push(Conversation {
                id: "test".into(),
                room_id: "r".into(),
                title: None,
                created_at: now_iso(),
                messages: msgs,
            });
        }
        let history = svc.build_history("test");
        assert_eq!(history.len(), 3);
        assert_eq!(history[0].1, "message 7");
        assert_eq!(history[2].1, "message 9");
    }

    #[test]
    fn test_build_history_empty_conv() {
        let svc = ChatService::new();
        assert!(svc.build_history("nonexistent").is_empty());
    }

    #[test]
    fn test_get_messages_nonexistent() {
        let svc = ChatService::new();
        assert!(svc.get_messages("nope").is_empty());
    }

    #[test]
    fn test_response_blocks_plain_text() {
        let blocks = ChatService::response_blocks("Just a text response.", "llama3.2");
        assert_eq!(blocks.len(), 1);
        assert_eq!(blocks[0].r#type, "text");
    }

    #[test]
    fn test_response_blocks_code_fence() {
        let blocks =
            ChatService::response_blocks("Here:\n```python\nprint(1)\n```\nDone.", "codellama");
        assert_eq!(blocks.len(), 3);
        assert_eq!(blocks[0].r#type, "text");
        assert_eq!(blocks[1].r#type, "code");
        assert_eq!(
            blocks[1].content.as_deref(),
            Some("print(1)")
        );
        assert_eq!(blocks[1].language.as_deref(), Some("python"));
        assert_eq!(blocks[2].r#type, "text");
    }

    #[test]
    fn test_response_blocks_multiple_code_fences() {
        let blocks = ChatService::response_blocks(
            "First:\n```py\na=1\n```\nSecond:\n```js\nlet x=2;\n```",
            "llama3.2",
        );
        assert_eq!(blocks.len(), 4);
        assert_eq!(blocks[0].r#type, "text");
        assert_eq!(blocks[1].r#type, "code");
        assert_eq!(blocks[2].r#type, "text");
        assert_eq!(blocks[3].r#type, "code");
    }

    #[test]
    fn test_response_blocks_no_language() {
        let blocks = ChatService::response_blocks("```\nplain code\n```", "llama3.2");
        assert_eq!(blocks.len(), 1);
        assert_eq!(blocks[0].r#type, "code");
        assert!(blocks[0].language.is_none());
    }

    #[test]
    fn test_response_blocks_empty_response() {
        let blocks = ChatService::response_blocks("", "llama3.2");
        assert_eq!(blocks.len(), 1);
        assert_eq!(blocks[0].r#type, "text");
        assert_eq!(blocks[0].title.as_deref(), Some("Empty response"));
    }

    #[test]
    fn test_response_blocks_whitespace_only() {
        let blocks = ChatService::response_blocks("   \n  ", "llama3.2");
        assert_eq!(blocks.len(), 1);
        assert_eq!(blocks[0].r#type, "text");
    }

    #[test]
    fn test_generate_with_code_response() {
        let svc = ChatService::new();
        let resp = svc.generate(make_req("write python"), mock_code_model);
        assert!(resp.response.contains("```python"));
    }

    #[test]
    fn test_privacy_level() {
        let svc = ChatService::new();
        assert_eq!(svc.privacy_level(), "local");
    }

    #[test]
    fn test_execute_via_harness() {
        let svc = ChatService::new();
        let mut p = HashMap::new();
        p.insert("message".into(), Value::String("hello".into()));
        let result = svc.execute(Some(p));
        let resp: ChatResponse = serde_json::from_value(result).unwrap();
        assert_eq!(resp.response, "Echo: hello");
    }

    #[test]
    fn test_execute_without_payload() {
        let svc = ChatService::new();
        let result = svc.execute(None);
        let resp: ChatResponse = serde_json::from_value(result).unwrap();
        assert_eq!(resp.response, "Echo: ping");
    }

    #[test]
    fn test_get_state() {
        let svc = ChatService::new();
        let state = svc.get_state();
        assert_eq!(state.get("default_model").and_then(|v| v.as_str()), Some("llama3.2"));
        assert_eq!(state.get("privacy_level").and_then(|v| v.as_str()), Some("local"));
    }

    #[test]
    fn test_conversation_count_in_record() {
        let svc = ChatService::new();
        let cid = svc.create_conversation("r", None);
        svc.generate(
            ChatRequest {
                conversation_id: Some(cid.clone()),
                ..make_req("msg1")
            },
            mock_model,
        );
        svc.generate(
            ChatRequest {
                conversation_id: Some(cid.clone()),
                ..make_req("msg2")
            },
            mock_model,
        );
        let convs = svc.list_conversations(Some("r"));
        assert_eq!(convs[0].message_count, 4);
    }

    #[test]
    fn test_response_blocks_metadata() {
        let blocks = ChatService::response_blocks("Hello", "test-model");
        assert_eq!(
            blocks[0].metadata.get("model").and_then(|v| v.as_str()),
            Some("test-model")
        );
    }
}
