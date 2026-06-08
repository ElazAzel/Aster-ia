from asterion_api.services.agent_sandbox import TaskSimulator


def test_plan_read_only():
    sim = TaskSimulator()
    plan = sim.plan("read the file")
    assert "file_read" in plan.required_permissions
    assert "file_write" not in plan.required_permissions
    assert "web_search" not in plan.required_permissions
    assert "run_code" not in plan.required_permissions


def test_plan_write_request():
    sim = TaskSimulator()
    plan = sim.plan("создай новый файл")
    assert "file_write" in plan.required_permissions


def test_plan_web_search():
    sim = TaskSimulator()
    plan = sim.plan("search the web for news")
    assert "web_search" in plan.required_permissions


def test_plan_code_execution():
    sim = TaskSimulator()
    plan = sim.plan("run python code to analyze data")
    assert "run_code" in plan.required_permissions


def test_plan_steps_count():
    sim = TaskSimulator()
    plan = sim.plan("do something complex")
    assert len(plan.steps) == 4


def test_plan_estimated_tokens():
    sim = TaskSimulator()
    plan = sim.plan("short")
    assert plan.estimated_tokens >= 800
    plan_long = sim.plan(" ".join(["word"] * 100))
    assert plan_long.estimated_tokens <= 8000
