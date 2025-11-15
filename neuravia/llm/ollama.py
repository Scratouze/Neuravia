from __future__ import annotations
import shutil, subprocess
from .base import LLM, LLMRequest
from ..security.kill import check_kill

def has_ollama() -> bool:
    return bool(shutil.which("ollama"))

class OllamaCLI(LLM):
    """
    Appelle 'ollama run <model>' en local (pas d'HTTP).
    Nécessite que le binaire 'ollama' soit sur le PATH (Windows: winget install Ollama.Ollama).
    """
    def __init__(self, model: str, *, extra: list[str] | None = None):
        self.model = model
        self.extra = list(extra or [])

    def generate(self, req: LLMRequest) -> str:
        # respecte le kill-switch global (chemin par défaut)
        check_kill("data/kill.switch")
        if not has_ollama():
            raise RuntimeError("Ollama non disponible (binaire 'ollama' introuvable sur PATH).")
        # Important: forcer UTF-8 pour éviter le mojibake sous Windows
        cmd = ["ollama", "run", self.model, req.prompt]
        p = subprocess.run(
            cmd,
            text=True,
            encoding="utf-8",   # ← forcer la décodage UTF-8
            errors="replace",   # ← jamais d'exception si caractère illégal
            capture_output=True,
            check=False,
        )
        if p.returncode != 0:
            raise RuntimeError(f"ollama run a échoué: {p.stderr.strip() or p.stdout.strip()}")
        out = p.stdout.strip()
        return out if out else "(réponse vide)"
