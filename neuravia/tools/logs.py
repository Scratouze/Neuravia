from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from ..config import Settings

def log_event(settings: Settings, message: str) -> Path:
    log_dir = Path(settings.general.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "neuravia.log"
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    with path.open("a", encoding="utf-8") as f:
        f.write(f"{ts} | {message}\n")
    return path
