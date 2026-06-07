use std::collections::HashMap;
use std::sync::Mutex;

use serde_json::Value;

use crate::harness::BaseHarness;
use crate::schemas::{DeepResearchResponse, ResearchResult};

pub struct SupervisorAgent {
    privacy_level: String,
    searxng_url: Mutex<String>,
}

impl Default for SupervisorAgent {
    fn default() -> Self {
        Self {
            privacy_level: "local".into(),
            searxng_url: Mutex::new("http://127.0.0.1:8080".into()),
        }
    }
}

impl SupervisorAgent {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn with_searxng(url: &str) -> Self {
        Self {
            privacy_level: "local".into(),
            searxng_url: Mutex::new(url.trim_end_matches('/').to_string()),
        }
    }

    pub fn decompose(&self, query: &str, max_subtasks: usize) -> Vec<String> {
        let aspects = [
            "core facts and definitions",
            "recent evidence and examples",
            "risks and constraints",
            "implementation options",
            "open questions",
        ];
        aspects
            .iter()
            .take(max_subtasks)
            .map(|aspect| format!("{query} - {aspect}"))
            .collect()
    }

    pub fn research(
        &self,
        query: &str,
        max_subtasks: usize,
        web_access: bool,
    ) -> DeepResearchResponse {
        let subtasks = self.decompose(query, max_subtasks);

        if !web_access {
            return DeepResearchResponse {
                query: query.into(),
                subtasks,
                results: vec![],
                privacy: None,
            };
        }

        DeepResearchResponse {
            query: query.into(),
            subtasks,
            results: vec![],
            privacy: None,
        }
    }
}

impl BaseHarness for SupervisorAgent {
    fn privacy_level(&self) -> &str {
        &self.privacy_level
    }

    fn execute(&self, payload: Option<HashMap<String, Value>>) -> Value {
        let p = payload.unwrap_or_default();
        let query = p.get("query").and_then(|v| v.as_str()).unwrap_or("");
        let max_subtasks = p
            .get("max_subtasks")
            .and_then(|v| v.as_u64())
            .unwrap_or(5) as usize;
        let web_access = p.get("web_access").and_then(|v| v.as_bool()).unwrap_or(true);

        let response = self.research(query, max_subtasks, web_access);
        serde_json::to_value(response).unwrap_or_default()
    }

    fn get_state(&self) -> HashMap<String, Value> {
        let mut state = HashMap::new();
        state.insert(
            "searxng_url".into(),
            Value::String(self.searxng_url.lock().unwrap().clone()),
        );
        state
    }

    fn set_state(&self, state: HashMap<String, Value>) {
        if let Some(url) = state.get("searxng_url").and_then(|v| v.as_str()) {
            *self.searxng_url.lock().unwrap() = url.trim_end_matches('/').to_string();
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_decompose_limits() {
        let agent = SupervisorAgent::new();
        let subtasks = agent.decompose("AI safety", 3);
        assert_eq!(subtasks.len(), 3);
        assert!(subtasks[0].contains("AI safety"));
        assert!(subtasks[0].contains("core facts"));
    }

    #[test]
    fn test_decompose_max_is_5() {
        let agent = SupervisorAgent::new();
        let subtasks = agent.decompose("test", 10);
        assert_eq!(subtasks.len(), 5);
    }

    #[test]
    fn test_research_no_web_returns_empty() {
        let agent = SupervisorAgent::new();
        let response = agent.research("test", 3, false);
        assert_eq!(response.query, "test");
        assert_eq!(response.subtasks.len(), 3);
        assert!(response.results.is_empty());
    }

    #[test]
    fn test_research_with_web_returns_stub() {
        let agent = SupervisorAgent::new();
        let response = agent.research("test", 2, true);
        assert_eq!(response.subtasks.len(), 2);
        assert!(response.results.is_empty());
    }

    #[test]
    fn test_get_state() {
        let agent = SupervisorAgent::new();
        let state = agent.get_state();
        assert!(state.contains_key("searxng_url"));
    }

    #[test]
    fn test_set_state_updates_url() {
        let agent = SupervisorAgent::with_searxng("http://old:8888");
        let mut state = HashMap::new();
        state.insert(
            "searxng_url".into(),
            Value::String("http://new:9999".into()),
        );
        agent.set_state(state);
        assert_eq!(*agent.searxng_url.lock().unwrap(), "http://new:9999");
    }

    #[test]
    fn test_privacy_level() {
        let agent = SupervisorAgent::new();
        assert_eq!(agent.privacy_level(), "local");
    }

    #[test]
    fn test_execute_via_harness() {
        let agent = SupervisorAgent::new();
        let mut p = HashMap::new();
        p.insert("query".into(), Value::String("hello".into()));
        p.insert("max_subtasks".into(), Value::Number(2.into()));
        p.insert("web_access".into(), Value::Bool(false));
        let result = agent.execute(Some(p));
        let response: DeepResearchResponse = serde_json::from_value(result).unwrap();
        assert_eq!(response.query, "hello");
    }
}
