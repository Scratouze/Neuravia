from neuravia.config import load_settings
from neuravia.tools.shell import run_command, ShellSecurityError

def test_echo_allowed():
    s = load_settings(config="config", profile="safe", overrides={"dry_run": True, "os_mode": "windows"})
    res = run_command(s, "echo", ["hello"])
    assert res.returncode == 0
    assert "hello" in res.stdout.lower()

def test_disallowed_command():
    s = load_settings(config="config", profile="safe", overrides={"dry_run": True})
    try:
        run_command(s, "python", ["-V"])
        assert False, "Should have raised"
    except ShellSecurityError:
        pass
