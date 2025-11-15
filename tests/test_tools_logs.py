from pathlib import Path
from neuravia.config import load_settings
from neuravia.tools.logs import log_event

def test_log_event_writes_line(tmp_path: Path):
    s = load_settings(config="config", profile="safe")
    p = log_event(s, "unit-test message")
    assert p.exists()
    data = p.read_text(encoding="utf-8").splitlines()[-1]
    assert "unit-test message" in data and "T" in data  # ISO timestamp
