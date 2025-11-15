from pathlib import Path
from starlette.testclient import TestClient
from neuravia.memory.db import MemoryDB
from neuravia.web.app import create_app

def test_sse_once_snapshot(tmp_path: Path):
    db_path = tmp_path / "ui.db"
    db = MemoryDB(db_path)
    try:
        for i in range(3):
            db.add_event("unit", "info", f"msg{i}")
    finally:
        db.close()

    app = create_app(str(db_path), sandbox_path=str(tmp_path/"sandbox"), log_dir=str(tmp_path/"logs"))
    client = TestClient(app)

    with client.stream("GET", "/api/events/stream", params={"once": "true"}) as s:
        text = next(s.iter_text())
        assert "data:" in text
