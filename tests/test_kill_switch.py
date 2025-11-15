from pathlib import Path
import pytest
from starlette.testclient import TestClient

from neuravia.config import Settings, General, Security, Network, Modules, LLM, Memory
from neuravia.tools.files import safe_write_text
from neuravia.tools.shell import run_command
from neuravia.security.kill import KillSwitchEngaged
from neuravia.web.app import create_app

def _settings(tmp_path: Path) -> Settings:
    return Settings(
        general=General(profile="safe", os_mode="auto", dry_run=False, no_confirm=True,
                        sandbox_path=str(tmp_path/"sb"), log_dir=str(tmp_path/"logs"), kill_switch_path=str(tmp_path/"kill")),
        security=Security(chain_secret=""),
        network=Network(),
        modules=Modules(),
        llm=LLM(),
        memory=Memory(db_path=str(tmp_path/"mem.db"), index_enabled=False)
    )

def test_kill_file_blocks_tools(tmp_path: Path):
    s = _settings(tmp_path)
    # Engage kill
    Path(s.general.kill_switch_path).write_text("KILLED", encoding="utf-8")
    with pytest.raises(KillSwitchEngaged):
        safe_write_text(s, "x.txt", "hello")
    with pytest.raises(KillSwitchEngaged):
        run_command(s, "echo", ["hello"])

def test_kill_http_endpoint(tmp_path: Path):
    s = _settings(tmp_path)
    app = create_app(str(tmp_path/"mem.db"), sandbox_path=str(tmp_path/"sb"), log_dir=str(tmp_path/"logs"),
                     profile="safe", kill_switch_path=s.general.kill_switch_path)
    client = TestClient(app)
    r = client.post("/api/kill")
    assert r.status_code == 200
    assert Path(s.general.kill_switch_path).exists()
