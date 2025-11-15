from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Optional
import shutil

from ..config import Settings
from ..memory.db import MemoryDB
from .patcher import apply_patch_text, PatchSecurityError, PatchFormatError
from .runner import run_pytest

ALLOWED_DIRS = [Path("neuravia"), Path("tests"), Path("config")]

@dataclass
class ImproveOutcome:
    status: str  # "need_approval"|"applied_ok"|"reverted_failed_tests"|"error"
    detail: str
    backups_dir: Optional[Path] = None

def self_improve_from_text(
    settings: Settings,
    patch_text: str,
    *,
    base_dir: Path,
    require_approval_safe: bool = True,
    approve: bool = False,
    run_tests: bool = True,
    db_path: Optional[Path] = None,
) -> ImproveOutcome:
    # killswitch
    kill = Path(settings.general.kill_switch_path)
    if kill.exists():
        return ImproveOutcome("error", f"Kill-switch présent: {kill}")

    # approval policy
    if require_approval_safe and settings.general.profile == "safe" and not approve:
        return ImproveOutcome("need_approval", "Profil safe: approbation requise (--approve)")

    # dry-run check apply
    try:
        apply_patch_text(base_dir, patch_text, allow_roots=ALLOWED_DIRS, dry_run=True)
    except (PatchSecurityError, PatchFormatError) as e:
        return ImproveOutcome("error", f"Validation patch échouée: {e}")

    # apply for real
    try:
        res = apply_patch_text(base_dir, patch_text, allow_roots=ALLOWED_DIRS, dry_run=False)
    except (PatchSecurityError, PatchFormatError) as e:
        return ImproveOutcome("error", f"Application patch échouée: {e}")

    # run tests
    if run_tests:
        rr = run_pytest(base_dir)
        ok = (rr.returncode == 0)
    else:
        ok = True
        rr = None  # type: ignore

    # journal
    dbp = Path(db_path) if db_path else Path(settings.memory.db_path)
    try:
        db = MemoryDB(dbp)
        db.add_event("auto_improve", "info" if ok else "error",
                     "apply_patch_and_test",
                     {"status": "ok" if ok else "fail", "backups_dir": str(res.backups_dir),
                      "changed": [str(p) for (p,_) in res.changed]})
        db.close()
    except Exception:
        pass

    if ok:
        return ImproveOutcome("applied_ok", f"Tests OK ({len(res.changed)} fichier(s) modifiés)", backups_dir=res.backups_dir)
    else:
        # revert from backups
        for (path, _) in res.changed:
            backup = res.backups_dir / path.relative_to(base_dir)
            if backup.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup, path)
        return ImproveOutcome("reverted_failed_tests", "Tests échoués: modifications revert", backups_dir=res.backups_dir)
