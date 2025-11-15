import sys, subprocess

def test_demo_cli_dummy_ok():
    p = subprocess.run(
        [sys.executable, "-m", "neuravia.llm.demo", "--goal", "Test objectif", "--model", "dummy"],
        text=True, capture_output=True
    )
    assert p.returncode == 0
    assert "=== PLAN (model:" in p.stdout
    assert "\n1." in p.stdout
