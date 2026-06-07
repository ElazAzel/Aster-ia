use std::collections::HashMap;
use std::sync::Mutex;

use serde_json::Value;

use crate::harness::BaseHarness;

/// State of a workflow run step.
#[derive(Debug, Clone, PartialEq)]
pub enum StepStatus {
    Pending,
    Completed,
    WaitingApproval,
    Rejected,
}

/// A single workflow run's state.
struct WorkflowRun {
    steps: Vec<HashMap<String, Value>>,
    results: Vec<HashMap<String, Value>>,
    status: StepStatus,
    approval: Option<bool>,
}

pub struct WorkflowRunner {
    privacy_level: String,
    runs: Mutex<HashMap<String, WorkflowRun>>,
    counter: std::sync::atomic::AtomicU64,
}

impl Default for WorkflowRunner {
    fn default() -> Self {
        Self {
            privacy_level: "local".into(),
            runs: Mutex::new(HashMap::new()),
            counter: std::sync::atomic::AtomicU64::new(1),
        }
    }
}

impl WorkflowRunner {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn run(&self, workflow: HashMap<String, Value>) -> HashMap<String, Value> {
        let run_id = self
            .counter
            .fetch_add(1, std::sync::atomic::Ordering::SeqCst)
            .to_string();
        let steps: Vec<HashMap<String, Value>> = workflow
            .get("steps")
            .and_then(|v| v.as_array())
            .map(|arr| {
                arr.iter()
                    .filter_map(|v| v.as_object().map(|o| {
                        o.iter().map(|(k, v)| (k.clone(), v.clone())).collect()
                    }))
                    .collect()
            })
            .unwrap_or_default();

        let mut results = Vec::new();

        for step in &steps {
            let step_type = step
                .get("type")
                .and_then(|v| v.as_str())
                .unwrap_or("auto");
            let step_name = step
                .get("name")
                .and_then(|v| v.as_str())
                .unwrap_or("step");

            if step_type == "human_approval" {
                let mut runs = self.runs.lock().unwrap();
                runs.insert(
                    run_id.clone(),
                    WorkflowRun {
                        steps: steps.clone(),
                        results: results.clone(),
                        status: StepStatus::WaitingApproval,
                        approval: None,
                    },
                );
                return serde_json::json!({
                    "run_id": run_id,
                    "status": "waiting_approval",
                    "step": step_name,
                    "results": results,
                })
                .as_object()
                .map(|o| o.iter().map(|(k, v)| (k.clone(), v.clone())).collect())
                .unwrap_or_default();
            }

            let mut result = HashMap::new();
            result.insert("step".into(), Value::String(step_name.into()));
            result.insert("status".into(), Value::String("completed".into()));
            results.push(result);
        }

        serde_json::json!({
            "run_id": run_id,
            "status": "completed",
            "results": results,
        })
        .as_object()
        .map(|o| o.iter().map(|(k, v)| (k.clone(), v.clone())).collect())
        .unwrap_or_default()
    }

    pub fn confirm(&self, run_id: &str, approved: bool) -> bool {
        let mut runs = self.runs.lock().unwrap();
        if let Some(run) = runs.get_mut(run_id) {
            if run.status != StepStatus::WaitingApproval {
                return false;
            }
            run.approval = Some(approved);
            run.status = if approved {
                StepStatus::Completed
            } else {
                StepStatus::Rejected
            };
            true
        } else {
            false
        }
    }

    pub fn get_run_status(&self, run_id: &str) -> Option<Value> {
        let runs = self.runs.lock().unwrap();
        runs.get(run_id).map(|run| {
            let status_str = match run.status {
                StepStatus::Pending => "pending",
                StepStatus::Completed => "completed",
                StepStatus::WaitingApproval => "waiting_approval",
                StepStatus::Rejected => "rejected",
            };
            serde_json::json!({
                "run_id": run_id,
                "status": status_str,
                "results": run.results,
            })
        })
    }
}

impl BaseHarness for WorkflowRunner {
    fn privacy_level(&self) -> &str {
        &self.privacy_level
    }

    fn execute(&self, payload: Option<HashMap<String, Value>>) -> Value {
        let p = payload.unwrap_or_default();
        let action = p.get("action").and_then(|v| v.as_str()).unwrap_or("run");
        match action {
            "run" => {
                let workflow = p
                    .get("workflow")
                    .and_then(|v| v.as_object())
                    .map(|o| o.iter().map(|(k, v)| (k.clone(), v.clone())).collect())
                    .unwrap_or_default();
                serde_json::to_value(self.run(workflow)).unwrap_or_default()
            }
            "confirm" => {
                let run_id = p.get("run_id").and_then(|v| v.as_str()).unwrap_or("");
                let approved = p.get("approved").and_then(|v| v.as_bool()).unwrap_or(false);
                let ok = self.confirm(run_id, approved);
                serde_json::json!({"ok": ok})
            }
            "status" => {
                let run_id = p.get("run_id").and_then(|v| v.as_str()).unwrap_or("");
                self.get_run_status(run_id)
                    .unwrap_or(serde_json::json!({"error": "run not found"}))
            }
            _ => Value::Null,
        }
    }

    fn get_state(&self) -> HashMap<String, Value> {
        let runs = self.runs.lock().unwrap();
        let mut state = HashMap::new();
        let active: Vec<String> = runs
            .keys()
            .filter(|k| {
                runs.get(*k)
                    .map(|r| r.status == StepStatus::WaitingApproval)
                    .unwrap_or(false)
            })
            .cloned()
            .collect();
        state.insert("paused_runs".into(), Value::Array(
            active.into_iter().map(Value::String).collect(),
        ));
        state
    }

    fn set_state(&self, _state: HashMap<String, Value>) {}
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_step(name: &str, step_type: &str) -> HashMap<String, Value> {
        let mut step = HashMap::new();
        step.insert("name".into(), Value::String(name.into()));
        step.insert("type".into(), Value::String(step_type.into()));
        step
    }

    fn make_workflow(steps: Vec<HashMap<String, Value>>) -> HashMap<String, Value> {
        let mut wf = HashMap::new();
        wf.insert(
            "steps".into(),
            Value::Array(steps.into_iter().collect()),
        );
        wf
    }

    #[test]
    fn test_run_completes() {
        let wr = WorkflowRunner::new();
        let steps = vec![make_step("step1", "auto"), make_step("step2", "auto")];
        let result = wr.run(make_workflow(steps));
        assert_eq!(
            result.get("status").and_then(|v| v.as_str()),
            Some("completed")
        );
        let results = result.get("results").and_then(|v| v.as_array());
        assert!(results.is_some());
        assert_eq!(results.unwrap().len(), 2);
    }

    #[test]
    fn test_run_empty_workflow() {
        let wr = WorkflowRunner::new();
        let result = wr.run(HashMap::new());
        assert_eq!(
            result.get("status").and_then(|v| v.as_str()),
            Some("completed")
        );
    }

    #[test]
    fn test_run_approval_pauses() {
        let wr = WorkflowRunner::new();
        let steps = vec![make_step("approve_me", "human_approval")];
        let result = wr.run(make_workflow(steps));
        assert_eq!(
            result.get("status").and_then(|v| v.as_str()),
            Some("waiting_approval")
        );
    }

    #[test]
    fn test_confirm_approves() {
        let wr = WorkflowRunner::new();
        let steps = vec![make_step("approve_me", "human_approval")];
        let result = wr.run(make_workflow(steps));
        let run_id = result.get("run_id").and_then(|v| v.as_str()).unwrap();

        let ok = wr.confirm(run_id, true);
        assert!(ok);

        let status = wr.get_run_status(run_id).unwrap();
        assert_eq!(
            status.get("status").and_then(|v| v.as_str()),
            Some("completed")
        );
    }

    #[test]
    fn test_confirm_rejects() {
        let wr = WorkflowRunner::new();
        let steps = vec![make_step("approve_me", "human_approval")];
        let result = wr.run(make_workflow(steps));
        let run_id = result.get("run_id").and_then(|v| v.as_str()).unwrap();

        let ok = wr.confirm(run_id, false);
        assert!(ok);

        let status = wr.get_run_status(run_id).unwrap();
        assert_eq!(
            status.get("status").and_then(|v| v.as_str()),
            Some("rejected")
        );
    }

    #[test]
    fn test_confirm_nonexistent() {
        let wr = WorkflowRunner::new();
        assert!(!wr.confirm("no-such-run", true));
    }

    #[test]
    fn test_get_state_has_paused() {
        let wr = WorkflowRunner::new();
        let steps = vec![make_step("pause", "human_approval")];
        wr.run(make_workflow(steps));
        let state = wr.get_state();
        let paused = state.get("paused_runs").and_then(|v| v.as_array());
        assert!(paused.is_some());
        assert_eq!(paused.unwrap().len(), 1);
    }

    #[test]
    fn test_privacy_level() {
        let wr = WorkflowRunner::new();
        assert_eq!(wr.privacy_level(), "local");
    }

    #[test]
    fn test_execute_run_action() {
        let wr = WorkflowRunner::new();
        let steps = vec![make_step("s1", "auto")];
        let wf = make_workflow(steps);
        let mut p = HashMap::new();
        p.insert("action".into(), Value::String("run".into()));
        p.insert(
            "workflow".into(),
            Value::Object(wf.into_iter().collect()),
        );
        let result = wr.execute(Some(p));
        let r: HashMap<String, Value> = serde_json::from_value(result).unwrap();
        assert_eq!(r.get("status").and_then(|v| v.as_str()), Some("completed"));
    }
}
