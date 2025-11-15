from __future__ import annotations
import shutil, subprocess
from pathlib import Path
from typing import Iterable, Sequence, List
from ..config import Settings
from .files import FileSecurityError

def has_tesseract() -> bool:
    return shutil.which("tesseract") is not None

def tesseract_version() -> str | None:
    try:
        out = subprocess.run(["tesseract", "--version"], capture_output=True, text=True, check=False)
        return out.stdout.splitlines()[0] if out.stdout else None
    except Exception:
        return None

# ---- path helpers (read within sandbox or allowlist) ----
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

def _resolve_read_path(settings: Settings, path: str) -> Path:
    base = _norm(Path(settings.general.sandbox_path))
    p = Path(path)
    if not p.is_absolute():
        p = _norm(base / p)
        if not _is_under(p, base):
            raise FileSecurityError(f"Lecture image refusée (échappe le sandbox): {p}")
    else:
        allowed_roots = [base] + [Path(a) for a in settings.security.file_write_allow]
        ok = any(_is_under(_norm(p), _norm(r)) for r in allowed_roots)
        if not ok:
            raise FileSecurityError(f"Lecture image refusée hors allowlist: {p}")
        p = _norm(p)
    if not p.exists():
        raise FileNotFoundError(p)
    return p

def _ext_allowed(path: Path, allowed_exts: Iterable[str]) -> bool:
    e = path.suffix.lower()
    return e in {x.lower() for x in allowed_exts}

def ocr_image_to_text(
    settings: Settings,
    image_path: str,
    *,
    lang: str = "eng",
    psm: int | None = 6,
    allowed_exts: Sequence[str] | None = None,
    extra_args: Sequence[str] | None = None,
) -> str:
    """OCR via tesseract CLI.
    - Enforce path within sandbox/allowlist.
    - Enforce extension allowlist.
    - Returns recognized text (stdout).
    """
    # 1) Résoudre le chemin + vérifier sandbox/allowlist
    img = _resolve_read_path(settings, image_path)

    # 2) Vérifier l'extension d'abord (ne dépend pas de tesseract)
    allowed = list(allowed_exts or [".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"])
    if not _ext_allowed(img, allowed):
        raise FileSecurityError(f"Extension non autorisée: {img.suffix} (allowlist: {allowed})")

    # 3) Ensuite seulement, vérifier la présence de tesseract
    if not has_tesseract():
        raise RuntimeError("tesseract non disponible")

    # 4) Exécuter tesseract
    cmd: List[str] = ["tesseract", str(img), "stdout"]
    if lang:
        cmd += ["-l", lang]
    if psm is not None:
        cmd += ["--psm", str(psm)]
    if extra_args:
        cmd += list(extra_args)

    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"tesseract a échoué (code {proc.returncode}): {proc.stderr.strip()}")
    return proc.stdout
