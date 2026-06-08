from asterion_api.config import Settings


def test_max_tokens_default():
    s = Settings()
    assert s.max_tokens == 2048


def test_chat_history_limit_default():
    s = Settings()
    assert s.chat_history_limit == 20


def test_comfyui_url_in_settings():
    s = Settings()
    assert "8188" in s.comfyui_url


def test_searxng_url_in_settings():
    s = Settings()
    assert "8080" in s.searxng_url
