import sys, subprocess

def test_cli_llm_dummy_plan_header_and_steps():
    p = subprocess.run(
        [
            sys.executable, "-m", "neuravia",
            "--goal", "Tester le plan LLM",
            "--dry-run", "--no-confirm",
            "--config", "config", "--profile", "safe", "--max-steps", "3",
            "--use-llm", "--llm-model", "dummy",
        ],
        text=True, capture_output=True
    )
    assert p.returncode == 0
    # Le header spécifique LLM doit apparaître
    assert "=== PLAN (via LLM) ===" in p.stdout
    # Dummy renvoie 3 étapes numérotées
    assert "\n1." in p.stdout and "\n2." in p.stdout and "\n3." in p.stdout
