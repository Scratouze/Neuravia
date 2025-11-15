from __future__ import annotations
from pathlib import Path

class ScreenSecurityError(RuntimeError):
    pass

def _norm(p: Path) -> Path:
    return p.resolve()

def _is_under(target: Path, root: Path) -> bool:
    t = _norm(target)
    r = _norm(root)
    try:
        t.relative_to(r)
        return True
    except Exception:
        return False

def capture_screen(settings, dest_rel_path: str, *, monitor: int = 1) -> Path:
    """Capture d'écran basique via 'mss' si disponible.
    - Écrit un PNG **strictement dans le sandbox**.
    - Nécessite le module 'mss' installé localement.
    """
    try:
        import mss  # type: ignore
        import mss.tools  # type: ignore
    except Exception as e:  # pragma: no cover - env-dependent
        raise ImportError("Le module 'mss' n'est pas installé. `pip install mss`.") from e

    base = _norm(Path(settings.general.sandbox_path))
    dest = Path(dest_rel_path)
    out = _norm(base / dest) if not dest.is_absolute() else _norm(dest)

    # Sécurité : la cible doit être SOUS le sandbox, même si chemin absolu
    if not _is_under(out, base):
        raise ScreenSecurityError(f"Capture hors sandbox refusée: {out}")

    # Forcer l'extension .png
    if out.suffix.lower() != ".png":
        out = out.with_suffix(".png")

    out.parent.mkdir(parents=True, exist_ok=True)

    with mss.mss() as sct:
        # monitors[0] = bounding monitor; 1..n = écrans
        monitors = sct.monitors
        idx = monitor if 0 <= monitor < len(monitors) else 1
        mon = monitors[idx]
        img = sct.grab(mon)
        mss.tools.to_png(img.rgb, img.size, output=str(out))
    return out
