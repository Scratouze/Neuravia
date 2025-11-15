from neuravia.config import load_settings
from neuravia.core.orchestrator import run_goal

def test_orchestrator_simple_run():
    s = load_settings(config="config", profile="safe", overrides={"dry_run": True})
    result = run_goal(s, "Dire bonjour", max_steps=3)
    assert result.status == "ok"
    assert len(result.plan.steps) >= 2
    assert any("Executor" in line for line in result.logs)
