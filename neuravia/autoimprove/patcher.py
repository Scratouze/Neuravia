from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, List, Tuple
import shutil, time

from .diff_apply import parse_unified_patch, apply_hunks_to_text

@dataclass
class PatchResult:
    changed: List[Tuple[Path,int]]  # (path, bytes_written)
    backups_dir: Path

class PatchSecurityError(Exception): ...
class PatchFormatError(Exception): ...

def _norm(p: Path) -> Path:
    return p.resolve()

def _is_under(target: Path, roots: Sequence[Path]) -> bool:
    t = _norm(target)
    for r in roots:
        try:
            t.relative_to(_norm(r))
            return True
        except Exception:
            continue
    return False

def apply_patch_text(
    base_dir: Path,
    patch_text: str,
    *,
    allow_roots: Sequence[Path],
    max_total_bytes: int = 512_000,  # 500 KB
    dry_run: bool = False,
) -> PatchResult:
    """
    Apply a unified diff to files under base_dir, restricted to allow_roots.
    Create backups under .patch_backups/<timestamp>/
    """
    try:
        files = parse_unified_patch(patch_text)
    except Exception as e:
        raise PatchFormatError(str(e)) from e

    changed: List[Tuple[Path,int]] = []
    ts = time.strftime("%Y%m%d-%H%M%S")
    backups = base_dir / ".patch_backups" / ts
    backups.mkdir(parents=True, exist_ok=True)

    total_bytes = 0
    for pf in files:
        rel = Path(pf.path)
        target = _norm(base_dir / rel)
        if not _is_under(target, [base_dir / r for r in allow_roots]):
            raise PatchSecurityError(f"Chemin non autorisé: {rel}")
        # read original (empty if new file and not exists)
        original = ""
        if target.exists():
            original = target.read_text(encoding="utf-8", errors="ignore")
        new_text = apply_hunks_to_text(original, pf.hunks)
        b = new_text.encode("utf-8")
        total_bytes += len(b)
        if total_bytes > max_total_bytes:
            raise PatchSecurityError("Patch dépasse la limite de taille autorisée")

        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            # backup if exists
            if target.exists():
                backup_path = backups / rel
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup_path)
            target.write_text(new_text, encoding="utf-8")
        changed.append((target, len(b)))
    return PatchResult(changed=changed, backups_dir=backups)
