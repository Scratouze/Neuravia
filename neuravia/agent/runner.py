from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from neuravia.llm.base import LLMRequest
from neuravia.llm.ollama import OllamaCLI
from neuravia.memory.db import MemoryDB


MEMORY_PATH = Path("data/memory.db")


@dataclass
class StepRecord:
    goal: str
    step: int
    content: str
    ts: str


@dataclass
class ReviewRecord:
    goal: str
    summary: str
    what_worked: str
    improvements: str
    ts: str


# -------------------- Mémoire : chargement --------------------


def _load_past_steps(db: MemoryDB, goal: str, limit: int = 10) -> List[StepRecord]:
    """
    Récupère les derniers steps pour ce goal, depuis la table events (kind='agent_step').
    On utilise une requête SQL directe pour filtrer sur le goal (= message).
    """
    cur = db.conn.cursor()
    cur.execute(
        """
        SELECT id, ts, kind, level, message, data
        FROM events
        WHERE kind = 'agent_step' AND message = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (goal, limit),
    )
    rows = cur.fetchall()
    out: List[StepRecord] = []
    for _id, ts, _kind, _level, message, data in rows:
        try:
            d = json.loads(data) if data else {}
        except Exception:
            d = {}
        step = int(d.get("step") or 0)
        content = str(d.get("content") or "")
        out.append(StepRecord(goal=message, step=step, content=content, ts=ts))
    return out


def _load_past_reviews(db: MemoryDB, goal: str, limit: int = 5) -> List[ReviewRecord]:
    """
    Récupère les dernières revues (kind='agent_review') pour ce goal.
    Les revues sont stockées dans events(message=goal, data=JSON).
    """
    cur = db.conn.cursor()
    cur.execute(
        """
        SELECT id, ts, kind, level, message, data
        FROM events
        WHERE kind = 'agent_review' AND message = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (goal, limit),
    )
    rows = cur.fetchall()
    out: List[ReviewRecord] = []
    for _id, ts, _kind, _level, message, data in rows:
        try:
            d = json.loads(data) if data else {}
        except Exception:
            d = {}
        out.append(
            ReviewRecord(
                goal=message,
                summary=str(d.get("summary") or ""),
                what_worked=str(d.get("what_worked") or ""),
                improvements=str(d.get("improvements") or ""),
                ts=ts,
            )
        )
    return out


def _format_memory_block(steps: List[StepRecord], reviews: List[ReviewRecord]) -> str:
    """
    Construit un bloc texte à injecter dans le prompt à partir des steps + reviews.
    """
    lines: List[str] = []

    if steps:
        lines.append("Contexte des tentatives précédentes (steps) :")
        for s in steps:
            preview = s.content.replace("\n", " ")
            if len(preview) > 180:
                preview = preview[:177] + "..."
            lines.append(f"- (step {s.step}) {preview}")
        lines.append("")

    if reviews:
        lines.append("Synthèse des revues précédentes :")
        for r in reviews:
            sum_preview = r.summary.replace("\n", " ")
            if len(sum_preview) > 180:
                sum_preview = sum_preview[:177] + "..."
            imp_preview = r.improvements.replace("\n", " ")
            if len(imp_preview) > 180:
                imp_preview = imp_preview[:177] + "..."
            lines.append(f"- [revue] {sum_preview}")
            if imp_preview:
                lines.append(f"          Améliorations suggérées : {imp_preview}")
        lines.append("")

    return "\n".join(lines).strip()


# -------------------- Mémoire : écriture --------------------


def _store_step(db: MemoryDB, goal: str, step: int, content: str) -> None:
    """
    Enregistre un step individuel dans la table events (kind='agent_step').
    """
    db.add_event(
        kind="agent_step",
        level="info",
        message=goal,
        data={"step": step, "content": content},
    )


def _store_review(db: MemoryDB, goal: str, review: dict) -> None:
    """
    Enregistre une revue structurée de run dans events (kind='agent_review').
    review est déjà un dict JSON-safe.
    """
    db.add_event(
        kind="agent_review",
        level="info",
        message=goal,
        data=review,
    )


# -------------------- LLM helpers --------------------


def _build_step_prompt(
    goal: str,
    step_index: int,
    max_steps: int,
    memory_block: str,
) -> str:
    """
    Prompt pour générer une action à un step donné, en tenant compte de la mémoire.
    """
    parts: List[str] = []
    parts.append("Tu es Neuravia, un agent autonome exécutant un plan en plusieurs étapes.")
    parts.append(f"Objectif global : \"{goal}\".")
    parts.append("")

    if memory_block:
        parts.append("Voici le contexte de tentatives précédentes pour cet objectif :")
        parts.append(memory_block)
        parts.append("")
        parts.append(
            "Essaie de t'inspirer de ce qui a bien fonctionné et d'éviter les redondances ou les actions absurdes."
        )

    parts.append("")
    parts.append(f"Tu es à l'étape {step_index} sur {max_steps} dans ce nouveau run.")
    parts.append(
        "Réponds UNIQUEMENT par une phrase ou deux décrivant précisément l'action que tu vas faire à cette étape."
    )
    parts.append(
        "Ne numérote pas toi-même les étapes et n'ajoute pas de préambule du type 'Étape 1 :', sauf si c'est naturel."
    )

    return "\n".join(parts)


def _build_review_prompt(goal: str, steps: List[str], memory_block: str) -> str:
    """
    Prompt pour demander au LLM une auto-critique structurée du run.
    La réponse doit être du JSON.
    """
    steps_txt = "\n".join(f"- Step {i+1}: {s}" for i, s in enumerate(steps))

    parts: List[str] = []
    parts.append("Tu es Neuravia, un agent autonome qui s'auto-évalue après un run.")
    parts.append(f"Objectif du run : \"{goal}\".")
    parts.append("")
    if memory_block:
        parts.append("Contexte de tentatives précédentes (résumé) :")
        parts.append(memory_block)
        parts.append("")
    parts.append("Voici les étapes que tu as exécutées lors de ce run :")
    parts.append(steps_txt)
    parts.append("")
    parts.append(
        "Produis une auto-critique STRUCTURÉE en JSON STRICTEMENT VALIDE, avec exactement les clés suivantes :"
    )
    parts.append(
        '{ "summary": "...", "what_worked": "...", "improvements": "..." }'
    )
    parts.append(
        "- summary : résumé très court (1–2 phrases) du run.\n"
        "- what_worked : ce qui a bien fonctionné ou semblait pertinent.\n"
        "- improvements : ce que tu pourrais faire différemment ou mieux la prochaine fois pour ce type de but."
    )
    parts.append("Ne renvoie QUE le JSON, sans texte avant ou après.")

    return "\n".join(parts)


def _generate_review_json(llm: OllamaCLI, goal: str, steps: List[str], memory_block: str) -> Optional[dict]:
    """
    Appelle le LLM pour obtenir une revue JSON. Tolérant aux erreurs :
    - si le JSON ne parse pas, on stocke une version dégradée.
    """
    if not steps:
        return None

    prompt = _build_review_prompt(goal, steps, memory_block)
    raw = llm.generate(LLMRequest(prompt=prompt))

    # Tentative de parse JSON strict
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("JSON retourné n'est pas un objet.")
        # On force les 3 clés attendues, au cas où
        return {
            "summary": str(data.get("summary") or ""),
            "what_worked": str(data.get("what_worked") or ""),
            "improvements": str(data.get("improvements") or ""),
            "raw": raw,
        }
    except Exception:
        # fallback : on stocke juste le texte brut
        return {
            "summary": "",
            "what_worked": "",
            "improvements": "",
            "raw": raw,
        }


# -------------------- Boucle principale de l'agent --------------------


def run_agent(goal: str, model: str, max_steps: int = 3) -> None:
    """
    Boucle principale de l'agent autonome.
    - charge la mémoire (steps + reviews)
    - exécute max_steps steps
    - enregistre chaque step dans memory.db
    - génère et enregistre une revue à la fin
    """
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = MemoryDB(MEMORY_PATH)

    try:
        # 1) Charger la mémoire existante pour ce goal
        past_steps = _load_past_steps(db, goal, limit=10)
        past_reviews = _load_past_reviews(db, goal, limit=5)
        memory_block = _format_memory_block(past_steps, past_reviews)

        if memory_block:
            print("=== MÉMOIRE CHARGÉE ===")
            print(memory_block)
            print("========================")
            print()

        llm = OllamaCLI(model=model)

        # 2) Exécution des steps
        steps_text: List[str] = []
        for i in range(1, max_steps + 1):
            prompt = _build_step_prompt(
                goal=goal,
                step_index=i,
                max_steps=max_steps,
                memory_block=memory_block,
            )
            out = llm.generate(LLMRequest(prompt=prompt)).strip()
            steps_text.append(out)
            print(f"[STEP {i}] {out}")
            _store_step(db, goal=goal, step=i, content=out)

        # 3) Auto-critique / revue du run
        try:
            review = _generate_review_json(llm, goal, steps_text, memory_block)
            if review is not None:
                _store_review(db, goal, review)
                print()
                print("=== REVUE DU RUN ENREGISTRÉE EN MÉMOIRE ===")
                if review.get("summary"):
                    print("Résumé :", review["summary"])
                if review.get("improvements"):
                    print("Améliorations :", review["improvements"])
                print("===========================================")
        except Exception as e:
            # On ne casse jamais l'agent pour une revue ratée
            print()
            print(f"[WARN] Impossible d'enregistrer la revue du run : {e}")

        # 4) Affichage du résultat final (comme avant)
        print()
        print("=== RÉSULTAT FINAL ===")
        for s in steps_text:
            print(s)

    finally:
        db.close()


# -------------------- CLI --------------------


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="neuravia.agent",
        description="Neuravia — Agent autonome (Phase 9)",
    )
    parser.add_argument(
        "--goal",
        required=True,
        help="Objectif global de l'agent (ce qu'il doit accomplir).",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=3,
        help="Nombre d'étapes maximum pour l'agent.",
    )
    parser.add_argument(
        "--model",
        default="llama3.1:8b-instruct-q4_K_M",
        help="Nom du modèle Ollama (voir `ollama list`).",
    )

    args = parser.parse_args(argv)

    run_agent(goal=args.goal, model=args.model, max_steps=args.max_steps)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
