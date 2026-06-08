from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = "Asterion AI Sidecar"
    host: str = os.getenv("ASTERION_API_HOST", "127.0.0.1")
    port: int = int(os.getenv("ASTERION_API_PORT", "8000"))
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    default_model: str = os.getenv("ASTERION_DEFAULT_MODEL", "llama3.2")
    keyring_service: str = os.getenv("ASTERION_KEYRING_SERVICE", "asterion-ai")
    keyring_db_key_name: str = os.getenv("ASTERION_KEYRING_DB_KEY_NAME", "sqlcipher-main")
    comfyui_url: str = os.getenv("ASTERION_COMFYUI_URL", "http://127.0.0.1:8188")
    searxng_url: str = os.getenv("ASTERION_SEARXNG_URL", "http://127.0.0.1:8080")
    max_tokens: int = int(os.getenv("ASTERION_MAX_TOKENS", "2048"))
    chat_history_limit: int = int(os.getenv("ASTERION_CHAT_HISTORY_LIMIT", "20"))
    local_first: bool = True
    required_models: tuple[str, ...] = ("llama3.2", "nomic-embed-text")
    searxng_base_url: str = os.getenv("SEARXNG_BASE_URL", "http://127.0.0.1:8080")
    duckdb_memory_limit: str = os.getenv("ASTERION_DUCKDB_MEMORY_LIMIT", "512MB")
    duckdb_threads: int = int(os.getenv("ASTERION_DUCKDB_THREADS", "2"))

    @property
    def data_dir(self) -> Path:
        return Path(os.getenv("ASTERION_DATA_DIR", Path.home() / ".asterion"))

    @property
    def database_path(self) -> Path:
        return self.data_dir / "asterion.db"

    @property
    def allow_plaintext_dev_db(self) -> bool:
        return os.getenv("ASTERION_ALLOW_PLAINTEXT_SQLITE_FOR_DEV", "0") == "1"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
