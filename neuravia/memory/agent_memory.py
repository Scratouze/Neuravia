# neuravia/memory/agent_memory.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from .db import MemoryDB

# On réutilise le même fichier SQLite que le reste de Neuravia
DEFAULT_DB_PATH = Path("data") / "memory.db"


@dataclass
class AgentMemoryEntry:
    id: int
    ts: str
    goal: str
    step: int
    content: str
    tags: list[str]
    run_label: str | None


def _open_db(db_path: Path | str = DEFAULT_DB_PATH) -> MemoryDB:
    return MemoryDB(db_path)


def store_step(
    goal: str,
    step: int,
    content: str,
    *,
    tags: Optional[Iterable[str]] = None,
    run_label: str | None = None,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> int:
    """
    Enregistre une étape d'agent dans la mémoire persistante en utilisant
    la table 'events' de MemoryDB (kind='agent_step').
    """
    db = _open_db(db_path)
    try:
        data = {
            "goal": goal,
            "step": step,
            "content": content,
            "tags": list(tags or []),
            "run_label": run_label,
        }
        # on met le goal dans 'message' pour pouvoir filtrer facilement
        event_id = db.add_event(
            kind="agent_step",
            level="info",
            message=goal,
            data=data,
        )
        return event_id
    finally:
        db.close()


def get_recent(
    goal: str,
    *,
    limit: int = 10,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> List[AgentMemoryEntry]:
    """
    Retourne les derniers souvenirs pour un objectif donné,
    du plus ancien au plus récent.
    """
    db = _open_db(db_path)
    try:
        # On prend un peu plus large puis on filtre
        events = db.list_events(kind="agent_step", limit=limit * 5)
    finally:
        db.close()

    filtered: List[AgentMemoryEntry] = []
    for e in events:
        # e: {"id","ts","kind","level","message","data"}
        data = e.get("data") or {}
        # On accepte soit message == goal, soit data["goal"] == goal
        if e.get("message") != goal and data.get("goal") != goal:
            continue

        try:
            step = int(data.get("step", 0))
        except Exception:
            step = 0

        tags = data.get("tags") or []
        if not isinstance(tags, list):
            tags = []

        entry = AgentMemoryEntry(
            id=e["id"],
            ts=e["ts"],
            goal=data.get("goal") or e.get("message") or "",
            step=step,
            content=str(data.get("content") or ""),
            tags=tags,
            run_label=data.get("run_label"),
        )
        filtered.append(entry)

    # MemoryDB.list_events renvoie du plus récent au plus ancien.
    # Pour le contexte, on préfère du plus ancien au plus récent.
    filtered.sort(key=lambda x: x.ts)
    return filtered[-limit:]
