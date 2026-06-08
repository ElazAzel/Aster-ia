from asterion_api.schemas import HardwareProfile
from asterion_api.services.model_router import ModelRouter


def test_select_local_model_with_enough_vram():
    router = ModelRouter()
    profile = HardwareProfile(vram_gb=8.0)
    selection = router.select("general chat", profile)
    assert selection.mode == "local"
    assert selection.model in ("phi3:mini", "mistral:7b", "llama3.2")


def test_select_low_vram_fallback():
    router = ModelRouter()
    profile = HardwareProfile(vram_gb=-1.0)
    selection = router.select("general chat", profile)
    assert selection.mode == "api"
    assert selection.model == "gpt-4o-mini"


def test_select_picks_largest_viable():
    router = ModelRouter()
    profile = HardwareProfile(vram_gb=10.0)
    selection = router.select("general chat", profile)
    assert selection.mode == "local"
    assert selection.model in ("phi3:mini", "mistral:7b", "llama3.2", "qwen2.5:7b")


def test_select_qwen_on_low_vram():
    router = ModelRouter()
    profile = HardwareProfile(vram_gb=3.0)
    selection = router.select("general chat", profile)
    assert selection.mode == "local"
    assert selection.model in ("phi3:mini", "qwen2.5:0.5b", "llama3.2:1b", "gemma2:2b")


def test_custom_catalog():
    router = ModelRouter()
    router.set_state({
        "local_catalog": [{"model": "custom", "required_vram_gb": 1.0, "reason": "test"}],
        "api_fallback": "custom-api",
    })
    profile = HardwareProfile(vram_gb=2.0)
    selection = router.select("task", profile)
    assert selection.model == "custom"
    assert selection.mode == "local"
