//! Privacy Analyzer — PII scanning + model/access risk classification.
//!
//! Mirrors `asterion_api.services.privacy_analyzer.PrivacyAnalyzer`.

use std::collections::HashMap;

use regex::Regex;
use serde_json::Value;

use crate::harness::BaseHarness;
use crate::schemas::{PrivacyItem, PrivacyReport};

lazy_static::lazy_static! {
    static ref EMAIL_RE: Regex = Regex::new(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+").unwrap();
    static ref PHONE_RE: Regex = Regex::new(r"(?:\+?\d{1,3}[\s\-.])?\(?\d{3}\)?[\s\-.‌​]?\d{3}[\s\-.‌​]?\d{4}").unwrap();
    static ref RU_PHONE_RE: Regex = Regex::new(r"(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}").unwrap();
    static ref ADDRESS_RE: Regex = {
        let patterns = [
            r"\bул\.\s+\w+", r"\bулица\s+\w+", r"\bпр\-кт\s+\w+",
            r"\bпроспект\s+\w+", r"\bпер\.\s+\w+", r"\bпереулок\s+\w+",
            r"\bг\.\s+\w+", r"\bгород\s+\w+", r"\bобл\.\s+\w+",
            r"\bобласть\s+\w+", r"\bhouse\b", r"\bapartment\b",
            r"\bstr\.\s+\w+", r"\bstreet\b", r"\bavenue\b",
        ];
        Regex::new(&patterns.join("|")).unwrap()
    };
}

pub struct PrivacyAnalyzer;

impl Default for PrivacyAnalyzer {
    fn default() -> Self {
        Self
    }
}

impl PrivacyAnalyzer {
    pub fn new() -> Self {
        Self
    }

    pub fn analyze(
        &self,
        model_type: &str,
        files_attached: bool,
        memory_enabled: bool,
        web_access: bool,
        prompt: Option<&str>,
    ) -> PrivacyReport {
        let mut items: Vec<PrivacyItem> = Vec::new();

        // Model type
        if model_type == "api" {
            items.push(PrivacyItem {
                what: "model".into(),
                destination: "external_api".into(),
                risk: "red".into(),
            });
        } else {
            items.push(PrivacyItem {
                what: "model".into(),
                destination: "local_ollama".into(),
                risk: "green".into(),
            });
        }

        // File attachments
        if files_attached {
            let destination = if model_type == "local" { "local_rag" } else { "external_api" };
            let risk = if model_type == "local" { "yellow" } else { "red" };
            items.push(PrivacyItem {
                what: "files".into(),
                destination: destination.into(),
                risk: risk.into(),
            });
        }

        // Memory access
        if memory_enabled {
            items.push(PrivacyItem {
                what: "memory".into(),
                destination: "encrypted_local_sqlcipher".into(),
                risk: "yellow".into(),
            });
        }

        // Web access
        if web_access {
            let risk = if model_type == "local" { "yellow" } else { "red" };
            items.push(PrivacyItem {
                what: "web_access".into(),
                destination: "local_searxng_to_public_web".into(),
                risk: risk.into(),
            });
        }

        // PII scanning
        if let Some(prompt_text) = prompt {
            let pii_risk = |is_api: bool| -> &str { if is_api { "red" } else { "yellow" } };

            if EMAIL_RE.is_match(prompt_text) {
                items.push(PrivacyItem {
                    what: "pii_email".into(),
                    destination: "prompt_data".into(),
                    risk: pii_risk(model_type == "api").into(),
                });
            }
            if PHONE_RE.is_match(prompt_text) || RU_PHONE_RE.is_match(prompt_text) {
                items.push(PrivacyItem {
                    what: "pii_phone".into(),
                    destination: "prompt_data".into(),
                    risk: pii_risk(model_type == "api").into(),
                });
            }
            if ADDRESS_RE.is_match(prompt_text) {
                items.push(PrivacyItem {
                    what: "pii_address".into(),
                    destination: "prompt_data".into(),
                    risk: pii_risk(model_type == "api").into(),
                });
            }
        }

        let level = if items.iter().any(|i| i.risk == "red") {
            "red"
        } else if items.iter().any(|i| i.risk == "yellow") {
            "yellow"
        } else {
            "green"
        };

        PrivacyReport {
            level: level.into(),
            items,
        }
    }
}

impl BaseHarness for PrivacyAnalyzer {
    fn privacy_level(&self) -> &str {
        "local"
    }

    fn execute(&self, payload: Option<HashMap<String, Value>>) -> Value {
        let p = payload.unwrap_or_default();
        let report = self.analyze(
            p.get("model_type").and_then(|v| v.as_str()).unwrap_or("local"),
            p.get("files_attached").and_then(|v| v.as_bool()).unwrap_or(false),
            p.get("memory_enabled").and_then(|v| v.as_bool()).unwrap_or(false),
            p.get("web_access").and_then(|v| v.as_bool()).unwrap_or(false),
            p.get("prompt").and_then(|v| v.as_str()),
        );
        serde_json::to_value(report).unwrap_or_default()
    }

    fn get_state(&self) -> HashMap<String, Value> {
        let mut state = HashMap::new();
        state.insert("rules".into(), serde_json::json!(["model_type", "files_attached", "memory_enabled", "web_access", "prompt"]));
        state
    }

    fn set_state(&self, _state: HashMap<String, Value>) {}
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_local_is_green() {
        let pa = PrivacyAnalyzer::new();
        let report = pa.analyze("local", false, false, false, None);
        assert_eq!(report.level, "green");
    }

    #[test]
    fn test_api_is_red() {
        let pa = PrivacyAnalyzer::new();
        let report = pa.analyze("api", false, false, false, None);
        assert_eq!(report.level, "red");
    }

    #[test]
    fn test_api_files_web_is_red() {
        let pa = PrivacyAnalyzer::new();
        let report = pa.analyze("api", true, false, true, None);
        assert_eq!(report.level, "red");
    }

    #[test]
    fn test_memory_is_yellow() {
        let pa = PrivacyAnalyzer::new();
        let report = pa.analyze("local", false, true, false, None);
        assert_eq!(report.level, "yellow");
    }

    #[test]
    fn test_pii_email_detected() {
        let pa = PrivacyAnalyzer::new();
        let report = pa.analyze("local", false, false, false, Some("email me at test@example.com"));
        let has_email = report.items.iter().any(|i| i.what == "pii_email");
        assert!(has_email);
    }

    #[test]
    fn test_pii_phone_detected() {
        let pa = PrivacyAnalyzer::new();
        let report = pa.analyze("local", false, false, false, Some("+7 (999) 123-45-67"));
        let has_phone = report.items.iter().any(|i| i.what == "pii_phone");
        assert!(has_phone);
    }

    #[test]
    fn test_pii_address_detected() {
        let pa = PrivacyAnalyzer::new();
        let report = pa.analyze("local", false, false, false, Some("ул. Ленина, дом 10"));
        let has_addr = report.items.iter().any(|i| i.what == "pii_address");
        assert!(has_addr);
    }

    #[test]
    fn test_no_pii_clean_text() {
        let pa = PrivacyAnalyzer::new();
        let report = pa.analyze("local", false, false, false, Some("hello world"));
        let pii_items: Vec<_> = report.items.iter().filter(|i| i.what.starts_with("pii_")).collect();
        assert!(pii_items.is_empty());
    }

    #[test]
    fn test_execute_via_harness() {
        use std::collections::HashMap;
        let pa = PrivacyAnalyzer::new();
        let mut payload = HashMap::new();
        payload.insert("model_type".into(), Value::String("api".into()));
        let result = pa.execute(Some(payload));
        let report: PrivacyReport = serde_json::from_value(result).unwrap();
        assert_eq!(report.level, "red");
    }

    #[test]
    fn test_privacy_level() {
        let pa = PrivacyAnalyzer::new();
        assert_eq!(pa.privacy_level(), "local");
    }
}
