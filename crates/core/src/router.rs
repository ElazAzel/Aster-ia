use std::collections::HashMap;

use serde_json::Value;

use crate::harness::BaseHarness;
use crate::schemas::{HardwareProfile, ModelEntry, ModelSelection};

/// ModelRouter — selects optimal local model based on hardware profile and task.
/// Mirrors `asterion_api.services.model_router.ModelRouter` from Python.
pub struct ModelRouter {
    pub local_catalog: Vec<ModelEntry>,
    pub api_fallback: String,
    task_routing: HashMap<String, Vec<String>>,
}

impl Default for ModelRouter {
    fn default() -> Self {
        Self::new()
    }
}

impl ModelRouter {
    pub fn new() -> Self {
        let local_catalog = vec![
            ModelEntry { model: "llama3.2:1b".into(), required_vram_gb: 0.0, ram_gb: 2.0, tags: vec!["chat".into(), "fast".into()], reason: "ultra-light CPU-only chat".into() },
            ModelEntry { model: "qwen2.5:0.5b".into(), required_vram_gb: 0.0, ram_gb: 1.5, tags: vec!["chat".into(), "fast".into()], reason: "smallest viable model, CPU".into() },
            ModelEntry { model: "phi3:mini".into(), required_vram_gb: 0.0, ram_gb: 3.0, tags: vec!["chat".into(), "reasoning".into()], reason: "Microsoft phi-3, excellent CPU perf".into() },
            ModelEntry { model: "gemma2:2b".into(), required_vram_gb: 0.0, ram_gb: 3.0, tags: vec!["chat".into()], reason: "Google Gemma2 2B, balanced".into() },
            ModelEntry { model: "llama3.2:3b".into(), required_vram_gb: 3.0, ram_gb: 4.0, tags: vec!["chat".into()], reason: "Meta 3B, good small GPU model".into() },
            ModelEntry { model: "qwen2.5:3b".into(), required_vram_gb: 3.0, ram_gb: 4.0, tags: vec!["chat".into(), "multilingual".into()], reason: "Qwen 3B, strong Russian/Chinese".into() },
            ModelEntry { model: "mistral:7b".into(), required_vram_gb: 5.0, ram_gb: 8.0, tags: vec!["chat".into(), "reasoning".into()], reason: "Mistral 7B instruction tuned".into() },
            ModelEntry { model: "codellama:7b".into(), required_vram_gb: 5.0, ram_gb: 8.0, tags: vec!["code".into()], reason: "Meta CodeLlama 7B, strong code".into() },
            ModelEntry { model: "qwen2.5:7b".into(), required_vram_gb: 5.5, ram_gb: 8.0, tags: vec!["chat".into(), "multilingual".into(), "reasoning".into()], reason: "Qwen2.5 7B, top Russian".into() },
            ModelEntry { model: "llama3.2".into(), required_vram_gb: 6.0, ram_gb: 8.0, tags: vec!["chat".into(), "general".into()], reason: "Meta Llama 3.2 8B, best general purpose".into() },
            ModelEntry { model: "llama3.1:8b".into(), required_vram_gb: 6.0, ram_gb: 8.0, tags: vec!["chat".into(), "reasoning".into()], reason: "Meta Llama 3.1 8B instruction".into() },
            ModelEntry { model: "gemma2:9b".into(), required_vram_gb: 6.5, ram_gb: 10.0, tags: vec!["chat".into(), "reasoning".into()], reason: "Google Gemma2 9B, excellent reasoning".into() },
            ModelEntry { model: "deepseek-coder-v2".into(), required_vram_gb: 10.0, ram_gb: 16.0, tags: vec!["code".into()], reason: "DeepSeek Coder V2, GPT-4 level code".into() },
            ModelEntry { model: "qwen2.5:14b".into(), required_vram_gb: 10.0, ram_gb: 16.0, tags: vec!["chat".into(), "multilingual".into(), "reasoning".into()], reason: "Qwen2.5 14B, top quality".into() },
            ModelEntry { model: "qwen2.5:32b".into(), required_vram_gb: 20.0, ram_gb: 32.0, tags: vec!["chat".into(), "reasoning".into(), "code".into()], reason: "Qwen2.5 32B, near-GPT4 quality".into() },
            ModelEntry { model: "llava:13b".into(), required_vram_gb: 8.0, ram_gb: 12.0, tags: vec!["vision".into()], reason: "LLaVA 1.6 13B, image understanding".into() },
            ModelEntry { model: "nomic-embed-text".into(), required_vram_gb: 0.0, ram_gb: 1.0, tags: vec!["embed".into()], reason: "Nomic embed for RAG, required".into() },
        ];

        let mut task_routing = HashMap::new();
        task_routing.insert("code".into(), vec!["code".into(), "reasoning".into(), "general".into()]);
        task_routing.insert("russian".into(), vec!["multilingual".into(), "chat".into()]);
        task_routing.insert("research".into(), vec!["reasoning".into(), "chat".into()]);
        task_routing.insert("vision".into(), vec!["vision".into()]);
        task_routing.insert("embed".into(), vec!["embed".into()]);
        task_routing.insert("quick".into(), vec!["fast".into(), "chat".into()]);
        task_routing.insert("general".into(), vec!["general".into(), "chat".into(), "reasoning".into()]);

        Self { local_catalog, api_fallback: "gpt-4o-mini".into(), task_routing }
    }

    /// Select the best model for a given task and hardware profile.
    /// Mirrors `ModelRouter.select()` in Python.
    pub fn select(&self, task_description: &str, hw: &HardwareProfile) -> ModelSelection {
        let task_lower = task_description.to_lowercase();
        let mut preferred_tags: Vec<String> = Vec::new();
        for (keyword, tags) in &self.task_routing {
            if task_lower.contains(keyword) {
                preferred_tags.extend(tags.iter().cloned());
            }
        }

        let user_ram = hw.ram_gb.unwrap_or(f64::INFINITY);

        let viable: Vec<&ModelEntry> = self.local_catalog.iter()
            .filter(|m| hw.vram_gb >= m.required_vram_gb && user_ram >= m.ram_gb)
            .collect();

        if viable.is_empty() {
            let vram = hw.vram_gb;
            let ram = hw.ram_gb.map(|r| format!("{:.1}", r)).unwrap_or_else(|| "N/A".into());
            return ModelSelection {
                model: self.api_fallback.clone(),
                mode: "api".into(),
                reason: format!("No local model fits VRAM={vram:.1}GB RAM={ram}GB; API fallback."),
            };
        }

        let best = viable.into_iter()
            .max_by(|a, b| {
                let score_a = self.score(a, &preferred_tags, hw.vram_gb);
                let score_b = self.score(b, &preferred_tags, hw.vram_gb);
                score_a.partial_cmp(&score_b).unwrap_or(std::cmp::Ordering::Equal)
            })
            .expect("viable is non-empty");

        ModelSelection {
            model: best.model.clone(),
            mode: "local".into(),
            reason: format!("VRAM {}GB OK; task-matched {}.", hw.vram_gb, best.reason),
        }
    }

    fn score(&self, entry: &ModelEntry, preferred_tags: &[String], vram_gb: f64) -> f64 {
        let tag_match = entry.tags.iter()
            .filter(|t| preferred_tags.contains(t))
            .count() as f64;
        let vram_headroom = vram_gb - entry.required_vram_gb;
        tag_match * 10.0 + vram_headroom.min(4.0)
    }

    pub fn get_task_routing(&self) -> &HashMap<String, Vec<String>> {
        &self.task_routing
    }
}

impl BaseHarness for ModelRouter {
    fn privacy_level(&self) -> &str {
        "local"
    }

    fn execute(&self, payload: Option<HashMap<String, Value>>) -> Value {
        let payload = payload.unwrap_or_default();
        let task = payload.get("task_description").and_then(|v| v.as_str()).unwrap_or("");
        let hw_map = payload.get("hw_profile").and_then(|v| v.as_object()).cloned().unwrap_or_default();
        let hw = HardwareProfile {
            vram_gb: hw_map.get("vram_gb").and_then(|v| v.as_f64()).unwrap_or(0.0),
            ram_gb: hw_map.get("ram_gb").and_then(|v| v.as_f64()),
        };
        let result = self.select(task, &hw);
        serde_json::to_value(result).unwrap_or_default()
    }

    fn get_state(&self) -> HashMap<String, Value> {
        let mut state = HashMap::new();
        state.insert("api_fallback".into(), Value::String(self.api_fallback.clone()));
        state
    }

    fn set_state(&self, _state: HashMap<String, Value>) {
        // Mutation not supported in this version
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_has_17_models() {
        let router = ModelRouter::new();
        assert_eq!(router.local_catalog.len(), 17);
    }

    #[test]
    fn test_select_local_high_vram() {
        let router = ModelRouter::new();
        let hw = HardwareProfile { vram_gb: 24.0, ram_gb: Some(32.0) };
        let result = router.select("write Python code", &hw);
        assert_eq!(result.mode, "local");
    }

    #[test]
    fn test_select_api_fallback_no_vram() {
        let router = ModelRouter::new();
        let hw = HardwareProfile { vram_gb: 0.0, ram_gb: Some(0.5) };
        let result = router.select("complex reasoning", &hw);
        assert_eq!(result.mode, "api");
    }

    #[test]
    fn test_code_task_prefers_code_model() {
        let router = ModelRouter::new();
        let hw = HardwareProfile { vram_gb: 8.0, ram_gb: Some(16.0) };
        let result = router.select("write Python code", &hw);
        assert_eq!(result.mode, "local");
    }

    #[test]
    fn test_russian_task_picks_multilingual() {
        let router = ModelRouter::new();
        let hw = HardwareProfile { vram_gb: 8.0, ram_gb: Some(16.0) };
        let result = router.select("напиши на русском", &hw);
        assert_eq!(result.mode, "local");
    }

    #[test]
    fn test_zero_vram_still_works() {
        let router = ModelRouter::new();
        let hw = HardwareProfile { vram_gb: 0.0, ram_gb: Some(4.0) };
        let result = router.select("quick chat", &hw);
        assert_eq!(result.mode, "local");
        assert!(["llama3.2:1b", "qwen2.5:0.5b", "phi3:mini", "gemma2:2b"].contains(&result.model.as_str()));
    }

    #[test]
    fn test_execute_via_harness() {
        let router = ModelRouter::new();
        let mut payload = HashMap::new();
        payload.insert("task_description".into(), Value::String("quick chat".into()));
        let mut hw = serde_json::Map::new();
        hw.insert("vram_gb".into(), Value::Number(serde_json::Number::from_f64(0.0).unwrap()));
        hw.insert("ram_gb".into(), Value::Number(serde_json::Number::from_f64(4.0).unwrap()));
        payload.insert("hw_profile".into(), Value::Object(hw));
        let result = router.execute(Some(payload));
        let sel: ModelSelection = serde_json::from_value(result).unwrap();
        assert_eq!(sel.mode, "local");
    }

    #[test]
    fn test_privacy_level() {
        let router = ModelRouter::new();
        assert_eq!(router.privacy_level(), "local");
    }
}
