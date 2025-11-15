from __future__ import annotations

import argparse

from .loop import AgentLoop
from neuravia.llm.ollama import OllamaCLI
from neuravia.llm.base import LLMRequest


class OllamaAdapter:
    """
    Petit wrapper pour adapter OllamaCLI à l'interface attendue par AgentLoop :
    un objet simplement appelable : llm(prompt: str) -> str
    """

    def __init__(self, model: str):
        self.cli = OllamaCLI(model=model)

    def __call__(self, prompt: str) -> str:
        req = LLMRequest(prompt=prompt)
        return self.cli.generate(req)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Neuravia — Agent autonome (Phase 9)")

    p.add_argument(
        "--goal",
        required=True,
        help="Objectif global de l'agent (ce qu'il doit accomplir).",
    )
    p.add_argument(
        "--max-steps",
        type=int,
        default=5,
        help="Nombre d'étapes maximum pour l'agent.",
    )
    p.add_argument(
        "--model",
        default="llama3.1:8b-instruct-q4_K_M",
        help="Nom du modèle Ollama (voir `ollama list`).",
    )

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # LLM = wrapper autour de ton OllamaCLI existant
    llm = OllamaAdapter(model=args.model)

    agent = AgentLoop(
        goal=args.goal,
        llm=llm,               # simplement appelé comme llm(prompt)
        max_steps=args.max_steps,
    )

    result = agent.run()

    print("\n=== RÉSULTAT FINAL ===")
    print(result)
    return 0
