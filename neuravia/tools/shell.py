from __future__ import annotations
import subprocess, platform
from dataclasses import dataclass
from typing import Sequence
from ..config import Settings
from .errors import ShellSecurityError
from ..security.kill import check_kill

__all__ = ["CommandResult", "run_command", "ShellSecurityError"]

@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str

def _allowed_from_settings(settings: Settings) -> set[str]:
    # récupère l'allowlist depuis la config (profil safe/balanced/danger)
    try:
        lst = settings.security.shell_allowlist
    except Exception:
        lst = ["echo"]
    return {c.lower() for c in lst}

def run_command(settings: Settings, command: str, args: Sequence[str] | None = None, *, timeout: int = 10) -> CommandResult:
    check_kill(settings.general.kill_switch_path)  # interrompt si kill-switch présent
    args = list(args or [])
    allowed = _allowed_from_settings(settings)
    if command.lower() not in allowed:
        raise ShellSecurityError(f"Commande non autorisée: {command}")

    # Windows: 'echo' via cmd /c pour un comportement cohérent
    if platform.system().lower().startswith("win") and command.lower() == "echo":
        full = ["cmd", "/c", "echo"] + args
    else:
        full = [command] + args

    p = subprocess.run(full, text=True, capture_output=True, timeout=timeout, check=False)
    return CommandResult(p.returncode, p.stdout.strip(), p.stderr.strip())
