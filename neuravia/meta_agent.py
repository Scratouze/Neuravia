# neuravia/meta_agent.py

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from textwrap import dedent
from typing import List, Dict, Any

from neuravia.llm.base import LLMRequest
from neuravia.llm.ollama import OllamaCLI
from neuravia.memory.db import MemoryDB

DEFAULT_DB_PATH = Path("data/memory.db")


def _load_full_history(db: MemoryDB, goal: str, max_steps: int = 1000, max_reviews: int = 200):
    """
    Charge tout l'historique (steps + reviews) pour un goal donné.
    On reste filtré sur message == goal pour ne pas mélanger les objectifs.
    """
    all_steps = [
        e for e in db.list_events(kind="agent_step", limit=max_steps)
        if e.get("message") == goal
    ]
    all_reviews = [
        e for e in db.list_events(kind="agent_review", limit=max_reviews)
        if e.get("message") == goal
    ]

    all_steps.sort(key=lambda e: e["id"])
    all_reviews.sort(key=lambda e: e["id"])
    return all_steps, all_reviews


def _shorten(text: str, max_len: int = 160) -> str:
    text = (text or "").replace("\n", " ").strip()
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def _build_history_blocks(steps, reviews) -> tuple[str, str]:
    """
    Construit deux blocs texte :
      - un bloc d'historique de steps
      - un bloc d'historique de reviews
    dans un format compact pour le prompt du méta-agent.
    """
    step_lines: list[str] = []
    for e in steps:
        data: Dict[str, Any] = e.get("data") or {}
        sid = data.get("step") or "?"
        title = data.get("title") or ""
        action = data.get("action") or data.get("content") or ""
        # petite "signature" du step
        line = f"- [step {sid}] {title} — {action}"
        step_lines.append(_shorten(line))

    review_lines: list[str] = []
    for e in reviews:
        data: Dict[str, Any] = e.get("data") or {}
        summary = (data.get("summary") or "").strip()
        improvements = data.get("improvements") or []
        if summary:
            review_lines.append(f"*Résumé :* {summary}")
        for imp in improvements:
            review_lines.append(f"*Amélioration :* {imp}")

    history_block = "\n".join(step_lines) if step_lines else "(aucun step enregistré)"
    reviews_block = "\n".join(review_lines) if review_lines else "(aucune review enregistrée)"

    return history_block, reviews_block


def _build_meta_prompt(goal: str, steps, reviews, target_steps: int) -> str:
    """
    Prompt du méta-agent : à partir de tout l'historique, produire un master-plan JSON.
    """
    history_block, reviews_block = _build_history_blocks(steps, reviews)

    prompt = f"""
Tu es un architecte d'IA senior chargé de synthétiser un plan global à partir de nombreuses tentatives
d'un agent précédent.

OBJECTIF GLOBAL :
{goal}

Tu disposes de l'historique suivant :

=== HISTORIQUE DES ÉTAPES (tous runs confondus) ===
{history_block}

=== COMMENTAIRES ET REVUES PRÉCÉDENTES ===
{reviews_block}

Ta mission :
- Dédupliquer et fusionner les idées similaires.
- Corriger les défauts signalés dans les revues (redondance, manque de tests, manque d'analyse des risques, etc.).
- Proposer un plan global cohérent en environ {target_steps} grandes étapes (pas besoin de respecter exactement le nombre, mais reste entre {max(3, target_steps-2)} et {target_steps+2}).
- Chaque étape doit être :
  - claire,
  - actionnable,
  - non redondante,
  - alignée avec l'objectif global.
- Quand c'est pertinent, inclure :
  - au moins une étape pour les TESTS / ÉVALUATION,
  - au moins une étape pour les RISQUES / ÉTHIQUE / LIMITES,
  - au moins une étape pour l'APPRENTISSAGE CONTINU ou l'amélioration du système.

FORMAT DE SORTIE STRICT (JSON valide, sans texte avant ni après) :

{{
  "goal": "<rappel concis de l'objectif>",
  "steps": [
    {{
      "index": 1,
      "title": "<titre très court>",
      "action": "<ce qui est fait concrètement dans l'étape>",
      "expected_result": "<ce que cette étape permet d'obtenir>",
      "role": "<un mot parmi : 'analysis', 'design', 'implementation', 'evaluation', 'governance', 'safety', 'meta'>"
    }},
    ...
  ],
  "notes": "<optionnel : une ou deux phrases de remarques globales sur le plan>"
}}

Rappels importants :
- Tu DOIS renvoyer du JSON valide.
- Pas de Markdown, pas de commentaires, pas d'explications hors du JSON.
- Les index d'étapes doivent commencer à 1 et être croissants.
"""
    return dedent(prompt).strip()


def _extract_json_block(text: str) -> str | None:
    """
    Essaie d'extraire un bloc JSON depuis la sortie brute du modèle.
    On recherche le premier '{{' ou '[' et le dernier '}}' ou ']'.
    """
    if not text:
        return None

    # On cherche un début plausible d'objet ou de liste JSON
    start_match = re.search(r"[\{\[]", text)
    if not start_match:
        return None
    start = start_match.start()

    # On cherche la dernière accolade ou crochet fermant
    end_match = re.search(r"[\}\]]\s*$", text.strip(), re.DOTALL)
    if end_match:
        # end_match est sur le texte strip(), on se contente de strip global
        trimmed = text[start:].strip()
        return trimmed

    # fallback : on prend du début trouvé jusqu'à la fin
    return text[start:].strip()


def _parse_master_plan(text: str) -> dict:
    """
    Parse la sortie du LLM en JSON Python.
    Si le JSON est invalide, essaie de le corriger minimalement ou lève une ValueError.
    """
    block = _extract_json_block(text)
    if not block:
        raise ValueError("Impossible d'extraire un bloc JSON dans la sortie du modèle.")

    try:
        return json.loads(block)
    except json.JSONDecodeError as e:
        # petite tentative de correction très basique (par exemple trailing commas)
        # on peut affiner si besoin plus tard
        cleaned = re.sub(r",\s*([\}\]])", r"\\1", block)
        return json.loads(cleaned)


def _print_master_plan(plan: dict) -> None:
    """
    Affiche le master-plan de façon lisible dans le terminal.
    """
    goal = plan.get("goal") or ""
    steps = plan.get("steps") or []
    notes = plan.get("notes")

    print("=== MASTER PLAN SYNTHÉTISÉ ===")
    if goal:
        print("Objectif réinterprété :", goal)
        print()

    for s in steps:
        idx = s.get("index")
        title = s.get("title") or ""
        action = s.get("action") or ""
        expected = s.get("expected_result") or ""
        role = s.get("role") or ""

        role_str = f" [{role}]" if role else ""
        print(f"Étape {idx}{role_str} — {title}")
        print(f"  ACTION : {action}")
        if expected:
            print(f"  RÉSULTAT ATTENDU : {expected}")
        print()

    if notes:
        print("Notes :", notes)
    print("=========================================\n")


def run_meta_agent(
    goal: str,
    model: str,
    target_steps: int,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """
    Agent "méta" : lit toute la mémoire pour un goal donné et produit un master-plan global.
    """
    db = MemoryDB(str(db_path))

    steps, reviews = _load_full_history(db, goal)
    if not steps and not reviews:
        print("Aucun historique trouvé pour ce goal dans la mémoire.")
        return

    print("=== PHASE 12 : SYNTHÈSE GLOBALE ===")
    print(f"Goal : {goal}")
    print(f"- Steps trouvés : {len(steps)}")
    print(f"- Reviews trouvées : {len(reviews)}")
    print("Génération du master-plan...\n")

    llm = OllamaCLI(model)
    prompt = _build_meta_prompt(goal, steps, reviews, target_steps=target_steps)
    raw = llm.generate(LLMRequest(prompt=prompt))

    try:
        plan = _parse_master_plan(raw)
    except Exception as e:
        print("Erreur lors du parsing du JSON renvoyé par le modèle :")
        print(e)
        print("Sortie brute du modèle :")
        print(raw)
        return

    # Affichage
    _print_master_plan(plan)

    # Sauvegarde en mémoire
    db.add_event(
        kind="agent_masterplan",
        level="info",
        message=goal,
        data=plan,
    )
    print("Master-plan enregistré dans la mémoire (kind='agent_masterplan').")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="neuravia.meta_agent",
        description="Neuravia — Méta-agent de synthèse (Phase 12 : master-plan global à partir de l'historique).",
    )
    parser.add_argument(
        "--goal",
        required=True,
        help="Objectif global pour lequel on veut synthétiser un master-plan.",
    )
    parser.add_argument(
        "--target-steps",
        type=int,
        default=10,
        help="Nombre cible d'étapes dans le master-plan (approx.).",
    )
    parser.add_argument(
        "--model",
        default="llama3.1:8b-instruct-q4_K_M",
        help="Nom du modèle Ollama (voir `ollama list`).",
    )
    parser.add_argument(
        "--memory-db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Chemin de la base SQLite de mémoire persistante.",
    )

    args = parser.parse_args(argv)

    run_meta_agent(
        goal=args.goal,
        model=args.model,
        target_steps=args.target_steps,
        db_path=args.memory_db,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
