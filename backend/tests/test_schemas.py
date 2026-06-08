from asterion_api.schemas import (
    AgentPlan,
    HardwareProfile,
    ModelSelection,
    PrivacyItem,
    PrivacyReport,
    RagChunk,
)


def test_privacy_report_level_override():
    report = PrivacyReport(
        level="green",
        items=[PrivacyItem(what="model", destination="local", risk="red")],
    )
    assert report.level == "green"
    assert report.items[0].risk == "red"


def test_hardware_profile_defaults():
    profile = HardwareProfile(vram_gb=4.0)
    assert profile.vram_gb == 4.0


def test_model_selection_fields():
    sel = ModelSelection(model="llama3.2", mode="local", reason="test")
    assert sel.model == "llama3.2"
    assert sel.mode == "local"


def test_rag_chunk_fields():
    chunk = RagChunk(
        id="abc",
        room_id="r1",
        content="text",
        source="/file.txt",
        score=0.95,
    )
    assert chunk.score == 0.95


def test_agent_plan_fields():
    plan = AgentPlan(
        steps=["a", "b"],
        required_permissions=["file_read"],
        estimated_tokens=1000,
    )
    assert len(plan.steps) == 2
