use std::collections::HashMap;

use serde_json::Value;

use crate::harness::BaseHarness;

const ACTION_KEYWORDS: &[&str] = &[
    "todo", "action", "follow up", "deadline", "task",
    "нужно", "надо", "сделать", "задача", "дедлайн",
];

const DECISION_KEYWORDS: &[&str] = &[
    "decided", "decision", "agreed", "решили", "решение", "согласовали",
];

pub struct VoiceService {
    privacy_level: String,
    model_name: String,
    device: String,
    compute_type: String,
}

impl Default for VoiceService {
    fn default() -> Self {
        Self {
            privacy_level: "local".into(),
            model_name: "base".into(),
            device: "cpu".into(),
            compute_type: "int8".into(),
        }
    }
}

impl VoiceService {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn status(&self) -> HashMap<String, Value> {
        let mut result = HashMap::new();
        result.insert("ok".into(), Value::Bool(true));
        result.insert("privacy_level".into(), Value::String(self.privacy_level.clone()));
        result.insert("engine".into(), Value::String("fallback".into()));
        result.insert("whisper_available".into(), Value::Bool(false));
        result.insert("model_name".into(), Value::String(self.model_name.clone()));
        result.insert("device".into(), Value::String(self.device.clone()));
        result.insert("supported_formats".into(), Value::Array(
            vec!["flac", "m4a", "mp3", "ogg", "wav", "webm"]
                .into_iter()
                .map(|f| Value::String(f.into()))
                .collect()
        ));
        result.insert("note".into(), Value::String(
            "Transcription runs locally when faster-whisper is installed. \
             Fallback mode keeps files local and returns a setup hint.".into()
        ));
        result
    }

    pub fn sentences(&self, text: &str) -> Vec<String> {
        let text = text.replace('\n', " ");
        let mut result = Vec::new();
        let mut current = String::new();

        for ch in text.chars() {
            current.push(ch);
            if ch == '.' || ch == '!' || ch == '?' {
                let trimmed = current.trim().to_string();
                if !trimmed.is_empty() {
                    result.push(trimmed);
                }
                current = String::new();
            }
        }
        let trimmed = current.trim().to_string();
        if !trimmed.is_empty() {
            result.push(trimmed);
        }

        result
    }

    pub fn extract_summary(&self, text: &str, max_sentences: usize) -> Vec<String> {
        let sentences = self.sentences(text);
        if sentences.is_empty() {
            return Vec::new();
        }
        let meaningful: Vec<&str> = sentences.iter().filter(|s| s.len() > 20).map(|s| s.as_str()).collect();
        let source: Vec<&str> = if meaningful.is_empty() {
            sentences.iter().map(|s| s.as_str()).collect()
        } else {
            meaningful
        };
        source.into_iter().take(max_sentences).map(|s| s.to_string()).collect()
    }

    pub fn extract_action_items(&self, text: &str) -> Vec<String> {
        self.sentences(text)
            .into_iter()
            .filter(|s| ACTION_KEYWORDS.iter().any(|kw| s.to_lowercase().contains(kw)))
            .collect()
    }

    pub fn extract_decisions(&self, text: &str) -> Vec<String> {
        self.sentences(text)
            .into_iter()
            .filter(|s| DECISION_KEYWORDS.iter().any(|kw| s.to_lowercase().contains(kw)))
            .collect()
    }

    pub fn extract_questions(&self, text: &str) -> Vec<String> {
        self.sentences(text)
            .into_iter()
            .filter(|s| s.trim().ends_with('?'))
            .collect()
    }

    pub fn analyze_meeting(&self, transcript: &str) -> HashMap<String, Value> {
        let mut result = HashMap::new();
        result.insert(
            "summary".into(),
            Value::Array(self.extract_summary(transcript, 3).into_iter().map(Value::String).collect()),
        );
        result.insert(
            "action_items".into(),
            Value::Array(self.extract_action_items(transcript).into_iter().map(Value::String).collect()),
        );
        result.insert(
            "decisions".into(),
            Value::Array(self.extract_decisions(transcript).into_iter().map(Value::String).collect()),
        );
        result.insert(
            "questions".into(),
            Value::Array(self.extract_questions(transcript).into_iter().map(Value::String).collect()),
        );
        result.insert("privacy_level".into(), Value::String(self.privacy_level.clone()));
        result
    }

    pub fn to_markdown(&self, text: &str, mode: &str) -> String {
        let summary = self.extract_summary(text, 3);
        let actions = self.extract_action_items(text);
        let decisions = self.extract_decisions(text);
        let questions = self.extract_questions(text);

        let mut lines: Vec<String> = vec![format!("# Voice {} Title", mode)];

        if !summary.is_empty() {
            lines.push("".into());
            lines.push("## Summary".into());
            for item in &summary {
                lines.push(format!("- {item}"));
            }
        }
        if !decisions.is_empty() {
            lines.push("".into());
            lines.push("## Decisions".into());
            for item in &decisions {
                lines.push(format!("- {item}"));
            }
        }
        if !actions.is_empty() {
            lines.push("".into());
            lines.push("## Action Items".into());
            for item in &actions {
                lines.push(format!("- {item}"));
            }
        }
        if !questions.is_empty() {
            lines.push("".into());
            lines.push("## Questions".into());
            for item in &questions {
                lines.push(format!("- {item}"));
            }
        }
        if !text.is_empty() {
            lines.push("".into());
            lines.push("## Transcript".into());
            lines.push(text.into());
        }

        lines.join("\n")
    }
}

impl BaseHarness for VoiceService {
    fn privacy_level(&self) -> &str {
        &self.privacy_level
    }

    fn execute(&self, payload: Option<HashMap<String, Value>>) -> Value {
        let p = payload.unwrap_or_default();
        let action = p.get("action").and_then(|v| v.as_str()).unwrap_or("status");

        match action {
            "status" => serde_json::to_value(self.status()).unwrap_or_default(),
            "meeting" => {
                let transcript = p
                    .get("transcript")
                    .and_then(|v| v.as_str())
                    .unwrap_or("");
                serde_json::to_value(self.analyze_meeting(transcript)).unwrap_or_default()
            }
            "structure" => {
                let text = p.get("text").and_then(|v| v.as_str()).unwrap_or("");
                let mode = p.get("mode").and_then(|v| v.as_str()).unwrap_or("notes");
                let markdown = self.to_markdown(text, mode);
                let mut result: HashMap<&str, Value> = HashMap::new();
                result.insert("mode".into(), Value::String(mode.into()));
                result.insert(
                    "summary".into(),
                    Value::Array(self.extract_summary(text, 3).into_iter().map(Value::String).collect()),
                );
                result.insert(
                    "action_items".into(),
                    Value::Array(self.extract_action_items(text).into_iter().map(Value::String).collect()),
                );
                result.insert(
                    "decisions".into(),
                    Value::Array(self.extract_decisions(text).into_iter().map(Value::String).collect()),
                );
                result.insert(
                    "questions".into(),
                    Value::Array(self.extract_questions(text).into_iter().map(Value::String).collect()),
                );
                result.insert("markdown".into(), Value::String(markdown));
                result.insert("privacy_level".into(), Value::String(self.privacy_level.clone()));
                serde_json::to_value(result).unwrap_or_default()
            }
            _ => Value::Null,
        }
    }

    fn get_state(&self) -> HashMap<String, Value> {
        let mut state = HashMap::new();
        state.insert("model_name".into(), Value::String(self.model_name.clone()));
        state.insert("device".into(), Value::String(self.device.clone()));
        state.insert("compute_type".into(), Value::String(self.compute_type.clone()));
        state
    }

    fn set_state(&self, _state: HashMap<String, Value>) {}
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sentences_splits() {
        let vs = VoiceService::new();
        let s = vs.sentences("Hello world. How are you? I am fine!");
        assert_eq!(s.len(), 3);
    }

    #[test]
    fn test_sentences_single() {
        let vs = VoiceService::new();
        let s = vs.sentences("Just one sentence");
        assert_eq!(s.len(), 1);
    }

    #[test]
    fn test_extract_summary() {
        let vs = VoiceService::new();
        let text = "Short. This is a longer meaningful sentence that should be included. Another meaningful one right here.";
        let summary = vs.extract_summary(text, 2);
        assert_eq!(summary.len(), 2);
        assert!(summary[0].len() > 20);
    }

    #[test]
    fn test_extract_action_items() {
        let vs = VoiceService::new();
        let text = "We need to do this. The deadline is Friday. Nothing else.";
        let items = vs.extract_action_items(text);
        assert_eq!(items.len(), 1);
        assert!(items[0].contains("deadline"));
    }

    #[test]
    fn test_extract_decisions() {
        let vs = VoiceService::new();
        let text = "We decided to proceed. The team agreed on the plan.";
        let decisions = vs.extract_decisions(text);
        assert_eq!(decisions.len(), 2);
    }

    #[test]
    fn test_extract_questions() {
        let vs = VoiceService::new();
        let text = "What is this? Unknown. Where are we going?";
        let questions = vs.extract_questions(text);
        assert_eq!(questions.len(), 2);
    }

    #[test]
    fn test_status_response() {
        let vs = VoiceService::new();
        let status = vs.status();
        assert_eq!(status.get("ok").and_then(|v| v.as_bool()), Some(true));
        assert_eq!(
            status.get("privacy_level").and_then(|v| v.as_str()),
            Some("local")
        );
    }

    #[test]
    fn test_status_has_supported_formats() {
        let vs = VoiceService::new();
        let status = vs.status();
        let formats = status.get("supported_formats").and_then(|v| v.as_array());
        assert!(formats.is_some());
        assert!(formats.unwrap().len() >= 5);
    }

    #[test]
    fn test_analyze_meeting_structure() {
        let vs = VoiceService::new();
        let text = "We decided to launch. John has a deadline on Friday. What is the budget?";
        let result = vs.analyze_meeting(text);
        assert!(result.contains_key("summary"));
        assert!(result.contains_key("action_items"));
        assert!(result.contains_key("decisions"));
        assert!(result.contains_key("questions"));
    }

    #[test]
    fn test_to_markdown() {
        let vs = VoiceService::new();
        let text = "We decided to launch. Action item: test.";
        let md = vs.to_markdown(text, "notes");
        assert!(md.contains("# Voice notes"));
        assert!(md.contains("## Decisions"));
    }

    #[test]
    fn test_privacy_level() {
        let vs = VoiceService::new();
        assert_eq!(vs.privacy_level(), "local");
    }

    #[test]
    fn test_get_state() {
        let vs = VoiceService::new();
        let state = vs.get_state();
        assert_eq!(state.get("model_name").and_then(|v| v.as_str()), Some("base"));
    }

    #[test]
    fn test_execute_status() {
        let vs = VoiceService::new();
        let result = vs.execute(None);
        let status: HashMap<String, Value> = serde_json::from_value(result).unwrap();
        assert_eq!(status.get("ok").and_then(|v| v.as_bool()), Some(true));
    }

    #[test]
    fn test_voice_enforces_privacy_level() {
        let vs = VoiceService::new();
        let status = vs.status();
        assert_eq!(
            status.get("engine").and_then(|v| v.as_str()),
            Some("fallback")
        );
    }
}
