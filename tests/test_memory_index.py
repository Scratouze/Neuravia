from pathlib import Path
from neuravia.memory.db import MemoryDB
from neuravia.memory.index import TextIndexerSimple

def test_simple_index_search(tmp_path: Path):
    db = MemoryDB(tmp_path / "idx.db")
    try:
        idx = TextIndexerSimple(db)
        idx.add("d1", "the quick brown fox jumps over the lazy dog")
        idx.add("d2", "python packaging and editable installs")
        idx.add("d3", "vision ocr and screenshots")
        res = idx.search("quick fox", top_k=2)
        assert res and res[0][0] == "d1"
    finally:
        db.close()
