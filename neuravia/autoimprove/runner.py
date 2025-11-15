from __future__ import annotations

import shutil
import sys
import subprocess
from pathlib import Path
from typing import Any, Iterable, Sequence

from ..config import Settings
from .patcher import (
    apply_patch_text,
    PatchFormatError,
    PatchSecurityError,
    PatchResult,
)

__all__ = ["run_pytest", "apply_patch_and_test", "self_improve_entry"]

# Répertoires autorisés pour l'application de patchs
ALLOWED_DIRS: list[Path] = [Path("neuravia"), Path("tests"), Path("config")]


def run_pytest(
    base_dir: Path | None = None,
    extra_args: Sequence[str] | None = None,
    timeout_sec: float | None = None,
) -> subprocess.CompletedProcess[str]:
    """
    Lance pytest et renvoie l'objet CompletedProcess (avec .returncode, .stdout, .stderr).

    Compatibilité tests:
      - test_auto_runner.py appelle run_pytest(tmp_path, timeout_sec=60)
      - workflow.py appelle run_pytest(base_dir)
    """
    cmd = [sys.executable, "-m", "pytest", "-q"]
    if extra_args:
        cmd.extend(list(extra_args))

    cp: subprocess.CompletedProcess[str] = subprocess.run(
        cmd,
        cwd=str(base_dir) if base_dir else None,
        text=True,
        capture_output=True,
        timeout=timeout_sec,
    )
    return cp


def _normalize_changed(changed: Iterable[Any] | None) -> list[str]:
    """
    Convertit PatchResult.changed en liste de chemins (str).
    Accepte: str | Path | tuple(..., path-like, ...) | autres types (repr).
    """
    out: list[str] = []
    if not changed:
        return out
    for item in changed:
        if isinstance(item, (str, Path)):
            out.append(str(item))
            continue
        if isinstance(item, tuple):
            taken = False
            for elem in item:
                if isinstance(elem, (str, Path)):
                    out.append(str(elem))
                    taken = True
                    break
            if not taken:
                out.append(str(item))
            continue
        out.append(str(item))
    return out


def _revert_from_backups(backups_dir: Path | None, base_dir: Path) -> bool:
    """
    Restaure les fichiers depuis le dossier de sauvegarde produit par apply_patch_text.
    Fallback simple si l'API du patcher ne fournit pas de fonction de revert dédiée.
    """
    if not backups_dir:
        return False
    b = Path(backups_dir)
    if not b.exists():
        return False

    for src in b.rglob("*"):
        if src.is_file():
            rel = src.relative_to(b)
            dst = base_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    return True


def _dry_run_validate(base_dir: Path, patch_text: str) -> PatchResult | None:
    """
    Valide le patch en dry-run. Retourne PatchResult (ou None selon l'implémentation).
    Lève PatchSecurityError / PatchFormatError en cas d'échec.
    """
    return apply_patch_text(
        base_dir,
        patch_text,
        allow_roots=ALLOWED_DIRS,
        dry_run=True,
    )


def _apply_for_real(base_dir: Path, patch_text: str) -> PatchResult:
    """
    Applique réellement le patch et renvoie PatchResult (avec backups_dir, changed, ...).
    Lève PatchSecurityError / PatchFormatError en cas d'échec.
    """
    res = apply_patch_text(
        base_dir,
        patch_text,
        allow_roots=ALLOWED_DIRS,
        dry_run=False,
    )
    if not isinstance(res, PatchResult):
        # Par sécurité si l'implémentation retournait autre chose
        raise RuntimeError("apply_patch_text n'a pas renvoyé un PatchResult attendu.")
    return res


def apply_patch_and_test(
    settings: Settings,
    patch_path: Path | str,
    approve: bool = False,
) -> dict[str, Any]:
    """
    Applique un patch texte et exécute pytest.
    Retour JSON-like:
      {
        "status": "need_approval" | "applied_ok" | "reverted_failed_tests" | "error",
        "backups_dir": str | None,
        "changed": [str, ...],
        "pytest_ok": bool | None,
        "pytest_output": str | None,
        "error": str | None
      }
    """
    base_dir = Path.cwd()

    # Kill-switch
    kill = Path(settings.general.kill_switch_path)
    if kill.exists():
        return {
            "status": "error",
            "backups_dir": None,
            "changed": None,
            "pytest_ok": None,
            "pytest_output": None,
            "error": f"Kill-switch présent: {kill}",
        }

    # Politique d'approbation pour le profil safe
    if settings.general.profile == "safe" and not approve:
        return {
            "status": "need_approval",
            "backups_dir": None,
            "changed": None,
            "pytest_ok": None,
            "pytest_output": None,
            "error": None,
        }

    # Lecture du patch
    patch_path = Path(patch_path)
    try:
        patch_text = patch_path.read_text(encoding="utf-8")
    except Exception as e:
        return {
            "status": "error",
            "backups_dir": None,
            "changed": None,
            "pytest_ok": None,
            "pytest_output": None,
            "error": f"Lecture patch échouée: {e}",
        }

    # Validation dry-run
    try:
        _dry_run_validate(base_dir, patch_text)
    except (PatchSecurityError, PatchFormatError) as e:
        return {
            "status": "error",
            "backups_dir": None,
            "changed": None,
            "pytest_ok": None,
            "pytest_output": None,
            "error": f"Validation patch échouée: {e}",
        }

    # Application réelle
    try:
        res = _apply_for_real(base_dir, patch_text)
    except (PatchSecurityError, PatchFormatError) as e:
        return {
            "status": "error",
            "backups_dir": None,
            "changed": None,
            "pytest_ok": None,
            "pytest_output": None,
            "error": f"Application patch échouée: {e}",
        }

    backups_dir = res.backups_dir
    changed_list = _normalize_changed(res.changed)

    # Lancer les tests
    rr = run_pytest(base_dir)
    pytest_ok = rr.returncode == 0

    if pytest_ok:
        status = "applied_ok"
        err_msg = None
    else:
        # revert et signaler l'échec
        _revert_from_backups(backups_dir, base_dir)
        status = "reverted_failed_tests"
        err_msg = None

    return {
        "status": status,
        "backups_dir": str(Path(backups_dir)) if backups_dir else None,
        "changed": changed_list,
        "pytest_ok": pytest_ok,
        "pytest_output": rr.stdout if rr else None,
        "error": err_msg,
    }


def self_improve_entry(
    settings: Settings,
    patch_path: Path | str,
    approve: bool = False,
) -> dict[str, Any]:
    """
    Point d'entrée utilisé par la CLI.
    """
    return apply_patch_and_test(settings, patch_path=patch_path, approve=approve)
