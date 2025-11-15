import pytest
from pathlib import Path
from neuravia.config import load_settings
from neuravia.tools.screen import capture_screen

def _has_mss():
    try:
        import mss  # type: ignore  # noqa
        return True
    except Exception:
        return False

@pytest.mark.skipif(not _has_mss(), reason="mss non installé")
def test_capture_screen(tmp_path: Path):
    s = load_settings(config="config", profile="safe")
    out = capture_screen(s, "captures/snap.png")
    assert out.exists() and out.suffix.lower() == ".png"
