use std::collections::HashMap;
use std::path::Path;
use std::process::Command;

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

pub struct AgentSandbox;

impl Default for AgentSandbox {
    fn default() -> Self {
        Self
    }
}

impl AgentSandbox {
    pub fn new() -> Self {
        Self
    }

    fn find_python() -> Option<&'static str> {
        let candidates = if cfg!(target_os = "windows") {
            &["python", "py", "python3"] as &[&str]
        } else {
            &["python3", "python"] as &[&str]
        };
        for cmd in candidates {
            if Command::new(cmd)
                .arg("--version")
                .output()
                .map(|o| o.status.success())
                .unwrap_or(false)
            {
                return Some(cmd);
            }
        }
        None
    }

    pub fn run_code(&self, code: &str, permissions: &AgentPermissions) -> Result<HashMap<String, Value>, String> {
        validate_code(code, permissions)?;

        let allowed_root = if permissions.allowed_folders.is_empty() {
            std::env::temp_dir()
        } else {
            std::path::PathBuf::from(&permissions.allowed_folders[0])
        };

        let python_cmd = Self::find_python().ok_or_else(|| "Python interpreter not found".to_string())?;
        let output = Command::new(python_cmd)
            .args(["-c", code])
            .current_dir(&allowed_root)
            .output();

        match output {
            Ok(out) => {
                let mut result = HashMap::new();
                result.insert("exit_code".into(), Value::Number(out.status.code().unwrap_or(-1).into()));
                result.insert("stdout".into(), Value::String(String::from_utf8_lossy(&out.stdout).to_string()));
                result.insert("stderr".into(), Value::String(String::from_utf8_lossy(&out.stderr).to_string()));
                result.insert("sandbox_dir".into(), Value::String(allowed_root.to_string_lossy().to_string()));
                result.insert("permissions".into(), serde_json::json!({
                    "network": permissions.network,
                    "shell": permissions.shell,
                    "allowed_folders": permissions.allowed_folders,
                }));
                Ok(result)
            }
            Err(e) => Err(format!("Failed to execute code: {e}")),
        }
    }
}

impl BaseHarness for AgentSandbox {
    fn privacy_level(&self) -> &str {
        "local"
    }

    fn execute(&self, payload: Option<HashMap<String, Value>>) -> Value {
        let p = payload.unwrap_or_default();
        let code = p.get("code").and_then(|v| v.as_str()).unwrap_or("");
        let permissions = p.get("permissions")
            .and_then(|v| serde_json::from_value::<AgentPermissions>(v.clone()).ok())
            .unwrap_or(AgentPermissions {
                allowed_folders: vec![],
                network: false,
                shell: false,
            });

        match self.run_code(code, &permissions) {
            Ok(result) => serde_json::to_value(result).unwrap_or_default(),
            Err(e) => serde_json::json!({"error": e}),
        }
    }

    fn get_state(&self) -> HashMap<String, Value> {
        let mut state = HashMap::new();
        state.insert("subprocess".into(), Value::String("python".into()));
        state.insert("network_default".into(), Value::Bool(false));
        state.insert("shell_default".into(), Value::Bool(false));
        state
    }

    fn set_state(&self, _state: HashMap<String, Value>) {}
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
    fn test_agent_sandbox_run_code_ok() {
        let sandbox = AgentSandbox::new();
        let perms = AgentPermissions {
            allowed_folders: vec![],
            network: false,
            shell: false,
        };
        let result = sandbox.run_code("print('hi')", &perms);
        // Accept either success or python-unavailable — we only test the sandbox interface
        if let Ok(r) = result {
            assert_eq!(r.get("exit_code").and_then(|v| v.as_i64()), Some(0));
        }
    }

    #[test]
    fn test_agent_sandbox_run_code_rejected() {
        let sandbox = AgentSandbox::new();
        let perms = AgentPermissions {
            allowed_folders: vec![],
            network: false,
            shell: false,
        };
        let result = sandbox.run_code("import subprocess", &perms);
        assert!(result.is_err());
    }

    #[test]
    fn test_agent_sandbox_execute_via_harness() {
        let sandbox = AgentSandbox::new();
        let mut p = HashMap::new();
        p.insert("code".into(), Value::String("print('ok')".into()));
        let result = sandbox.execute(Some(p));
        let r: HashMap<String, Value> = serde_json::from_value(result).unwrap();
        // Accept either exit_code=0 (python works) or no exit_code (python unavailable)
        if let Some(ec) = r.get("exit_code").and_then(|v| v.as_i64()) {
            assert_eq!(ec, 0);
        }
    }

    #[test]
    fn test_agent_sandbox_privacy_level() {
        let sandbox = AgentSandbox::new();
        assert_eq!(sandbox.privacy_level(), "local");
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
