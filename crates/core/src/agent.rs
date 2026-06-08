use std::collections::{HashMap, HashSet};

use serde_json::Value;

use crate::harness::BaseHarness;
use crate::schemas::{
    AgentCatalog, AgentManifest, RuntimeSkillManifest, ValidationResult,
};

pub struct AgentRegistry {
    privacy_level: String,
    agents: Vec<AgentManifest>,
    skills: Vec<RuntimeSkillManifest>,
}

impl AgentRegistry {
    pub fn new() -> Self {
        Self {
            privacy_level: "local".into(),
            agents: Vec::new(),
            skills: Vec::new(),
        }
    }

    pub fn with_catalog(agents: Vec<AgentManifest>, skills: Vec<RuntimeSkillManifest>) -> Self {
        Self {
            privacy_level: "local".into(),
            agents,
            skills,
        }
    }

    pub fn catalog(&self) -> AgentCatalog {
        AgentCatalog {
            agents: self.agents.clone(),
            skills: self.skills.clone(),
        }
    }

    pub fn get_agent(&self, agent_id: &str) -> Option<&AgentManifest> {
        self.agents.iter().find(|a| a.id == agent_id)
    }

    pub fn get_skill(&self, skill_id: &str) -> Option<&RuntimeSkillManifest> {
        self.skills.iter().find(|s| s.id == skill_id)
    }

    pub fn validate_catalog(&self) -> ValidationResult {
        let mut errors: Vec<String> = Vec::new();
        let mut warnings: Vec<String> = Vec::new();

        // Duplicate check
        let agent_ids: Vec<&str> = self.agents.iter().map(|a| a.id.as_str()).collect();
        let skill_ids: Vec<&str> = self.skills.iter().map(|s| s.id.as_str()).collect();
        Self::append_duplicates("agent", &agent_ids, &mut errors);
        Self::append_duplicates("skill", &skill_ids, &mut errors);

        let known_skill_ids: HashSet<&str> = skill_ids.iter().cloned().collect();
        let known_agent_ids: HashSet<&str> = agent_ids.iter().cloned().collect();

        for agent in &self.agents {
            // Missing skills
            for skill_id in &agent.skills {
                if !known_skill_ids.contains(skill_id.as_str()) {
                    errors.push(format!("agent:{}: unknown skill '{}'", agent.id, skill_id));
                }
            }
            // Missing handoff targets
            for target in &agent.handoff_targets {
                if !known_agent_ids.contains(target.as_str()) {
                    errors.push(format!("agent:{}: unknown handoff target '{}'", agent.id, target));
                }
            }
            // Privacy warnings
            if agent.privacy_level == "local" && agent.permissions.network {
                warnings.push(format!("agent:{}: local privacy with network=true", agent.id));
            }
            if agent.privacy_level == "local" && agent.permissions.shell {
                warnings.push(format!("agent:{}: local privacy with shell=true", agent.id));
            }
            if agent.acceptance_checks.is_empty() {
                warnings.push(format!("agent:{}: missing acceptance checks", agent.id));
            }
        }

        for skill in &self.skills {
            if skill.privacy_level == "external" && skill.requires_consent.is_empty() {
                errors.push(format!("skill:{}: external skill must declare requires_consent", skill.id));
            }
            if skill.acceptance_checks.is_empty() {
                warnings.push(format!("skill:{}: missing acceptance checks", skill.id));
            }
        }

        ValidationResult {
            ok: errors.is_empty(),
            agents_count: self.agents.len(),
            skills_count: self.skills.len(),
            errors,
            warnings,
        }
    }

    fn append_duplicates(kind: &str, ids: &[&str], errors: &mut Vec<String>) {
        let mut seen: HashSet<&str> = HashSet::new();
        for id in ids {
            if !seen.insert(id) {
                errors.push(format!("{}:{}: duplicate id", kind, id));
            }
        }
    }

    pub fn load_from_values(
        agent_values: Vec<Value>,
        skill_values: Vec<Value>,
    ) -> (Vec<AgentManifest>, Vec<RuntimeSkillManifest>, Vec<String>) {
        let mut errors = Vec::new();
        let mut agents = Vec::new();
        let mut skills = Vec::new();

        for v in &agent_values {
            match serde_json::from_value::<AgentManifest>(v.clone()) {
                Ok(a) => agents.push(a),
                Err(e) => {
                    let id = v.get("id").and_then(|x| x.as_str()).unwrap_or("<unknown>");
                    errors.push(format!("agent:{id}: {e}"));
                }
            }
        }

        for v in &skill_values {
            match serde_json::from_value::<RuntimeSkillManifest>(v.clone()) {
                Ok(s) => skills.push(s),
                Err(e) => {
                    let id = v.get("id").and_then(|x| x.as_str()).unwrap_or("<unknown>");
                    errors.push(format!("skill:{id}: {e}"));
                }
            }
        }

        (agents, skills, errors)
    }
}

impl BaseHarness for AgentRegistry {
    fn privacy_level(&self) -> &str {
        &self.privacy_level
    }

    fn execute(&self, _payload: Option<HashMap<String, Value>>) -> Value {
        let catalog = self.catalog();
        serde_json::to_value(catalog).unwrap_or_default()
    }

    fn get_state(&self) -> HashMap<String, Value> {
        let mut state = HashMap::new();
        state.insert(
            "agents_count".into(),
            Value::Number(self.agents.len().into()),
        );
        state.insert(
            "skills_count".into(),
            Value::Number(self.skills.len().into()),
        );
        state
    }

    fn set_state(&self, _state: HashMap<String, Value>) {}
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::schemas::AgentPermissions;

    fn make_agent(id: &str, skills: Vec<&str>, handoffs: Vec<&str>) -> AgentManifest {
        AgentManifest {
            id: id.into(),
            name: id.into(),
            version: "0.1.0".into(),
            role: "test".into(),
            description: "".into(),
            privacy_level: "local".into(),
            default_model: "llama3.2".into(),
            triggers: vec![],
            skills: skills.into_iter().map(|s| s.into()).collect(),
            permissions: AgentPermissions {
                allowed_folders: vec![],
                network: false,
                shell: false,
            },
            lifecycle: vec![],
            outputs: vec![],
            handoff_targets: handoffs.into_iter().map(|h| h.into()).collect(),
            acceptance_checks: vec!["check1".into()],
            system_prompt: "".into(),
            escalation_policy: "".into(),
        }
    }

    fn make_skill(id: &str) -> RuntimeSkillManifest {
        RuntimeSkillManifest {
            id: id.into(),
            name: id.into(),
            version: "0.1.0".into(),
            owner: "asterion".into(),
            category: "test".into(),
            description: "".into(),
            privacy_level: "local".into(),
            triggers: vec![],
            inputs: vec![],
            outputs: vec![],
            tools: vec![],
            guardrails: vec![],
            requires_consent: vec![],
            failure_modes: vec![],
            acceptance_checks: vec!["check1".into()],
        }
    }

    #[test]
    fn test_catalog_empty() {
        let reg = AgentRegistry::new();
        let cat = reg.catalog();
        assert!(cat.agents.is_empty());
        assert!(cat.skills.is_empty());
    }

    #[test]
    fn test_get_agent() {
        let agents = vec![make_agent("a1", vec![], vec![])];
        let reg = AgentRegistry::with_catalog(agents, vec![]);
        assert!(reg.get_agent("a1").is_some());
        assert!(reg.get_agent("nonexistent").is_none());
    }

    #[test]
    fn test_get_skill() {
        let skills = vec![make_skill("s1")];
        let reg = AgentRegistry::with_catalog(vec![], skills);
        assert!(reg.get_skill("s1").is_some());
        assert!(reg.get_skill("nonexistent").is_none());
    }

    #[test]
    fn test_validate_ok() {
        let skills = vec![make_skill("skill_a")];
        let agents = vec![make_agent("agent_a", vec!["skill_a"], vec![])];
        let reg = AgentRegistry::with_catalog(agents, skills);
        let result = reg.validate_catalog();
        assert!(result.ok);
        assert_eq!(result.agents_count, 1);
        assert_eq!(result.skills_count, 1);
        assert!(result.errors.is_empty());
    }

    #[test]
    fn test_validate_duplicate_agent() {
        let agents = vec![make_agent("dup", vec![], vec![]), make_agent("dup", vec![], vec![])];
        let reg = AgentRegistry::with_catalog(agents, vec![]);
        let result = reg.validate_catalog();
        assert!(!result.ok);
        assert!(result.errors.iter().any(|e| e.contains("dup")));
    }

    #[test]
    fn test_validate_unknown_skill() {
        let agents = vec![make_agent("a", vec!["missing-skill"], vec![])];
        let reg = AgentRegistry::with_catalog(agents, vec![]);
        let result = reg.validate_catalog();
        assert!(!result.ok);
        assert!(result.errors.iter().any(|e| e.contains("missing-skill")));
    }

    #[test]
    fn test_validate_unknown_handoff() {
        let agents = vec![make_agent("a", vec![], vec!["missing-agent"])];
        let reg = AgentRegistry::with_catalog(agents, vec![]);
        let result = reg.validate_catalog();
        assert!(!result.ok);
        assert!(result.errors.iter().any(|e| e.contains("missing-agent")));
    }

    #[test]
    fn test_validate_privacy_warning() {
        let mut agent = make_agent("a", vec![], vec![]);
        agent.permissions.network = true;
        let reg = AgentRegistry::with_catalog(vec![agent], vec![]);
        let result = reg.validate_catalog();
        assert!(result.ok);
        assert!(result.warnings.iter().any(|w| w.contains("network=true")));
    }

    #[test]
    fn test_validate_external_skill_needs_consent() {
        let mut skill = make_skill("ext");
        skill.privacy_level = "external".into();
        let reg = AgentRegistry::with_catalog(vec![], vec![skill]);
        let result = reg.validate_catalog();
        assert!(!result.ok);
        assert!(result.errors.iter().any(|e| e.contains("requires_consent")));
    }

    #[test]
    fn test_load_from_values() {
        let agent_value = serde_json::json!({
            "id": "test-agent",
            "name": "Test Agent",
            "role": "helper",
            "description": "A test",
            "privacy_level": "local",
            "default_model": "llama3.2",
            "system_prompt": "You are a test",
            "escalation_policy": "none",
        });
        let skill_value = serde_json::json!({
            "id": "test-skill",
            "name": "Test Skill",
            "category": "test",
            "description": "A skill",
            "privacy_level": "local",
        });
        let (agents, skills, errors) = AgentRegistry::load_from_values(vec![agent_value], vec![skill_value]);
        assert!(errors.is_empty());
        assert_eq!(agents.len(), 1);
        assert_eq!(skills.len(), 1);
        assert_eq!(agents[0].id, "test-agent");
    }

    #[test]
    fn test_load_from_values_with_errors() {
        let bad = serde_json::json!({"id": "bad-agent"}); // missing required fields
        let (_, _, errors) = AgentRegistry::load_from_values(vec![bad], vec![]);
        assert!(!errors.is_empty());
    }

    #[test]
    fn test_privacy_level() {
        let reg = AgentRegistry::new();
        assert_eq!(reg.privacy_level(), "local");
    }

    #[test]
    fn test_get_state() {
        let agents = vec![make_agent("a", vec![], vec![])];
        let reg = AgentRegistry::with_catalog(agents, vec![]);
        let state = reg.get_state();
        assert_eq!(
            state.get("agents_count").and_then(|v| v.as_u64()),
            Some(1)
        );
    }
}
