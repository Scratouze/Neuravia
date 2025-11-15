from __future__ import annotations
import sqlite3, json, hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

ISO = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        kind TEXT NOT NULL,
        level TEXT NOT NULL,
        message TEXT NOT NULL,
        data TEXT
    );""",
    """CREATE TABLE IF NOT EXISTS actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        name TEXT NOT NULL,
        status TEXT NOT NULL,
        input TEXT,
        output TEXT
    );""",
    """CREATE TABLE IF NOT EXISTS artifacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        path TEXT NOT NULL,
        sha256 TEXT NOT NULL,
        meta TEXT
    );""",
    """CREATE TABLE IF NOT EXISTS index_docs (
        doc_id TEXT PRIMARY KEY,
        text TEXT NOT NULL,
        tokens TEXT NOT NULL
    );"""
]

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha256_text(text: str, encoding: str = "utf-8") -> str:
    return sha256_bytes(text.encode(encoding))

class MemoryDB:
    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        for stmt in SCHEMA:
            cur.execute(stmt)
        self.conn.commit()

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

    # ---------------- Events ----------------
    def add_event(self, kind: str, level: str, message: str, data: Optional[dict] = None) -> int:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO events(ts, kind, level, message, data) VALUES (?, ?, ?, ?, ?)",
            (ISO(), kind, level, message, json.dumps(data or {}, ensure_ascii=False)),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_events(self, kind: Optional[str] = None, limit: int = 100) -> List[dict]:
        cur = self.conn.cursor()
        if kind:
            cur.execute("SELECT id, ts, kind, level, message, data FROM events WHERE kind=? ORDER BY id DESC LIMIT ?", (kind, limit))
        else:
            cur.execute("SELECT id, ts, kind, level, message, data FROM events ORDER BY id DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        out = []
        for r in rows:
            d = {"id": r[0], "ts": r[1], "kind": r[2], "level": r[3], "message": r[4]}
            try:
                d["data"] = json.loads(r[5]) if r[5] else None
            except Exception:
                d["data"] = None
            out.append(d)
        return out

    # ---------------- Actions ----------------
    def add_action(self, name: str, status: str, input: Optional[dict] = None, output: Optional[dict] = None) -> int:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO actions(ts, name, status, input, output) VALUES (?, ?, ?, ?, ?)",
            (ISO(), name, status, json.dumps(input or {}, ensure_ascii=False), json.dumps(output or {}, ensure_ascii=False)),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    # ---------------- Artifacts ----------------
    def add_artifact(self, path: str, meta: Optional[dict] = None, *, content_bytes: bytes | None = None) -> int:
        digest = sha256_bytes(content_bytes) if content_bytes is not None else sha256_text(path)
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO artifacts(ts, path, sha256, meta) VALUES (?, ?, ?, ?)",
            (ISO(), path, digest, json.dumps(meta or {}, ensure_ascii=False)),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    # ---------------- Index (simple) ----------------
    @staticmethod
    def _tokenize(text: str) -> list[str]:
        import re
        return [t for t in re.findall(r"[a-zA-Z0-9]+", text.lower()) if t]

    def index_add_document(self, doc_id: str, text: str) -> None:
        tokens = self._tokenize(text)
        tok_str = " ".join(tokens)
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO index_docs(doc_id, text, tokens) VALUES (?, ?, ?)",
            (doc_id, text, tok_str),
        )
        self.conn.commit()

    def index_search(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        q_tokens = set(self._tokenize(query))
        cur = self.conn.cursor()
        cur.execute("SELECT doc_id, tokens FROM index_docs")
        scores: list[tuple[str, float]] = []
        for doc_id, tok_str in cur.fetchall():
            d_tokens = set(tok_str.split()) if tok_str else set()
            if not q_tokens and not d_tokens:
                score = 0.0
            else:
                inter = len(q_tokens & d_tokens)
                union = len(q_tokens | d_tokens) or 1
                score = inter / union
            if score > 0:
                scores.append((doc_id, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:max(1, top_k)]

def persist_run(db: "MemoryDB", objective: str, status: str, logs: list[str]) -> int:
    return db.add_event(kind="run", level="info", message=f"objective={objective}", data={"status": status, "lines": len(logs)})
