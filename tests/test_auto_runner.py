from pathlib import Path
from neuravia.autoimprove.runner import run_pytest

def test_run_pytest_smoke(tmp_path: Path):
    # create a trivial test that passes
    t = tmp_path / "tests"
    t.mkdir(parents=True, exist_ok=True)
    (t / "test_ok.py").write_text("def test_ok():\n    assert 1+1==2\n", encoding="utf-8")
    rr = run_pytest(tmp_path, timeout_sec=60)
    assert rr.returncode == 0
    assert "1 passed" in rr.stdout or "1 passed" in rr.stderr
