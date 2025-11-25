from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from textwrap import dedent
from typing import List

from neuravia.llm.base import LLMRequest
from neuravia.llm.ollama import OllamaCLI
from neuravia.memory.db import MemoryDB

DEFAULT_DB_PATH = Path("data/memory.db")


# ---------------------------------------------------------------------------
# Chargement de la mémoire "locale" (steps + reviews)
# ---------------------------------------------------------------------------

def _load_context(db: MemoryDB, goal: str, max_steps: int = 10, max_reviews: int = 5):
    """Récupère les derniers steps et revues pour ce goal."""
    all_steps = [
        e for e in db.list_events(kind="agent_step", limit=200)
        if e.get("message") == goal
    ]
    all_reviews = [
        e for e in db.list_events(kind="agent_review", limit=50)
        if e.get("message") == goal
    ]

    all_steps.sort(key=lambda e: e["id"])
    all_reviews.sort(key=lambda e: e["id"])

    steps_ctx = all_steps[-max_steps:]
    reviews_ctx = all_reviews[-max_reviews:]
    return steps_ctx, reviews_ctx


def _load_masterplan(db: MemoryDB, goal: str) -> dict | None:
    """
    Récupère le master-plan le plus pertinent pour ce goal.

    On cherche les events kind='agent_masterplan' et on essaie de faire
    matcher sur le goal (via message ou data['goal']). Pour l'instant,
    on prend le plus récent qui semble lié.
    """
    candidates = db.list_events(kind="agent_masterplan", limit=20)
    best: dict | None = None
    best_score = 0

    goal_norm = goal.lower().strip()

    for e in candidates:
        data = e.get("data") or {}
        msg = (e.get("message") or "").lower().strip()
        mp_goal = (data.get("goal") or "").lower().strip()

        score = 0
        if goal_norm and mp_goal:
            if goal_norm in mp_goal or mp_goal in goal_norm:
                score += 2
        if goal_norm and msg:
            if goal_norm in msg or msg in goal_norm:
                score += 1

        # fallback : si on n'a aucun score, on utilise quand même le plus récent
        if score == 0 and best is None:
            best = data
            best_score = 0
        elif score > best_score:
            best = data
            best_score = score

    return best


def _print_masterplan(masterplan: dict) -> None:
    """Affiche un résumé du master-plan détecté (pour l'humain)."""
    if not masterplan:
        return

    goal = masterplan.get("goal") or "Objectif non spécifié"
    steps = masterplan.get("steps") or []

    print("=== MASTER-PLAN DÉTECTÉ (mémoire) ===")
    print(f"Objectif master-plan : {goal}")
    for s in steps:
        idx = s.get("index")
        title = s.get("title") or ""
        role = s.get("role") or ""
        action = s.get("action") or ""
        print(f"- Étape {idx} [{role}]: {title} — {action}")
    notes = masterplan.get("notes")
    if notes:
        print()
        print("Notes :", notes)
    print("=====================================")
    print()




def _print_context(steps_ctx, reviews_ctx) -> None:
    """Affiche un résumé de la mémoire avant de lancer un nouveau run."""
    if not steps_ctx and not reviews_ctx:
        return

    print("=== MÉMOIRE CHARGÉE ===")
    if steps_ctx:
        print("Contexte des tentatives précédentes (steps) :")
        for e in reversed(steps_ctx):
            data = e.get("data") or {}
            step = data.get("step", "?")
            content = (
                data.get("content")
                or data.get("action")
                or ""
            )
            content = content.replace("\n", " ").strip()
            if len(content) > 120:
                content = content[:117] + "..."
            print(f"- (step {step}) {content}")
    if reviews_ctx:
        print()
        print("Synthèse des revues précédentes :")
        for e in reversed(reviews_ctx):
            data = e.get("data") or {}
            summary = (data.get("summary") or "").strip()
            if summary:
                print(f"- [revue] {summary}")
                improvements = data.get("improvements")
                if improvements:
                    print("          Améliorations suggérées :", improvements)
    print("========================")
    print()


# ---------------------------------------------------------------------------
# Chargement du MASTER-PLAN (Phase 12.1)
# ---------------------------------------------------------------------------

def _load_masterplan(db: MemoryDB, goal: str) -> Optional[Dict[str, Any]]:
    """
    Récupère le dernier master-plan pour ce goal (kind='agent_masterplan').

    Le meta-agent enregistre typiquement :
      data = {
        "goal": "...",
        "steps": [
            {"index": 1, "title": "...", "action": "...", "expected_result": "...", "role": "..."},
            ...
        ],
        "notes": "..."
      }
    """
    plans = [
        e for e in db.list_events(kind="agent_masterplan", limit=20)
        if e.get("message") == goal
    ]
    if not plans:
        return None

    plans.sort(key=lambda e: e["id"])
    latest = plans[-1]
    data = latest.get("data") or {}

    # on normalise un peu pour être sûr
    goal_mp = data.get("goal") or goal
    steps = data.get("steps") or []
    notes = data.get("notes") or ""

    return {
        "goal": goal_mp,
        "steps": steps,
        "notes": notes,
    }


def _print_masterplan(masterplan: Dict[str, Any]) -> None:
    """Affiche un résumé du master-plan s'il existe."""
    if not masterplan:
        return

    print("=== MASTER-PLAN DÉTECTÉ  ===")
    print(f"Objectif master-plan : {masterplan.get('goal')}")
    steps = masterplan.get("steps") or []
    for s in steps:
        idx = s.get("index")
        title = s.get("title") or "Sans titre"
        role = s.get("role") or "?"
        action = (s.get("action") or "").replace("\n", " ").strip()
        if len(action) > 100:
            action = action[:97] + "..."
        print(f"- Étape {idx} [{role}]: {title} — {action}")
    notes = (masterplan.get("notes") or "").strip()
    if notes:
        print()
        print("Notes :", notes)
    print("=======================================")
    print()


def _masterplan_block(masterplan: Optional[Dict[str, Any]]) -> str:
    """Construit un bloc de texte à injecter dans le prompt à partir du master-plan."""
    if not masterplan:
        return "(aucun master-plan enregistré pour cet objectif)"

    lines = []
    steps = masterplan.get("steps") or []
    for s in steps:
        idx = s.get("index")
        title = s.get("title") or "Sans titre"
        role = s.get("role") or "?"
        action = (s.get("action") or "").replace("\n", " ").strip()
        lines.append(f"- Étape {idx} [{role}] : {title} — {action}")
    notes = (masterplan.get("notes") or "").strip()
    if notes:
        lines.append("")
        lines.append(f"Notes : {notes}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Construction des prompts d'étapes
# ---------------------------------------------------------------------------

def _build_step_prompt(
    goal: str,
    step_index: int,
    max_steps: int,
    run_steps: List[str],
    mem_steps,
    mem_reviews,
    masterplan: dict | None = None,
) -> str:
    """Construit le prompt pour une étape de planification, en intégrant la mémoire ET le master-plan."""

    # --- Contexte du run en cours ---
    if run_steps:
        run_block = "\n".join(
            f"- Étape {i+1}: {s}" for i, s in enumerate(run_steps)
        )
    else:
        run_block = "(aucune étape encore dans ce run)"

    # --- Contexte des anciens steps mémorisés ---
    mem_steps_block_lines: list[str] = []
    for e in mem_steps:
        data = e.get("data") or {}
        s_idx = data.get("step")
        content = (
            data.get("content")
            or data.get("action")
            or ""
        )
        # certains steps (issus du meta_agent) ont un dict complet dans "step"
        if isinstance(s_idx, dict):
            # on essaie d'en extraire quelque chose de lisible
            s_title = s_idx.get("title") or ""
            s_action = s_idx.get("action") or ""
            content = s_action or s_title or content

        content = (content or "").replace("\n", " ").strip()
        if len(content) > 120:
            content = content[:117] + "..."
        mem_steps_block_lines.append(f"- Ancien step {s_idx}: {content}")
    mem_steps_block = (
        "\n".join(mem_steps_block_lines)
        if mem_steps_block_lines
        else "(aucune étape mémorisée pertinente)"
    )

    # --- Contexte des revues mémorisées ---
    mem_reviews_block_lines: list[str] = []
    for e in mem_reviews:
        data = e.get("data") or {}
        summary = (data.get("summary") or "").strip()
        if summary:
            mem_reviews_block_lines.append(f"- {summary}")
    mem_reviews_block = (
        "\n".join(mem_reviews_block_lines)
        if mem_reviews_block_lines
        else "(aucune revue enregistrée)"
    )

    # --- Contexte du master-plan (phase 12) ---
    if masterplan:
        mp_goal = masterplan.get("goal") or goal
        mp_steps = masterplan.get("steps") or []
        mp_lines: list[str] = []
        for s in mp_steps:
            idx = s.get("index")
            title = s.get("title") or ""
            role = s.get("role") or ""
            action = s.get("action") or ""
            line = f"- [{idx}][{role}] {title}: {action}"
            mp_lines.append(line.strip())
        masterplan_block = (
            "\n".join(mp_lines)
            if mp_lines
            else "(master-plan présent mais sans étapes détaillées)"
        )
    else:
        masterplan_block = "(aucun master-plan enregistré pour cet objectif)"

    prompt = f"""
Tu es un agent autonome de planification qui construit des plans en plusieurs étapes NUMÉROTÉES pour atteindre un objectif.

OBJECTIF GLOBAL :
{goal}

MASTER-PLAN GLOBAL ACTUEL (phase 12) :
{masterplan_block}

Tu dois maintenant produire l'ÉTAPE {step_index} sur {max_steps} pour CE RUN.

Règles importantes :
- L'étape doit être CONCRÈTE et ACTIONNABLE (ce que tu fais, configures ou décides).
- Elle doit être COMPLÉMENTAIRE des autres étapes de ce run : pas de redite, pas de paraphrase.
- Elle doit rester COHÉRENTE avec la trajectoire globale du master-plan ci-dessus.
- Tu dois tirer parti des tentatives précédentes et de leurs critiques pour améliorer ce plan.
- Ne réécris pas mot pour mot une ancienne étape.
- Si l'objectif mentionne plusieurs aspects,
  assure-toi qu'au fil des {max_steps} étapes de CE RUN, ces aspects soient progressivement tous couverts.

Contexte de ce run (étapes déjà prévues) :
{run_block}

Exemples d'étapes issues de runs précédents (à NE PAS répéter telles quelles) :
{mem_steps_block}

Synthèse des revues précédentes :
{mem_reviews_block}

FORMAT DE SORTIE OBLIGATOIRE (en français) :

TITRE: <un très court résumé de l'étape, en quelques mots>
ACTION: <ce que tu fais concrètement dans cette étape, phrase ou deux maximum>
RÉSULTAT ATTENDU: <ce que cette étape permet d'obtenir ou de sécuriser>

Ne rajoute rien en dehors de ces trois lignes.
"""
    return dedent(prompt).strip()



# ---------------------------------------------------------------------------
# Prompts de revue
# ---------------------------------------------------------------------------

def _build_review_prompt(goal: str, steps: List[str]) -> str:
    """Prompt de revue de run pour produire un résumé + des améliorations en JSON strict."""
    steps_block = "\n".join(f"- Étape {i+1}: {s}" for i, s in enumerate(steps, start=1))
    prompt = f"""
Tu es un observateur critique qui analyse un plan en plusieurs étapes.

OBJECTIF :
{goal}

PLAN OBTENU :
{steps_block}

Tâche :
- Tu dois évaluer ce plan et proposer des pistes d'amélioration pour un futur run.

⚠️ FORMAT DE RÉPONSE OBLIGATOIRE (JSON UNIQUEMENT) :

Réponds EXCLUSIVEMENT avec un JSON valide, dans ce format précis :

{{
  "summary": "une phrase ou deux qui résume le plan",
  "improvements": [
    "amélioration 1 (phrase courte, concrète)",
    "amélioration 2 (optionnelle)",
    "amélioration 3 (optionnelle)"
  ]
}}

Règles importantes :
- Ne rajoute AUCUN texte avant ou après le JSON.
- N'utilise que des doubles guillemets pour les chaînes (format JSON strict).
- "summary" doit être une chaîne de caractères en français.
- "improvements" doit être une liste (éventuellement vide) de chaînes.
"""
    return dedent(prompt).strip()



def _parse_review_output(text: str):
    """
    Parse la revue pour extraire Résumé + Améliorations.

    1) On essaie d'abord de parser un JSON strict du type :
       {"summary": "...", "improvements": ["...", "..."]}

    2) Si ça échoue, on retombe sur l'ancien parsing tolérant
       (sections "Résumé" / "Améliorations").
    """

    # ---------- 1) Tentative de parsing JSON strict ----------
    json_obj = None

    # On essaie de récupérer le bloc JSON principal (entre le premier '{' et le dernier '}')
    if "{" in text and "}" in text:
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            json_str = text[start:end]
            json_obj = json.loads(json_str)
        except Exception:
            json_obj = None

    if isinstance(json_obj, dict):
        summary = json_obj.get("summary")
        improvements = json_obj.get("improvements") or []

        # Normalisation douce
        if isinstance(summary, str):
            summary = summary.strip()
        else:
            summary = None

        if not isinstance(improvements, list):
            improvements = []

        cleaned_improvements: list[str] = []
        for item in improvements:
            if isinstance(item, str):
                s = item.strip()
                if s:
                    cleaned_improvements.append(s)

        if summary or cleaned_improvements:
            return summary or None, cleaned_improvements

    # ---------- 2) Fallback : ancien parsing texte libre ----------
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    summary_lines: list[str] = []
    improvements_fallback: list[str] = []
    mode: str | None = None

    for line in lines:
        low = line.lower()

        # Détection de la section Résumé
        if low.startswith("résumé"):
            # On enlève tout préfixe "Résumé", "Résumé :", "Résumé** :" etc.
            parts = re.split(r"résumé\s*[:\-]?\s*", line, maxsplit=1, flags=re.IGNORECASE)
            if len(parts) == 2 and parts[1].strip():
                summary_lines.append(parts[1].strip())
            mode = "summary"
            continue

        # Détection de la section Améliorations
        if low.startswith("améliorations"):
            mode = "improv"
            continue

        if mode == "summary":
            summary_lines.append(line)
        elif mode == "improv":
            # Lignes d'améliorations (puces ou pas)
            if line.startswith(("-", "*")):
                line = line.lstrip("-* ").strip()
            improvements_fallback.append(line)

    def clean(s: str) -> str:
        return s.strip().strip("*").strip()

    summary = clean(" ".join(summary_lines))
    base = summary.lower().strip(":").strip()
    if base in ("", "résumé", "resume"):
        summary = None

    improvements_fallback = [clean(i) for i in improvements_fallback if clean(i)]

    return summary, improvements_fallback


# ---------------------------------------------------------------------------
# Parsing des steps (TITRE / ACTION / RÉSULTAT ATTENDU)
# ---------------------------------------------------------------------------

def _parse_step_output(text: str) -> dict:
    """
    Parse la sortie d'une étape structurée.

    On attend idéalement le format :
    TITRE: ...
    ACTION: ...
    RÉSULTAT ATTENDU: ...

    Mais on reste tolérant si le modèle dérive un peu
    (markdown **, espaces, tirets, etc.).
    """

    def _clean_line(line: str) -> str:
        line = line.strip()
        line = re.sub(r"^[\-\*\s]+", "", line)
        return line.strip()

    title = ""
    action = ""
    expected = ""

    lines = [l.rstrip() for l in text.splitlines() if l.strip()]
    for raw_line in lines:
        line = _clean_line(raw_line)
        low = line.lower()

        low_no_accents = (
            low.replace("é", "e")
               .replace("è", "e")
               .replace("ê", "e")
               .replace("à", "a")
               .replace("ù", "u")
        )

        if low_no_accents.startswith("titre"):
            parts = line.split(":", 1)
            if len(parts) == 2:
                title = parts[1].strip()
            else:
                title = line.strip()
            continue

        if low_no_accents.startswith("action"):
            parts = line.split(":", 1)
            if len(parts) == 2:
                action = parts[1].strip()
            else:
                action = line.strip()
            continue

        if (
            low_no_accents.startswith("resultat attendu")
            or "resultat attendu" in low_no_accents
        ):
            parts = line.split(":", 1)
            if len(parts) == 2:
                expected = parts[1].strip()
            else:
                expected = line.strip()
            continue

    raw = text.strip()

    if not action and raw:
        action = raw
    if not title:
        title = "Étape planifiée"
    if not expected:
        expected = ""

    title = title.strip("* ").strip()
    action = action.strip("* ").strip()

    return {
        "title": title,
        "action": action,
        "expected_result": expected or None,
        "raw": raw,
    }


# ---------------------------------------------------------------------------
# Boucle principale
# ---------------------------------------------------------------------------

def run_agent(goal: str, model: str, max_steps: int, db_path: Path = DEFAULT_DB_PATH) -> None:
    """Boucle principale de l'agent autonome."""
    db = MemoryDB(str(db_path))

    # 1) Charger le contexte depuis la mémoire
    mem_steps, mem_reviews = _load_context(db, goal)

    # 1.bis) Charger un éventuel master-plan
    masterplan = _load_masterplan(db, goal)

    _print_context(mem_steps, mem_reviews)
    if masterplan:
        _print_masterplan(masterplan)

    # 2) Préparer le LLM
    llm = OllamaCLI(model)
    run_steps: list[str] = []

    # 3) Génération des étapes
    for i in range(1, max_steps + 1):
        prompt = _build_step_prompt(
            goal=goal,
            step_index=i,
            max_steps=max_steps,
            run_steps=run_steps,
            mem_steps=mem_steps,
            mem_reviews=mem_reviews,
            masterplan=masterplan,
        )
        out = llm.generate(LLMRequest(prompt=prompt))
        parsed = _parse_step_output(out)
        step_text = parsed["action"] or parsed["raw"]

        print(f"[STEP {i}] {parsed['title']} — {parsed['action']}")

        run_steps.append(step_text)
        db.add_event(
            kind="agent_step",
            level="info",
            message=goal,
            data={
                "step": i,
                "content": step_text,           # compatibilité avec l'ancien format
                "title": parsed["title"],
                "action": parsed["action"],
                "expected_result": parsed["expected_result"],
                "raw": parsed["raw"],
            },
        )

    # 4) Revue globale du run
    review_prompt = _build_review_prompt(goal, run_steps)
    review_raw = llm.generate(LLMRequest(prompt=review_prompt))
    summary, improvements = _parse_review_output(review_raw)

    print("\n=== REVUE DU RUN ENREGISTRÉE EN MÉMOIRE ===")
    if summary:
        print(f"Résumé : {summary}")
    if improvements:
        print(f"Améliorations : {improvements}")
    print("===========================================\n")

    review_data: dict = {}
    if summary:
        review_data["summary"] = summary
    if improvements:
        review_data["improvements"] = improvements

    db.add_event(
        kind="agent_review",
        level="info",
        message=goal,
        data=review_data,
    )

    # 5) Afficher le plan final
    print("=== RÉSULTAT FINAL ===")
    for s in run_steps:
        print(s)
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="neuravia.agent",
        description="Neuravia — Agent autonome (planificateur avec mémoire persistante, master-plan Phase 12.1).",
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
    parser.add_argument(
        "--memory-db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Chemin de la base SQLite de mémoire persistante.",
    )

    args = parser.parse_args(argv)

    run_agent(goal=args.goal, model=args.model, max_steps=args.max_steps, db_path=args.memory_db)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
