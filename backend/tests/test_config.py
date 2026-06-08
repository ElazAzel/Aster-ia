from asterion_api.config import Settings


def test_default_settings():
    s = Settings()
    assert s.host == "127.0.0.1"
    assert s.port == 8000
    assert s.ollama_base_url == "http://127.0.0.1:11434"
    assert s.default_model == "llama3.2"
    assert s.comfyui_url == "http://127.0.0.1:8188"
    assert s.searxng_url == "http://127.0.0.1:8080"
    assert s.local_first is True


def test_data_dir_property(monkeypatch):
    monkeypatch.delenv("ASTERION_DATA_DIR", raising=False)
    s = Settings()
    assert s.data_dir.name == ".asterion"


def test_database_path_property(monkeypatch):
    monkeypatch.delenv("ASTERION_DATA_DIR", raising=False)
    s = Settings()
    assert s.database_path.name == "asterion.db"
