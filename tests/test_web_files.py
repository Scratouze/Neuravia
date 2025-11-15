from pathlib import Path
from starlette.testclient import TestClient
from neuravia.web.app import create_app

def test_files_listing_and_download(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir(parents=True, exist_ok=True)
    (sandbox / "a.txt").write_text("hello", encoding="utf-8")
    (sandbox / "b.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    app = create_app(db_path=str(tmp_path / "db.sqlite"), sandbox_path=str(sandbox), log_dir=str(tmp_path/"logs"))
    client = TestClient(app)

    r = client.get("/api/files")
    assert r.status_code == 200
    js = r.json()
    assert js["count"] >= 1
    assert any(it["path"] == "a.txt" for it in js["items"])

    r = client.get("/files/download", params={"path": "a.txt"})
    assert r.status_code == 200
    assert r.content == b"hello"

    r = client.get("/files/download", params={"path": "../secret.txt"})
    assert r.status_code in (400,403,404)
