from pathlib import Path
from neuravia.memory.db import MemoryDB

def test_memory_db_events(tmp_path: Path):
    db = MemoryDB(tmp_path / "mem.db")
    try:
        eid = db.add_event("unit", "info", "hello", {"a": 1})
        assert isinstance(eid, int) and eid > 0
        rows = db.list_events(kind="unit", limit=10)
        assert rows and rows[0]["message"] == "hello"
    finally:
        db.close()
