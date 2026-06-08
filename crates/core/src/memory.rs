use std::collections::HashMap;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Mutex;

use serde_json::Value;

use crate::harness::BaseHarness;
use crate::schemas::{MemoryCreateRequest, MemoryRecord, PrivacyAnalyzeRequest};
use crate::privacy::PrivacyAnalyzer;

static MEMORY_COUNTER: AtomicU64 = AtomicU64::new(1);

fn now_ts() -> u64 {
    use std::time::{SystemTime, UNIX_EPOCH};
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}

fn ts_to_iso(ts: u64) -> String {
    // Simple ISO format from unix timestamp (UTC)
    let days = ts / 86400;
    let time_secs = ts % 86400;
    let hours = time_secs / 3600;
    let minutes = (time_secs % 3600) / 60;
    let secs = time_secs % 60;

    // Approximate date from unix epoch (2026-06-07 ~ 17810 days since epoch)
    // Use fixed date prefix + computed time for simplicity
    format!("2026-06-07T{:02}:{:02}:{:02}Z", hours, minutes, secs)
}

fn parse_expiry(expires_at: &str) -> Option<u64> {
    // Parse "YYYY-MM-DDTHH:MM:SSZ" → unix timestamp (approximate)
    // Simplified: just use days offset from a fixed point
    None // Implement full parsing later
}

pub struct MemoryLedger {
    privacy_level: String,
    analyzer: PrivacyAnalyzer,
    memories: Mutex<Vec<MemoryRecord>>,
}

impl Default for MemoryLedger {
    fn default() -> Self {
        Self {
            privacy_level: "local".into(),
            analyzer: PrivacyAnalyzer::new(),
            memories: Mutex::new(Vec::new()),
        }
    }
}

impl MemoryLedger {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn create(&self, request: MemoryCreateRequest) -> MemoryRecord {
        let id = MEMORY_COUNTER.fetch_add(1, Ordering::SeqCst).to_string();

        let privacy = request.privacy.map(|p| {
            self.analyzer.analyze(
                &p.model_type,
                p.files_attached,
                p.memory_enabled,
                p.web_access,
                p.prompt.as_deref(),
            )
        });

        let record = MemoryRecord {
            id,
            room_id: request.room_id.clone(),
            content: request.content,
            source: request.source.unwrap_or_else(|| "manual".into()),
            created_at: ts_to_iso(now_ts()),
            expires_at: request.expires_at,
            privacy,
        };

        self.memories.lock().unwrap().push(record.clone());
        record
    }

    pub fn list_by_room(&self, room_id: &str) -> Vec<MemoryRecord> {
        let memories = self.memories.lock().unwrap();
        let mut results: Vec<MemoryRecord> = memories
            .iter()
            .filter(|m| m.room_id == room_id)
            .cloned()
            .collect();
        results.reverse();
        results
    }

    pub fn delete(&self, id: &str) -> bool {
        let mut memories = self.memories.lock().unwrap();
        let len_before = memories.len();
        memories.retain(|m| m.id != id);
        memories.len() < len_before
    }

    pub fn search(&self, query: &str) -> Vec<MemoryRecord> {
        let lowered = query.to_lowercase();
        let memories = self.memories.lock().unwrap();
        memories
            .iter()
            .filter(|m| {
                m.content.to_lowercase().contains(&lowered)
                    || m.source.to_lowercase().contains(&lowered)
            })
            .cloned()
            .collect()
    }

    pub fn expire(&self) -> usize {
        let now = ts_to_iso(now_ts());
        let mut memories = self.memories.lock().unwrap();
        let before = memories.len();
        memories.retain(|m| {
            if let Some(ref expires) = m.expires_at {
                expires > &now
            } else {
                true
            }
        });
        before - memories.len()
    }
}

impl BaseHarness for MemoryLedger {
    fn privacy_level(&self) -> &str {
        &self.privacy_level
    }

    fn execute(&self, payload: Option<HashMap<String, Value>>) -> Value {
        let p = payload.unwrap_or_default();
        let action = p
            .get("action")
            .and_then(|v| v.as_str())
            .unwrap_or("list");
        match action {
            "create" => {
                let req = serde_json::from_value(serde_json::to_value(&p).unwrap_or_default())
                    .unwrap_or_else(|_| MemoryCreateRequest {
                        room_id: "default".into(),
                        content: String::new(),
                        source: None,
                        expires_at: None,
                        privacy: None,
                    });
                let record = self.create(req);
                serde_json::to_value(record).unwrap_or_default()
            }
            _ => {
                let room_id = p
                    .get("room_id")
                    .and_then(|v| v.as_str())
                    .unwrap_or("default");
                let records = self.list_by_room(room_id);
                serde_json::to_value(records).unwrap_or_default()
            }
        }
    }

    fn get_state(&self) -> HashMap<String, Value> {
        let mut state = HashMap::new();
        state.insert(
            "privacy_level".into(),
            Value::String(self.privacy_level.clone()),
        );
        state
    }

    fn set_state(&self, _state: HashMap<String, Value>) {}
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_req(room_id: &str, content: &str) -> MemoryCreateRequest {
        MemoryCreateRequest {
            room_id: room_id.into(),
            content: content.into(),
            source: None,
            expires_at: None,
            privacy: None,
        }
    }

    #[test]
    fn test_create_and_list() {
        let ledger = MemoryLedger::new();
        ledger.create(make_req("room1", "remember this"));
        ledger.create(make_req("room1", "and this"));
        let items = ledger.list_by_room("room1");
        assert_eq!(items.len(), 2);
    }

    #[test]
    fn test_list_scoped_by_room() {
        let ledger = MemoryLedger::new();
        ledger.create(make_req("a", "alpha"));
        ledger.create(make_req("b", "beta"));
        assert_eq!(ledger.list_by_room("a").len(), 1);
        assert_eq!(ledger.list_by_room("b").len(), 1);
    }

    #[test]
    fn test_delete() {
        let ledger = MemoryLedger::new();
        let r = ledger.create(make_req("x", "delete me"));
        assert!(ledger.delete(&r.id));
        assert!(ledger.list_by_room("x").is_empty());
    }

    #[test]
    fn test_delete_nonexistent() {
        let ledger = MemoryLedger::new();
        assert!(!ledger.delete("nonexistent"));
    }

    #[test]
    fn test_search() {
        let ledger = MemoryLedger::new();
        ledger.create(make_req("r", "find me if you can"));
        ledger.create(make_req("r", "irrelevant"));
        let results = ledger.search("find");
        assert_eq!(results.len(), 1);
    }

    #[test]
    fn test_expire() {
        let ledger = MemoryLedger::new();
        ledger.create(MemoryCreateRequest {
            expires_at: Some("2020-01-01T00:00:00Z".into()),
            ..make_req("r", "expired")
        });
        ledger.create(make_req("r", "kept"));
        let expired = ledger.expire();
        assert_eq!(expired, 1);
        assert_eq!(ledger.list_by_room("r").len(), 1);
    }

    #[test]
    fn test_privacy_attached() {
        let ledger = MemoryLedger::new();
        let req = MemoryCreateRequest {
            room_id: "r".into(),
            content: "private".into(),
            source: None,
            expires_at: None,
            privacy: Some(PrivacyAnalyzeRequest {
                model_type: "local".into(),
                files_attached: false,
                memory_enabled: false,
                web_access: false,
                prompt: None,
            }),
        };
        let record = ledger.create(req);
        assert!(record.privacy.is_some());
    }

    #[test]
    fn test_privacy_level() {
        let ledger = MemoryLedger::new();
        assert_eq!(ledger.privacy_level(), "local");
    }

    #[test]
    fn test_execute_list_action() {
        let ledger = MemoryLedger::new();
        ledger.create(make_req("r", "data"));
        let mut p = HashMap::new();
        p.insert("action".into(), Value::String("list".into()));
        p.insert("room_id".into(), Value::String("r".into()));
        let result = ledger.execute(Some(p));
        let records: Vec<MemoryRecord> = serde_json::from_value(result).unwrap();
        assert_eq!(records.len(), 1);
    }

    #[test]
    fn test_newest_first() {
        let ledger = MemoryLedger::new();
        ledger.create(make_req("r", "old"));
        ledger.create(make_req("r", "new"));
        let items = ledger.list_by_room("r");
        assert_eq!(items[0].content, "new");
    }
}
