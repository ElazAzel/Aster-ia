use std::collections::{HashMap, HashSet};

use lazy_static::lazy_static;
use serde_json::Value;

use crate::harness::BaseHarness;

const RECIPE_KEYS: &[&str] = &[
    "workflow", "client_id", "checkpoint", "width", "height", "steps", "cfg",
    "sampler_name", "scheduler", "seed", "negative_prompt", "batch_size", "filename_prefix",
];

const LOOPBACK_HOSTS: &[&str] = &["127.0.0.1", "localhost", "::1"];
const BLOCKED_CLASS_MARKERS: &[&str] = &["download", "http", "url"];
const BLOCKED_URI_PREFIXES: &[&str] = &["http://", "https://", "ftp://", "s3://", "file://"];

struct RecipePreset {
    id: &'static str,
    title: &'static str,
    recipe: HashMap<String, Value>,
}

lazy_static! {
    static ref RECIPE_PRESETS: Vec<RecipePreset> = vec![
        RecipePreset {
            id: "sdxl-square",
            title: "SDXL Square",
            recipe: {
                let mut m = HashMap::new();
                m.insert("width".into(), serde_json::json!(1024));
                m.insert("height".into(), serde_json::json!(1024));
                m.insert("steps".into(), serde_json::json!(20));
                m.insert("cfg".into(), serde_json::json!(7.0));
                m.insert("sampler_name".into(), serde_json::json!("euler"));
                m.insert("scheduler".into(), serde_json::json!("normal"));
                m.insert("filename_prefix".into(), serde_json::json!("asterion-square"));
                m
            },
        },
        RecipePreset {
            id: "portrait-fast",
            title: "Portrait Fast",
            recipe: {
                let mut m = HashMap::new();
                m.insert("width".into(), serde_json::json!(832));
                m.insert("height".into(), serde_json::json!(1216));
                m.insert("steps".into(), serde_json::json!(16));
                m.insert("cfg".into(), serde_json::json!(6.5));
                m.insert("sampler_name".into(), serde_json::json!("euler"));
                m.insert("scheduler".into(), serde_json::json!("normal"));
                m.insert("negative_prompt".into(), serde_json::json!("low quality, blurry, distorted anatomy, extra fingers"));
                m.insert("filename_prefix".into(), serde_json::json!("asterion-portrait"));
                m
            },
        },
        RecipePreset {
            id: "wide-concept",
            title: "Wide Concept",
            recipe: {
                let mut m = HashMap::new();
                m.insert("width".into(), serde_json::json!(1344));
                m.insert("height".into(), serde_json::json!(768));
                m.insert("steps".into(), serde_json::json!(24));
                m.insert("cfg".into(), serde_json::json!(7.5));
                m.insert("sampler_name".into(), serde_json::json!("euler"));
                m.insert("scheduler".into(), serde_json::json!("normal"));
                m.insert("filename_prefix".into(), serde_json::json!("asterion-wide"));
                m
            },
        },
        RecipePreset {
            id: "ui-mockup",
            title: "UI Mockup",
            recipe: {
                let mut m = HashMap::new();
                m.insert("width".into(), serde_json::json!(1152));
                m.insert("height".into(), serde_json::json!(768));
                m.insert("steps".into(), serde_json::json!(22));
                m.insert("cfg".into(), serde_json::json!(6.0));
                m.insert("sampler_name".into(), serde_json::json!("euler"));
                m.insert("scheduler".into(), serde_json::json!("normal"));
                m.insert("negative_prompt".into(), serde_json::json!("messy text, illegible UI, distorted interface, low contrast"));
                m.insert("filename_prefix".into(), serde_json::json!("asterion-ui"));
                m
            },
        },
    ];
}

fn is_loopback_host(hostname: &str) -> bool {
    LOOPBACK_HOSTS.iter().any(|h| *h == hostname)
}

fn is_absolute_windows_path(s: &str) -> bool {
    let bytes = s.as_bytes();
    bytes.len() >= 3
        && bytes[0].is_ascii_alphabetic()
        && bytes[1] == b':'
        && (bytes[2] == b'\\' || bytes[2] == b'/')
}

fn recipe_int(recipe: &HashMap<String, Value>, key: &str, default: i64) -> i64 {
    recipe
        .get(key)
        .and_then(|v| v.as_i64())
        .unwrap_or(default)
}

fn recipe_float(recipe: &HashMap<String, Value>, key: &str, default: f64) -> f64 {
    recipe
        .get(key)
        .and_then(|v| v.as_f64())
        .unwrap_or(default)
}

fn recipe_string(recipe: &HashMap<String, Value>, key: &str, default: &str) -> String {
    recipe
        .get(key)
        .and_then(|v| v.as_str())
        .filter(|s| !s.is_empty())
        .map(|s| s.to_string())
        .unwrap_or_else(|| default.to_string())
}

fn default_workflow(prompt: &str, recipe: &HashMap<String, Value>) -> HashMap<String, Value> {
    let checkpoint = recipe_string(recipe, "checkpoint", "model.safetensors");
    let negative = recipe_string(recipe, "negative_prompt", "");
    let filename = recipe_string(recipe, "filename_prefix", "asterion");

    let mut wf = HashMap::new();
    wf.insert("1".into(), serde_json::json!({
        "class_type": "CheckpointLoaderSimple",
        "inputs": {"ckpt_name": checkpoint}
    }));
    wf.insert("2".into(), serde_json::json!({
        "class_type": "CLIPTextEncode",
        "inputs": {"text": prompt, "clip": ["1", 1]}
    }));
    wf.insert("3".into(), serde_json::json!({
        "class_type": "CLIPTextEncode",
        "inputs": {"text": negative, "clip": ["1", 1]}
    }));
    wf.insert("4".into(), serde_json::json!({
        "class_type": "EmptyLatentImage",
        "inputs": {
            "width": recipe_int(recipe, "width", 1024),
            "height": recipe_int(recipe, "height", 1024),
            "batch_size": recipe_int(recipe, "batch_size", 1),
        }
    }));
    wf.insert("5".into(), serde_json::json!({
        "class_type": "KSampler",
        "inputs": {
            "seed": recipe_int(recipe, "seed", 1),
            "steps": recipe_int(recipe, "steps", 20),
            "cfg": recipe_float(recipe, "cfg", 7.0),
            "sampler_name": recipe_string(recipe, "sampler_name", "euler"),
            "scheduler": recipe_string(recipe, "scheduler", "normal"),
            "denoise": 1.0,
            "model": ["1", 0],
            "positive": ["2", 0],
            "negative": ["3", 0],
            "latent_image": ["4", 0],
        }
    }));
    wf.insert("6".into(), serde_json::json!({
        "class_type": "VAEDecode",
        "inputs": {"samples": ["5", 0], "vae": ["1", 2]}
    }));
    wf.insert("7".into(), serde_json::json!({
        "class_type": "SaveImage",
        "inputs": {"images": ["6", 0], "filename_prefix": filename}
    }));
    wf
}

struct ValidationContext {
    errors: Vec<String>,
    warnings: Vec<String>,
    node_ids: HashSet<String>,
}

fn validate_value(value: &Value, node_ids: &HashSet<String>, path: &str, ctx: &mut ValidationContext) {
    match value {
        Value::String(s) => {
            let lowered = s.to_lowercase();
            if s.len() > 16_000 {
                ctx.errors.push(format!("{path}: string value exceeds 16000 characters"));
            }
            if BLOCKED_URI_PREFIXES.iter().any(|p| lowered.starts_with(p)) {
                ctx.errors.push(format!("{path}: external URI values are not allowed in local recipes"));
            }
            if s.contains("../") || s.contains("..\\") || s.starts_with('/') || s.starts_with('\\') {
                ctx.errors.push(format!("{path}: path traversal or absolute paths are not allowed in recipes"));
            }
            if is_absolute_windows_path(s) {
                ctx.errors.push(format!("{path}: absolute Windows paths are not allowed in recipes"));
            }
        }
        Value::Number(_) | Value::Bool(_) | Value::Null => {}
        Value::Array(arr) => {
            if arr.len() == 2 {
                if let (Some(a), Some(b)) = (arr[0].as_str(), arr[1].as_i64()) {
                    if !node_ids.contains(a) {
                        ctx.errors.push(format!("{path}: references missing node '{a}'"));
                    }
                    if b < 0 {
                        ctx.errors.push(format!("{path}: output index must be non-negative"));
                    }
                    return;
                }
            }
            for (i, item) in arr.iter().enumerate() {
                validate_value(item, node_ids, &format!("{path}[{i}]"), ctx);
            }
        }
        Value::Object(map) => {
            for (k, v) in map {
                validate_value(v, node_ids, &format!("{path}.{k}"), ctx);
            }
        }
    }
}

pub struct ComfyUIService {
    privacy_level: String,
    base_url: String,
}

impl Default for ComfyUIService {
    fn default() -> Self {
        Self {
            privacy_level: "local".into(),
            base_url: "http://127.0.0.1:8188".into(),
        }
    }
}

impl ComfyUIService {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn normalize_base_url(&self, url: &str) -> Result<String, String> {
        let url = url.trim_end_matches('/').to_string();
        if !url.starts_with("http://") && !url.starts_with("https://") {
            return Err("ComfyUI base_url must use http or https".into());
        }
        // Simple hostname check
        let after_scheme = url
            .trim_start_matches("http://")
            .trim_start_matches("https://");
        let hostname = after_scheme.split(':').next().unwrap_or("");

        if !is_loopback_host(hostname) {
            return Err("ComfyUI base_url must point to localhost or 127.0.0.1".into());
        }
        Ok(url)
    }

    pub fn get_recipe_preset(&self, preset_id: &str) -> Option<&RecipePreset> {
        RECIPE_PRESETS.iter().find(|p| p.id == preset_id)
    }

    pub fn list_recipe_presets(&self) -> Vec<HashMap<String, Value>> {
        RECIPE_PRESETS
            .iter()
            .map(|preset| {
                let mut map = HashMap::new();
                map.insert("id".into(), Value::String(preset.id.into()));
                map.insert("title".into(), Value::String(preset.title.into()));
                let recipe_val: HashMap<String, Value> = preset.recipe.iter().map(|(k, v)| (k.clone(), v.clone())).collect();
                map.insert("recipe".into(), Value::Object(recipe_val.into_iter().collect()));
                map.insert(
                    "privacy_level".into(),
                    Value::String(self.privacy_level.clone()),
                );
                map
            })
            .collect()
    }

    pub fn build_recipe(
        &self,
        preset_id: Option<&str>,
        overrides: Option<&HashMap<String, Value>>,
    ) -> HashMap<String, Value> {
        let mut recipe = HashMap::new();
        if let Some(pid) = preset_id {
            if let Some(preset) = self.get_recipe_preset(pid) {
                for (k, v) in &preset.recipe {
                    recipe.insert(k.to_string(), v.clone());
                }
            }
        }
        if let Some(over) = overrides {
            for (k, v) in over {
                recipe.insert(k.clone(), v.clone());
            }
        }
        recipe
    }

    pub fn validate_recipe(
        &self,
        recipe: Option<&HashMap<String, Value>>,
        prompt: &str,
    ) -> HashMap<String, Value> {
        let mut ctx = ValidationContext {
            errors: Vec::new(),
            warnings: Vec::new(),
            node_ids: HashSet::new(),
        };

        let recipe = match recipe {
            Some(r) => r,
            None => {
                ctx.errors.push("recipe must be a JSON object".into());
                return validation_response(ctx.errors, ctx.warnings, 0);
            }
        };

        let known_keys: HashSet<&str> = RECIPE_KEYS.iter().cloned().collect();
        let unknown_keys: Vec<String> = recipe
            .keys()
            .filter(|k| !known_keys.contains(k.as_str()))
            .cloned()
            .collect();
        if !unknown_keys.is_empty() {
            ctx.warnings
                .push(format!("ignored top-level recipe keys: {}", unknown_keys.join(", ")));
        }

        let workflow: HashMap<String, Value> = recipe
            .get("workflow")
            .and_then(|v| v.as_object())
            .map(|o| o.iter().map(|(k, v)| (k.clone(), v.clone())).collect())
            .unwrap_or_else(|| default_workflow(prompt, recipe));

        if workflow.is_empty() {
            ctx.errors.push("workflow must contain at least one node".into());
        }
        if workflow.len() > 128 {
            ctx.errors.push(format!("workflow has too many nodes: {} > 128", workflow.len()));
        }

        ctx.node_ids = workflow.keys().cloned().collect();

        for (node_id, raw_node) in &workflow {
            let node_path = format!("workflow.{node_id}");
            if node_id.trim().is_empty() {
                ctx.errors.push(format!("{node_path}: node id must be a non-empty string"));
            }

            let node_obj = match raw_node.as_object() {
                Some(o) => o,
                None => {
                    ctx.errors.push(format!("{node_path}: node must be an object"));
                    continue;
                }
            };

            let class_type = node_obj
                .get("class_type")
                .and_then(|v| v.as_str())
                .unwrap_or("");

            if class_type.is_empty() {
                ctx.errors.push(format!("{node_path}: class_type is required"));
            } else if BLOCKED_CLASS_MARKERS.iter().any(|m| class_type.to_lowercase().contains(m)) {
                ctx.errors.push(format!(
                    "{node_path}: class_type '{class_type}' can route data outside local ComfyUI"
                ));
            }

            let inputs = match node_obj.get("inputs").and_then(|v| v.as_object()) {
                Some(o) => o,
                None => {
                    ctx.errors.push(format!("{node_path}: inputs must be an object"));
                    continue;
                }
            };

            if class_type == "SaveImage" {
                if let Some(fp) = inputs.get("filename_prefix").and_then(|v| v.as_str()) {
                    if fp.contains('/') || fp.contains('\\') {
                        ctx.errors.push(format!(
                            "{node_path}.inputs.filename_prefix: subdirectories are not allowed"
                        ));
                    }
                }
            }

            for (k, v) in inputs {
                validate_value(v, &ctx.node_ids, &format!("{node_path}.inputs.{k}"), &mut ctx);
            }
        }

        let has_save_image = workflow.values().any(|v| {
            v.as_object()
                .and_then(|o| o.get("class_type"))
                .and_then(|c| c.as_str())
                == Some("SaveImage")
        });
        if !has_save_image {
            ctx.warnings
                .push("workflow has no SaveImage node; ComfyUI may finish without image output".into());
        }

        validation_response(ctx.errors, ctx.warnings, workflow.len())
    }
}

fn validation_response(
    errors: Vec<String>,
    warnings: Vec<String>,
    nodes_count: usize,
) -> HashMap<String, Value> {
    let mut r = HashMap::new();
    r.insert("ok".into(), Value::Bool(errors.is_empty()));
    r.insert(
        "errors".into(),
        Value::Array(errors.into_iter().map(Value::String).collect()),
    );
    r.insert(
        "warnings".into(),
        Value::Array(warnings.into_iter().map(Value::String).collect()),
    );
    r.insert("nodes_count".into(), Value::Number(nodes_count.into()));
    r.insert("privacy_level".into(), Value::String("local".into()));
    r
}

impl BaseHarness for ComfyUIService {
    fn privacy_level(&self) -> &str {
        &self.privacy_level
    }

    fn execute(&self, payload: Option<HashMap<String, Value>>) -> Value {
        let p = payload.unwrap_or_default();
        let action = p.get("action").and_then(|v| v.as_str()).unwrap_or("list_presets");
        match action {
            "validate" => {
                let recipe = p.get("recipe").and_then(|v| v.as_object()).map(|o| {
                    o.iter().map(|(k, v)| (k.clone(), v.clone())).collect()
                });
                let prompt = p.get("prompt").and_then(|v| v.as_str()).unwrap_or("");
                serde_json::to_value(self.validate_recipe(recipe.as_ref(), prompt))
                    .unwrap_or_default()
            }
            "list_presets" => {
                serde_json::to_value(self.list_recipe_presets()).unwrap_or_default()
            }
            "build_recipe" => {
                let preset_id = p.get("preset_id").and_then(|v| v.as_str());
                let overrides = p.get("overrides").and_then(|v| v.as_object()).map(|o| {
                    o.iter().map(|(k, v)| (k.clone(), v.clone())).collect()
                });
                serde_json::to_value(self.build_recipe(preset_id, overrides.as_ref()))
                    .unwrap_or_default()
            }
            _ => Value::Null,
        }
    }

    fn get_state(&self) -> HashMap<String, Value> {
        let mut state = HashMap::new();
        state.insert("base_url".into(), Value::String(self.base_url.clone()));
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

    #[test]
    fn test_list_presets() {
        let svc = ComfyUIService::new();
        let presets = svc.list_recipe_presets();
        assert_eq!(presets.len(), 4);
    }

    #[test]
    fn test_get_preset() {
        let svc = ComfyUIService::new();
        let preset = svc.get_recipe_preset("sdxl-square");
        assert!(preset.is_some());
        assert_eq!(preset.unwrap().id, "sdxl-square");
    }

    #[test]
    fn test_get_preset_unknown() {
        let svc = ComfyUIService::new();
        assert!(svc.get_recipe_preset("nonexistent").is_none());
    }

    #[test]
    fn test_build_recipe_preset_only() {
        let svc = ComfyUIService::new();
        let recipe = svc.build_recipe(Some("sdxl-square"), None);
        assert_eq!(recipe.get("width").and_then(|v| v.as_i64()), Some(1024));
    }

    #[test]
    fn test_build_recipe_overrides() {
        let svc = ComfyUIService::new();
        let mut overrides = HashMap::new();
        overrides.insert("steps".into(), serde_json::json!(10));
        let recipe = svc.build_recipe(Some("sdxl-square"), Some(&overrides));
        assert_eq!(recipe.get("steps").and_then(|v| v.as_i64()), Some(10));
    }

    #[test]
    fn test_validate_empty_recipe() {
        let svc = ComfyUIService::new();
        let r = svc.validate_recipe(None, "test");
        assert!(!r.get("ok").and_then(|v| v.as_bool()).unwrap_or(true));
    }

    #[test]
    fn test_validate_default_workflow_ok() {
        let svc = ComfyUIService::new();
        let recipe = HashMap::new();
        let r = svc.validate_recipe(Some(&recipe), "a cat");
        assert!(r.get("ok").and_then(|v| v.as_bool()).unwrap_or(false));
        assert_eq!(
            r.get("nodes_count").and_then(|v| v.as_u64()),
            Some(7)
        );
    }

    #[test]
    fn test_validate_blocked_class_type() {
        let svc = ComfyUIService::new();
        let mut workflow = HashMap::new();
        workflow.insert("42".into(), serde_json::json!({
            "class_type": "HTTPRequest",
            "inputs": {}
        }));
        let mut recipe = HashMap::new();
        recipe.insert("workflow".into(), Value::Object(workflow));
        let r = svc.validate_recipe(Some(&recipe), "");
        assert!(!r.get("ok").and_then(|v| v.as_bool()).unwrap_or(true));
    }

    #[test]
    fn test_validate_external_uri_blocked() {
        let svc = ComfyUIService::new();
        let mut workflow = HashMap::new();
        workflow.insert("1".into(), serde_json::json!({
            "class_type": "LoadImage",
            "inputs": {"image": "http://evil.com/payload.png"}
        }));
        let mut recipe = HashMap::new();
        recipe.insert("workflow".into(), Value::Object(workflow));
        let r = svc.validate_recipe(Some(&recipe), "");
        assert!(!r.get("ok").and_then(|v| v.as_bool()).unwrap_or(true));
    }

    #[test]
    fn test_validate_missing_node_ref() {
        let svc = ComfyUIService::new();
        let mut workflow = HashMap::new();
        workflow.insert("1".into(), serde_json::json!({
            "class_type": "KSampler",
            "inputs": {"model": ["999", 0]}
        }));
        let mut recipe = HashMap::new();
        recipe.insert("workflow".into(), Value::Object(workflow));
        let r = svc.validate_recipe(Some(&recipe), "");
        assert!(!r.get("ok").and_then(|v| v.as_bool()).unwrap_or(true));
    }

    #[test]
    fn test_validate_warns_no_save_image() {
        let svc = ComfyUIService::new();
        let mut workflow = HashMap::new();
        workflow.insert("1".into(), serde_json::json!({
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 512, "height": 512, "batch_size": 1}
        }));
        let mut recipe = HashMap::new();
        recipe.insert("workflow".into(), Value::Object(workflow));
        let r = svc.validate_recipe(Some(&recipe), "");
        let warnings = r.get("warnings").and_then(|v| v.as_array()).unwrap();
        assert!(warnings.iter().any(|w| w.as_str().unwrap_or("").contains("SaveImage")));
    }

    #[test]
    fn test_normalize_base_url_rejects_external() {
        let svc = ComfyUIService::new();
        assert!(svc.normalize_base_url("http://evil.com:8188").is_err());
    }

    #[test]
    fn test_normalize_base_url_accepts_localhost() {
        let svc = ComfyUIService::new();
        assert!(svc.normalize_base_url("http://localhost:8188").is_ok());
    }

    #[test]
    fn test_normalize_base_url_rejects_ftp() {
        let svc = ComfyUIService::new();
        assert!(svc.normalize_base_url("ftp://127.0.0.1").is_err());
    }

    #[test]
    fn test_privacy_level() {
        let svc = ComfyUIService::new();
        assert_eq!(svc.privacy_level(), "local");
    }

    #[test]
    fn test_execute_list_presets() {
        let svc = ComfyUIService::new();
        let mut p = HashMap::new();
        p.insert("action".into(), Value::String("list_presets".into()));
        let result = svc.execute(Some(p));
        let presets: Vec<HashMap<String, Value>> = serde_json::from_value(result).unwrap();
        assert_eq!(presets.len(), 4);
    }

    #[test]
    fn test_validate_too_many_nodes() {
        let svc = ComfyUIService::new();
        let mut workflow = HashMap::new();
        for i in 0..150 {
            workflow.insert(i.to_string(), serde_json::json!({
                "class_type": "EmptyLatentImage",
                "inputs": {"width": 512, "height": 512, "batch_size": 1}
            }));
        }
        let mut recipe = HashMap::new();
        recipe.insert("workflow".into(), Value::Object(workflow));
        let r = svc.validate_recipe(Some(&recipe), "");
        assert!(!r.get("ok").and_then(|v| v.as_bool()).unwrap_or(true));
    }
}
