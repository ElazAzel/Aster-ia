use std::path::PathBuf;
use std::sync::OnceLock;

/// Application configuration — mirrors `asterion_api.config.Settings`.
#[derive(Debug, Clone)]
pub struct Settings {
    pub app_name: String,
    pub host: String,
    pub port: u16,
    pub ollama_base_url: String,
    pub default_model: String,
    pub keyring_service: String,
    pub keyring_db_key_name: String,
    pub local_first: bool,
    pub required_models: Vec<String>,
    pub searxng_base_url: String,
    pub duckdb_memory_limit: String,
    pub duckdb_threads: u32,
    pub data_dir: PathBuf,
}

fn env_or(key: &str, default: &str) -> String {
    std::env::var(key).unwrap_or_else(|_| default.to_string())
}

impl Default for Settings {
    fn default() -> Self {
        let data_dir = PathBuf::from(env_or(
            "ASTERION_DATA_DIR",
            &format!("{}/.asterion", env_or("HOME", &env_or("USERPROFILE", "."))),
        ));

        Self {
            app_name: "Asterion AI Sidecar".into(),
            host: env_or("ASTERION_API_HOST", "127.0.0.1"),
            port: env_or("ASTERION_API_PORT", "8000").parse().unwrap_or(8000),
            ollama_base_url: env_or("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            default_model: env_or("ASTERION_DEFAULT_MODEL", "llama3.2"),
            keyring_service: env_or("ASTERION_KEYRING_SERVICE", "asterion-ai"),
            keyring_db_key_name: env_or("ASTERION_KEYRING_DB_KEY_NAME", "sqlcipher-main"),
            local_first: true,
            required_models: vec!["llama3.2".into(), "nomic-embed-text".into()],
            searxng_base_url: env_or("SEARXNG_BASE_URL", "http://127.0.0.1:8080"),
            duckdb_memory_limit: env_or("ASTERION_DUCKDB_MEMORY_LIMIT", "512MB"),
            duckdb_threads: env_or("ASTERION_DUCKDB_THREADS", "2").parse().unwrap_or(2),
            data_dir,
        }
    }
}

impl Settings {
    pub fn database_path(&self) -> PathBuf {
        self.data_dir.join("asterion.db")
    }

    pub fn allow_plaintext_dev_db(&self) -> bool {
        env_or("ASTERION_ALLOW_PLAINTEXT_SQLITE_FOR_DEV", "0") == "1"
    }
}

static SETTINGS: OnceLock<Settings> = OnceLock::new();

pub fn get_settings() -> &'static Settings {
    SETTINGS.get_or_init(Settings::default)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn with_clean_env<T>(f: impl FnOnce() -> T) -> T {
        let api_port = std::env::var("ASTERION_API_PORT").ok();
        std::env::remove_var("ASTERION_API_PORT");
        let api_host = std::env::var("ASTERION_API_HOST").ok();
        std::env::remove_var("ASTERION_API_HOST");
        let result = f();
        if let Some(v) = api_port {
            std::env::set_var("ASTERION_API_PORT", v);
        }
        if let Some(v) = api_host {
            std::env::set_var("ASTERION_API_HOST", v);
        }
        result
    }

    #[test]
    fn test_settings_defaults() {
        with_clean_env(|| {
            let s = Settings::default();
            assert_eq!(s.app_name, "Asterion AI Sidecar");
            assert!(s.ollama_base_url.contains("127.0.0.1"));
            assert_eq!(s.port, 8000);
            assert!(s.local_first);
            assert_eq!(s.required_models.len(), 2);
            assert!(s.searxng_base_url.contains("127.0.0.1"));
        });
    }

    #[test]
    fn test_database_path() {
        with_clean_env(|| {
            let s = Settings::default();
            let db = s.database_path();
            assert!(db.to_string_lossy().ends_with("asterion.db"));
        });
    }

    #[test]
    fn test_allow_plaintext_default_false() {
        with_clean_env(|| {
            let s = Settings::default();
            assert!(!s.allow_plaintext_dev_db());
        });
    }

    #[test]
    fn test_get_settings_singleton() {
        let a = get_settings();
        let b = get_settings();
        assert!(std::ptr::eq(a, b));
    }

    #[test]
    fn test_env_override() {
        with_clean_env(|| {
            std::env::set_var("ASTERION_API_PORT", "9090");
            let s = Settings::default();
            assert_eq!(s.port, 9090);
            std::env::remove_var("ASTERION_API_PORT");
        });
    }

    #[test]
    fn test_duckdb_defaults() {
        with_clean_env(|| {
            let s = Settings::default();
            assert_eq!(s.duckdb_memory_limit, "512MB");
            assert_eq!(s.duckdb_threads, 2);
        });
    }
}
