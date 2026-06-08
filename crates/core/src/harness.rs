use std::collections::HashMap;

use serde_json::Value;

/// BaseHarness trait — every service must implement this.
/// Mirrors `asterion_api.harness.BaseHarness` from Python.
pub trait BaseHarness: Send + Sync {
    fn privacy_level(&self) -> &str;

    fn execute(&self, payload: Option<HashMap<String, Value>>) -> Value;

    fn get_state(&self) -> HashMap<String, Value>;

    fn set_state(&self, state: HashMap<String, Value>);
}
