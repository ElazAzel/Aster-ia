use std::collections::HashMap;
use std::path::Path;

use serde_json::Value;

use crate::harness::BaseHarness;
use crate::schemas::{AgentPermissions, AgentPlan};

pub struct TaskSimulator;

impl Default for TaskSimulator {
    fn default() -> Self {
        Self
    }
}

impl TaskSimulator {
    pub fn new() -> Self {
        Self
    }

    pub fn plan(&self, task: &str) -> AgentPlan {
        let lowered = task.to_lowercase();
        let mut permissions: Vec<String> = vec!["file_read".into()];

        if lowered.contains("write")
            || lowered.contains("создай")
            || lowered.contains("измен")
        {
            permissions.push("file_write".into());
        }
        if lowered.contains("web")
            || lowered.contains("search")
            || lowered.contains("поиск")
        {
            permissions.push("web_search".into());
        }
        if lowered.contains("code") || lowered.contains("python") {
            permissions.push("run_code".into());
        }

        let estimated = (task.split_whitespace().count() as u64 * 120).clamp(800, 8000);

        AgentPlan {
            steps: vec![
                "Clarify local context and inputs".into(),
                "Collect required files or search results".into(),
                "Execute the minimal allowed action".into(),
                "Validate output and summarize changes".into(),
            ],
            required_permissions: permissions,
            estimated_tokens: estimated,
        }
    }
}

impl BaseHarness for TaskSimulator {
    fn privacy_level(&self) -> &str {
        "local"
    }

    fn execute(&self, payload: Option<HashMap<String, Value>>) -> Value {
        let task = payload
            .unwrap_or_default()
            .get("task")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let plan = self.plan(&task);
        serde_json::to_value(plan).unwrap_or_default()
    }

    fn get_state(&self) -> HashMap<String, Value> {
        let mut state = HashMap::new();
        state.insert("planner".into(), Value::String("heuristic".into()));
        state
    }

    fn set_state(&self, _state: HashMap<String, Value>) {}
}

// ── Permission validation (pure logic, no subprocess) ───────────────────────

pub fn validate_code(code: &str, permissions: &AgentPermissions) -> Result<(), String> {
    let lowered = code.to_lowercase();
    if !permissions.shell {
        let shell_tokens = ["subprocess", "os.system"];
        if shell_tokens.iter().any(|t| lowered.contains(t)) {
            return Err("shell permission is disabled".into());
        }
    }
    if !permissions.network {
        let network_tokens = ["socket", "httpx", "requests", "urllib"];
        if network_tokens.iter().any(|t| lowered.contains(t)) {
            return Err("network permission is disabled".into());
        }
    }
    Ok(())
}

pub fn resolve_allowed(path: &str, permissions: &AgentPermissions) -> Result<String, String> {
    let resolved = Path::new(path)
        .canonicalize()
        .map_err(|e| format!("cannot resolve path: {e}"))?;

    let resolved_str = resolved.to_string_lossy().to_string();

    for folder in &permissions.allowed_folders {
        let root = Path::new(folder);
        let root_canonical = root
            .canonicalize()
            .map_err(|e| format!("cannot resolve root {folder}: {e}"))?;

        if resolved == root_canonical || resolved.starts_with(&root_canonical) {
            return Ok(resolved_str);
        }
    }

    Err("path is outside allowed folders".into())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_plan_simple_read() {
        let ts = TaskSimulator::new();
        let plan = ts.plan("read the file");
        assert!(plan.required_permissions.contains(&"file_read".to_string()));
        assert!(!plan.required_permissions.contains(&"file_write".to_string()));
        assert!(!plan.required_permissions.contains(&"web_search".to_string()));
    }

    #[test]
    fn test_plan_write_web() {
        let ts = TaskSimulator::new();
        let plan = ts.plan("создай and search web");
        assert!(plan.required_permissions.contains(&"file_write".to_string()));
        assert!(plan.required_permissions.contains(&"web_search".to_string()));
    }

    #[test]
    fn test_plan_code() {
        let ts = TaskSimulator::new();
        let plan = ts.plan("run python code");
        assert!(plan.required_permissions.contains(&"run_code".to_string()));
    }

    #[test]
    fn test_plan_estimated_tokens_clamped() {
        let ts = TaskSimulator::new();
        let plan = ts.plan("short");
        assert_eq!(plan.estimated_tokens, 800);
    }

    #[test]
    fn test_plan_estimated_tokens_large() {
        let ts = TaskSimulator::new();
        let long = "word ".repeat(100);
        let plan = ts.plan(&long);
        assert!(plan.estimated_tokens >= 800);
        assert!(plan.estimated_tokens <= 8000);
        assert_eq!(plan.steps.len(), 4);
    }

    #[test]
    fn test_privacy_level() {
        let ts = TaskSimulator::new();
        assert_eq!(ts.privacy_level(), "local");
    }

    #[test]
    fn test_execute_returns_plan() {
        let ts = TaskSimulator::new();
        let mut p = HashMap::new();
        p.insert("task".into(), Value::String("search web".into()));
        let result = ts.execute(Some(p));
        let plan: AgentPlan = serde_json::from_value(result).unwrap();
        assert!(plan.required_permissions.contains(&"web_search".to_string()));
    }

    #[test]
    fn test_validate_code_shell_blocked() {
        let perms = AgentPermissions {
            allowed_folders: vec![],
            network: false,
            shell: false,
        };
        assert!(validate_code("import subprocess; subprocess.run()", &perms).is_err());
        assert!(validate_code("import os; os.system('ls')", &perms).is_err());
    }

    #[test]
    fn test_validate_code_network_blocked() {
        let perms = AgentPermissions {
            allowed_folders: vec![],
            network: false,
            shell: false,
        };
        assert!(validate_code("import httpx", &perms).is_err());
        assert!(validate_code("import socket", &perms).is_err());
    }

    #[test]
    fn test_validate_code_allowed() {
        let perms = AgentPermissions {
            allowed_folders: vec![],
            network: false,
            shell: false,
        };
        assert!(validate_code("print('hello')", &perms).is_ok());
    }

    #[test]
    fn test_validate_code_permissions_granted() {
        let perms = AgentPermissions {
            allowed_folders: vec![],
            network: true,
            shell: true,
        };
        assert!(validate_code("import httpx", &perms).is_ok());
        assert!(validate_code("import subprocess", &perms).is_ok());
    }
}
