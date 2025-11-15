from __future__ import annotations
from .base import LLM, LLMRequest

class DummyLLM(LLM):
    """
    LLM déterministe pour tests/démo.
    Renvoie toujours 3 étapes numérotées en fonction du prompt.
    """
    def generate(self, req: LLMRequest) -> str:
        goal = req.prompt.strip().splitlines()[0][:200]
        return (
            f"1. Analyser l'objectif: {goal}\n"
            f"2. Élaborer un plan d'actions minimal\n"
            f"3. Simuler l'exécution et consigner les observations\n"
        )
