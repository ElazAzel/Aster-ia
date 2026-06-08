use crate::engine::InferenceEngine;
use crate::{InferenceRequest, InferenceMessage};
use asterion_core::schemas::BenchmarkRunResult;
use std::time::{Instant, Duration};

pub struct BenchmarkEngine {
    pub iterations: usize,
}

impl BenchmarkEngine {
    pub fn new(iterations: usize) -> Self {
        Self { iterations }
    }

    fn estimate_vram(&self, model: &str) -> f64 {
        // Delegate to core VRAM estimation helper
        asterion_core::benchmark::BenchmarkService::estimate_vram(model)
    }

    fn stddev(&self, samples: &[f64]) -> f64 {
        if samples.len() <= 1 {
            return 0.0;
        }
        let mean = samples.iter().sum::<f64>() / samples.len() as f64;
        let variance = samples.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / (samples.len() - 1) as f64;
        variance.sqrt()
    }

    pub async fn run_benchmark(
        &self,
        engine: &impl InferenceEngine,
        model: &str,
        prompt: &str,
    ) -> Result<BenchmarkRunResult, String> {
        let mut tps_samples = Vec::new();
        let mut ttft_samples = Vec::new();
        let mut total_samples = Vec::new();
        let mut last_error = None;

        for _ in 0..self.iterations {
            let req = InferenceRequest {
                model: model.to_string(),
                messages: vec![InferenceMessage {
                    role: "user".to_string(),
                    content: prompt.to_string(),
                }],
                max_tokens: Some(32),
                temperature: Some(0.0),
                stream: false,
            };

            let start = Instant::now();
            match engine.generate(req).await {
                Ok(resp) => {
                    let total_time = start.elapsed();
                    let total_ms = total_time.as_secs_f64() * 1000.0;
                    
                    // Estimate completion tokens based on response length or usage
                    let tokens = resp.usage.map(|u| u.completion_tokens).unwrap_or_else(|| {
                        // fallback calculation
                        (resp.text.split_whitespace().count() as u32).max(1)
                    });

                    // For non-streaming, estimate TTFT as 20% of total latency or a constant offset
                    let ttft_ms = total_ms * 0.2;
                    let tps = (tokens as f64) / total_time.as_secs_f64();

                    tps_samples.push(tps);
                    ttft_samples.push(ttft_ms);
                    total_samples.push(total_ms);
                }
                Err(err) => {
                    last_error = Some(err);
                }
            }
        }

        let vram_est = self.estimate_vram(model);

        if tps_samples.is_empty() {
            return Ok(BenchmarkRunResult {
                model: model.to_string(),
                runs: 0,
                avg_tokens_per_second: 0.0,
                avg_time_to_first_token_ms: 0.0,
                avg_total_time_ms: 0.0,
                min_tps: 0.0,
                max_tps: 0.0,
                stddev_tps: 0.0,
                vram_estimate_gb: vram_est,
                privacy_level: "local".to_string(),
                error: last_error.or_else(|| Some("No successful benchmark runs".to_string())),
                cached_at: None,
            });
        }

        let avg_tps = tps_samples.iter().sum::<f64>() / tps_samples.len() as f64;
        let avg_ttft = ttft_samples.iter().sum::<f64>() / ttft_samples.len() as f64;
        let avg_total = total_samples.iter().sum::<f64>() / total_samples.len() as f64;
        let min_tps = tps_samples.iter().cloned().fold(f64::MAX, f64::min);
        let max_tps = tps_samples.iter().cloned().fold(f64::MIN, f64::max);

        Ok(BenchmarkRunResult {
            model: model.to_string(),
            runs: tps_samples.len(),
            avg_tokens_per_second: (avg_tps * 100.0).round() / 100.0,
            avg_time_to_first_token_ms: (avg_ttft * 10.0).round() / 10.0,
            avg_total_time_ms: (avg_total * 10.0).round() / 10.0,
            min_tps: (min_tps * 100.0).round() / 100.0,
            max_tps: (max_tps * 100.0).round() / 100.0,
            stddev_tps: (self.stddev(&tps_samples) * 100.0).round() / 100.0,
            vram_estimate_gb: vram_est,
            privacy_level: "local".to_string(),
            error: None,
            cached_at: None,
        })
    }
}
