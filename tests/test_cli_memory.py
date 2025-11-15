import sqlite3, subprocess, sys
from pathlib import Path

def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "neuravia", *args], text=True, capture_output=True, check=False)

def test_cli_persist_run(tmp_path: Path):
    db_path = tmp_path / "run.db"
    p = run_cli("--goal", "persist test", "--dry-run", "--no-confirm", "--config", "config", "--profile", "safe", "--max-steps", "2", "--persist-run", "--memory-db", str(db_path))
    assert p.returncode == 0
    assert "[memory] persisted run" in p.stdout
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        cur.execute("SELECT count(*) FROM events")
        n = cur.fetchone()[0]
        assert n >= 1
    finally:
        con.close()
