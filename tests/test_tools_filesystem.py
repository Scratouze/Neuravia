from pathlib import Path
from neuravia.config import load_settings
from neuravia.tools.files import safe_write_text, safe_read_text, FileSecurityError

def test_safe_write_and_read(tmp_path: Path):
    # Prépare config pointant vers un sandbox dans ./data/sandbox
    s = load_settings(config="config", profile="safe", overrides={"dry_run": True})
    # Ecrit dans sandbox relatif
    target = safe_write_text(s, "test_dir/hello.txt", "hello world")
    assert target.exists()
    read = safe_read_text(s, "test_dir/hello.txt")
    assert read == "hello world"

def test_block_outside_allow(tmp_path: Path):
    s = load_settings(config="config", profile="safe", overrides={"dry_run": True})
    # Tentative de sortie de sandbox via ..
    try:
        safe_write_text(s, "../evil.txt", "nope")
        assert False, "Should have raised"
    except FileSecurityError:
        pass
