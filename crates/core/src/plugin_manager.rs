use std::collections::HashMap;

use serde_json::Value;

use crate::harness::BaseHarness;
use crate::schemas::PluginManifest;

const TRUST_LEVELS: &[&str] = &["verified", "local-only", "network", "file", "shell", "danger"];

pub struct PluginManager {
    trust_levels: Vec<String>,
}

impl Default for PluginManager {
    fn default() -> Self {
        Self {
            trust_levels: TRUST_LEVELS.iter().map(|s| s.to_string()).collect(),
        }
    }
}

impl PluginManager {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn process_manifest(
        &self,
        name: &str,
        trust_level: &str,
        is_signed: bool,
        is_signature_valid: bool,
        path: &str,
        description: Option<String>,
    ) -> Option<PluginManifest> {
        let trust_level = self.compute_trust_level(trust_level, is_signed, is_signature_valid);
        if trust_level == "danger" {
            None
        } else {
            Some(PluginManifest {
                name: name.into(),
                trust_level,
                path: path.into(),
                description,
            })
        }
    }

    pub fn compute_trust_level(&self, trust_level: &str, is_signed: bool, is_signature_valid: bool) -> String {
        let mut tl = trust_level.to_lowercase();

        if tl == "verified" && !(is_signed && is_signature_valid) {
            tl = "danger".into();
        }

        if !self.trust_levels.contains(&tl) {
            tl = "danger".into();
        }

        if !is_signed {
            if matches!(tl.as_str(), "shell" | "network" | "file" | "danger") {
                tl = "danger".into();
            } else {
                tl = "local-only".into();
            }
        }

        tl
    }

    pub fn parse_from_value(&self, manifest_value: &Value, signed: bool, signature_valid: bool) -> Option<PluginManifest> {
        let name = manifest_value
            .get("name")
            .and_then(|v| v.as_str())
            .unwrap_or("unknown");

        let trust_level = manifest_value
            .get("trust_level")
            .and_then(|v| v.as_str())
            .unwrap_or("local-only");

        let description = manifest_value
            .get("description")
            .and_then(|v| v.as_str())
            .map(|s| s.to_string());

        self.process_manifest(name, trust_level, signed, signature_valid, "", description)
    }
}

impl BaseHarness for PluginManager {
    fn privacy_level(&self) -> &str {
        "local"
    }

    fn execute(&self, _payload: Option<HashMap<String, Value>>) -> Value {
        Value::Null
    }

    fn get_state(&self) -> HashMap<String, Value> {
        let mut state = HashMap::new();
        state.insert("trust_levels".into(), Value::Array(
            self.trust_levels.iter().map(|s| Value::String(s.clone())).collect()
        ));
        state
    }

    fn set_state(&self, _state: HashMap<String, Value>) {}
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_verified_signed_valid_passes() {
        let pm = PluginManager::new();
        let m = pm.process_manifest("test", "verified", true, true, "/path", None);
        assert!(m.is_some());
        assert_eq!(m.unwrap().trust_level, "verified");
    }

    #[test]
    fn test_verified_unsigned_is_danger() {
        let pm = PluginManager::new();
        let m = pm.process_manifest("test", "verified", false, false, "/path", None);
        assert!(m.is_none());
    }

    #[test]
    fn test_verified_signed_invalid_is_danger() {
        let pm = PluginManager::new();
        let m = pm.process_manifest("test", "verified", true, false, "/path", None);
        assert!(m.is_none());
    }

    #[test]
    fn test_unsigned_shell_downgraded_to_danger() {
        let pm = PluginManager::new();
        let tl = pm.compute_trust_level("shell", false, false);
        assert_eq!(tl, "danger");
    }

    #[test]
    fn test_unsigned_local_only_stays_local_only() {
        let pm = PluginManager::new();
        let tl = pm.compute_trust_level("local-only", false, false);
        assert_eq!(tl, "local-only");
    }

    #[test]
    fn test_unknown_trust_level_danger() {
        let pm = PluginManager::new();
        let tl = pm.compute_trust_level("super-admin", false, false);
        assert_eq!(tl, "danger");
    }

    #[test]
    fn test_parse_from_value_minimal() {
        let pm = PluginManager::new();
        let v = serde_json::json!({"name": "my-plugin"});
        let m = pm.parse_from_value(&v, false, false);
        assert!(m.is_some());
        assert_eq!(m.unwrap().trust_level, "local-only");
    }

    #[test]
    fn test_privacy_level() {
        let pm = PluginManager::new();
        assert_eq!(pm.privacy_level(), "local");
    }

    #[test]
    fn test_get_state() {
        let pm = PluginManager::new();
        let state = pm.get_state();
        assert!(state.contains_key("trust_levels"));
    }

    #[test]
    fn test_signed_network_plugin_passes() {
        let pm = PluginManager::new();
        let m = pm.process_manifest("net-plugin", "network", true, true, "/path", Some("A network plugin".into()));
        let m = m.unwrap();
        assert_eq!(m.trust_level, "network");
        assert_eq!(m.description.unwrap(), "A network plugin");
    }
}
