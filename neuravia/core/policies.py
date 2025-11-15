from __future__ import annotations
from pathlib import Path

def load_prompt_resource() -> str:
    """Charge un prompt/policy si disponible (facultatif)."""
    for candidate in [
        Path.cwd() / "Prompt_Neuravia_Autonomy.md",
        Path("policies.md"),
    ]:
        try:
            if candidate.exists():
                return candidate.read_text(encoding="utf-8")[:20000]
        except Exception:
            pass
    # Fallback minimal
    return (
        "# Neuravia Policies (Phase 3)\n"
        "- Offline-first, exécution prudente.\n"
        "- Pas d'élévation de privilèges.\n"
        "- Respecter sandbox et allowlists.\n"
    )
