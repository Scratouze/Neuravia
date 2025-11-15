from __future__ import annotations
from pathlib import Path
from typing import Optional
from ..config import Settings
from .errors import FileSecurityError
from ..security.kill import check_kill, KillSwitchEngaged

def _resolve_in_sandbox(settings: Settings, rel_path: str) -> Path:
    base = Path(settings.general.sandbox_path).resolve()
    p = Path(rel_path)
    full = (base / p).resolve() if not p.is_absolute() else p.resolve()
    # prevent escape
    try:
        full.relative_to(base)
    except Exception:
        raise FileSecurityError(f"Chemin hors sandbox: {rel_path}")
    return full

def safe_write_text(settings: Settings, rel_path: str, content: str, *, encoding: str = "utf-8") -> Path:
    check_kill(settings.general.kill_switch_path)  # raise if engaged
    dest = _resolve_in_sandbox(settings, rel_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding=encoding)
    return dest

def safe_read_text(settings: Settings, rel_path: str, *, encoding: str = "utf-8") -> str:
    src = _resolve_in_sandbox(settings, rel_path)
    return src.read_text(encoding=encoding)
