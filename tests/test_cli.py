import subprocess
import sys
from pathlib import Path

def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "neuravia", *args],
        text=True,
        capture_output=True,
        check=False,
    )

def test_help_works():
    p = run_cli("--help")
    assert p.returncode == 0
    assert "Neuravia-Autonomy" in p.stdout

def test_goal_exec_and_plan():
    assert Path("config").exists()
    p = run_cli("--goal", "Objet test", "--dry-run", "--no-confirm", "--config", "config", "--profile", "safe", "--max-steps", "3")
    assert p.returncode == 0
    assert "Phase 3 (config loaded)" in p.stdout
    assert "=== PLAN ===" in p.stdout
    assert "STATUS: ok" in p.stdout
