from pathlib import Path
from starlette.testclient import TestClient
from neuravia.memory.db import MemoryDB
from neuravia.web.app import create_app

def test_api_health_and_stats(tmp_path: Path):
    # Prepare a small DB
    db_path = tmp_path / "ui.db"
    db = MemoryDB(db_path)
    try:
        db.add_event("unit", "info", "hello")
        db.add_action("plan", "ok", {"a":1}, {"b":2})
    finally:
        db.close()

    app = create_app(str(db_path), sandbox_path=str(tmp_path/"sandbox"), log_dir=str(tmp_path/"logs"))
    client = TestClient(app)

    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"

    r = client.get("/api/stats")
    assert r.status_code == 200
    js = r.json()
    assert js["events"] >= 1 and js["actions"] >= 1

    r = client.get("/")
    assert r.status_code == 200
    assert "Neuravia" in r.text
