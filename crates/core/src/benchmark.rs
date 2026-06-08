use std::collections::HashMap;
use std::sync::Mutex;
use std::time::{Duration, Instant};

use serde_json::Value;

use crate::harness::BaseHarness;
use crate::schemas::BenchmarkRunResult;

const CACHE_TTL: Duration = Duration::from_secs(3600);

static VRAM_ESTIMATES: &[(&str, f64)] = &[
    ("phi3:mini", 1.8),
    ("phi3", 2.4),
    ("llama3.2:1b", 1.3),
    ("llama3.2:3b", 2.0),
    ("llama3.2", 4.7),
    ("llama3.1:8b", 4.9),
    ("mistral:7b", 4.1),
    ("mistral", 4.1),
    ("gemma2:2b", 1.6),
    ("gemma2:9b", 5.5),
    ("qwen2.5:0.5b", 0.4),
    ("qwen2.5:1.5b", 1.0),
    ("qwen2.5:3b", 1.9),
    ("qwen2.5:7b", 4.4),
    ("qwen2.5:14b", 8.9),
    ("qwen2.5:32b", 19.0),
    ("codellama:7b", 3.8),
    ("deepseek-coder-v2", 8.9),
    ("nomic-embed-text", 0.3),
    ("llava:13b", 8.0),
];

pub struct BenchmarkService {
    privacy_level: String,
    cache: Mutex<HashMap<String, CachedBenchmark>>,
}

struct CachedBenchmark {
    result: BenchmarkRunResult,
    ts: Instant,
}

impl Default for BenchmarkService {
    fn default() -> Self {
        Self {
            privacy_level: "local".into(),
            cache: Mutex::new(HashMap::new()),
        }
    }
}

impl BenchmarkService {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn estimate_vram(model: &str) -> f64 {
        let lower = model.to_lowercase();
        for &(key, vram) in VRAM_ESTIMATES {
            if lower.starts_with(key) {
                return vram;
            }
        }
        4.0
    }

    pub fn get_cached(&self, model: &str) -> Option<BenchmarkRunResult> {
        let mut cache = self.cache.lock().unwrap();
        let entry = cache.get(model)?;
        if entry.ts.elapsed() > CACHE_TTL {
            cache.remove(model);
            return None;
        }
        Some(entry.result.clone())
    }

    pub fn clear_cache(&self) {
        self.cache.lock().unwrap().clear();
    }

    fn stddev(samples: &[f64]) -> f64 {
        if samples.len() <= 1 {
            return 0.0;
        }
        let mean = samples.iter().sum::<f64>() / samples.len() as f64;
        let variance = samples.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / (samples.len() - 1) as f64;
        variance.sqrt()
    }

    pub fn compute_result(
        &self,
        model: &str,
        tps_samples: &[f64],
        ttft_samples: &[f64],
        total_samples: &[f64],
        last_error: Option<String>,
    ) -> BenchmarkRunResult {
        let vram_est = Self::estimate_vram(model);

        let result = if tps_samples.is_empty() {
            BenchmarkRunResult {
                model: model.into(),
                runs: 0,
                avg_tokens_per_second: 0.0,
                avg_time_to_first_token_ms: 0.0,
                avg_total_time_ms: 0.0,
                min_tps: 0.0,
                max_tps: 0.0,
                stddev_tps: 0.0,
                vram_estimate_gb: vram_est,
                privacy_level: self.privacy_level.clone(),
                error: last_error,
                cached_at: None,
            }
        } else {
            let avg_tps = tps_samples.iter().sum::<f64>() / tps_samples.len() as f64;
            let avg_ttft = ttft_samples.iter().sum::<f64>() / ttft_samples.len() as f64;
            let avg_total = total_samples.iter().sum::<f64>() / total_samples.len() as f64;
            let min_tps = tps_samples.iter().cloned().fold(f64::MAX, f64::min);
            let max_tps = tps_samples.iter().cloned().fold(f64::MIN, f64::max);

            BenchmarkRunResult {
                model: model.into(),
                runs: tps_samples.len(),
                avg_tokens_per_second: (avg_tps * 100.0).round() / 100.0,
                avg_time_to_first_token_ms: (avg_ttft * 10.0).round() / 10.0,
                avg_total_time_ms: (avg_total * 10.0).round() / 10.0,
                min_tps: (min_tps * 100.0).round() / 100.0,
                max_tps: (max_tps * 100.0).round() / 100.0,
                stddev_tps: (Self::stddev(tps_samples) * 100.0).round() / 100.0,
                vram_estimate_gb: vram_est,
                privacy_level: self.privacy_level.clone(),
                error: None,
                cached_at: None,
            }
        };

        self.cache.lock().unwrap().insert(
            model.into(),
            CachedBenchmark {
                result: result.clone(),
                ts: Instant::now(),
            },
        );
        result
    }
}

impl BaseHarness for BenchmarkService {
    fn privacy_level(&self) -> &str {
        &self.privacy_level
    }

    fn execute(&self, _payload: Option<HashMap<String, Value>>) -> Value {
        Value::Null
    }

    fn get_state(&self) -> HashMap<String, Value> {
        let cache = self.cache.lock().unwrap();
        let mut state = HashMap::new();
        state.insert("cache_entries".into(), Value::Number(cache.len().into()));
        state.insert(
            "cached_models".into(),
            Value::Array(cache.keys().map(|k| Value::String(k.clone())).collect()),
        );
        state
    }

    fn set_state(&self, state: HashMap<String, Value>) {
        if state.contains_key("clear_cache") {
            self.cache.lock().unwrap().clear();
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_estimate_vram_known() {
        assert!((BenchmarkService::estimate_vram("llama3.2:3b") - 2.0).abs() < 0.01);
        assert!((BenchmarkService::estimate_vram("phi3:mini") - 1.8).abs() < 0.01);
    }

    #[test]
    fn test_estimate_vram_unknown_returns_default() {
        assert!((BenchmarkService::estimate_vram("unknown-model") - 4.0).abs() < 0.01);
    }

    #[test]
    fn test_estimate_vram_case_insensitive() {
        assert!((BenchmarkService::estimate_vram("LLAMA3.2:3B") - 2.0).abs() < 0.01);
    }

    #[test]
    fn test_compute_result_with_samples() {
        let svc = BenchmarkService::new();
        let result = svc.compute_result(
            "llama3.2:3b",
            &[10.0, 12.0, 11.0],
            &[200.0, 210.0, 205.0],
            &[3000.0, 3100.0, 3050.0],
            None,
        );
        assert_eq!(result.model, "llama3.2:3b");
        assert_eq!(result.runs, 3);
        assert!((result.avg_tokens_per_second - 11.0).abs() < 0.01);
        assert!((result.min_tps - 10.0).abs() < 0.01);
        assert!((result.max_tps - 12.0).abs() < 0.01);
        assert!((result.vram_estimate_gb - 2.0).abs() < 0.01);
        assert!(result.error.is_none());
        assert!(result.cached_at.is_none());
    }

    #[test]
    fn test_compute_result_no_samples() {
        let svc = BenchmarkService::new();
        let result = svc.compute_result("empty", &[], &[], &[], Some("timeout".into()));
        assert_eq!(result.runs, 0);
        assert_eq!(result.error, Some("timeout".into()));
    }

    #[test]
    fn test_cache_hit() {
        let svc = BenchmarkService::new();
        svc.compute_result("phi3:mini", &[15.0], &[100.0], &[2000.0], None);
        let cached = svc.get_cached("phi3:mini");
        assert!(cached.is_some());
        assert!((cached.unwrap().vram_estimate_gb - 1.8).abs() < 0.01);
    }

    #[test]
    fn test_cache_miss_nonexistent() {
        let svc = BenchmarkService::new();
        assert!(svc.get_cached("no-such-model").is_none());
    }

    #[test]
    fn test_clear_cache() {
        let svc = BenchmarkService::new();
        svc.compute_result("phi3", &[15.0], &[100.0], &[2000.0], None);
        svc.clear_cache();
        assert!(svc.get_cached("phi3").is_none());
    }

    #[test]
    fn test_privacy_level() {
        let svc = BenchmarkService::new();
        assert_eq!(svc.privacy_level(), "local");
    }

    #[test]
    fn test_stddev() {
        let std = BenchmarkService::stddev(&[10.0, 12.0, 11.0]);
        assert!((std - 1.0).abs() < 0.01);
    }

    #[test]
    fn test_stddev_single_sample() {
        let std = BenchmarkService::stddev(&[42.0]);
        assert!((std - 0.0).abs() < 0.01);
    }

    #[test]
    fn test_get_state() {
        let svc = BenchmarkService::new();
        svc.compute_result("test", &[1.0], &[1.0], &[1.0], None);
        let state = svc.get_state();
        assert_eq!(
            state.get("cache_entries").and_then(|v| v.as_u64()),
            Some(1)
        );
    }
}
