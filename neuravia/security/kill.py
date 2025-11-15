from __future__ import annotations
from pathlib import Path

class KillSwitchEngaged(Exception):
    """Raised when kill-switch is engaged."""

def check_kill(kill_switch_path: str) -> None:
    """Raise if the kill-switch file exists."""
    p = Path(kill_switch_path)
    if p.exists():
        raise KillSwitchEngaged(f"Kill-switch engaged: {p}")
