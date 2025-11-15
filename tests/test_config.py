from pathlib import Path
from neuravia.config import load_settings

def test_safe_defaults():
    s = load_settings(config=str(Path("config")), profile="safe")
    assert s.general.profile == "safe"
    assert s.general.sandbox_path == "data/sandbox"
    assert s.network.enabled is False
    assert s.modules.filesystem is True
    assert s.llm.local_enabled is True
    assert s.llm.remote_enabled is False

def test_danger_allows_network():
    s = load_settings(config=str(Path("config")), profile="danger")
    assert s.network.enabled is True
    assert s.modules.http is True

def test_cli_overrides_apply():
    s = load_settings(config=str(Path("config")), profile="safe", overrides={"dry_run": True, "os_mode": "windows"})
    assert s.general.dry_run is True
    assert s.general.os_mode == "windows"
