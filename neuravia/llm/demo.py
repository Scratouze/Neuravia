from __future__ import annotations
import argparse, sys
from .base import LLMRequest
from .dummy import DummyLLM
from .ollama import OllamaCLI, has_ollama

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser("neuravia.llm.demo", description="Démo LLM local (dummy/ollama)")
    ap.add_argument("--goal", required=True, help="Objectif en texte libre")
    ap.add_argument("--model", default="dummy", help="dummy | <nom_ollama> (ex: llama3.1:8b-instruct)")
    ap.add_argument("--max-tokens", type=int, default=256)
    ap.add_argument("--temperature", type=float, default=0.2)
    args = ap.parse_args(argv)

    if args.model.lower() == "dummy":
        llm = DummyLLM()
    else:
        if not has_ollama():
            print("ERR: Ollama non disponible. Installez-le ou utilisez --model dummy.", file=sys.stderr)
            return 2
        llm = OllamaCLI(args.model)

    req = LLMRequest(prompt=args.goal, max_tokens=args.max_tokens, temperature=args.temperature)
    txt = llm.generate(req).strip()
    print("=== PLAN (model:", args.model, ") ===")
    print(txt)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
