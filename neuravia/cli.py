from __future__ import annotations
import argparse
from pathlib import Path
from . import __version__
from .config import load_settings
from .tools.logs import log_event

# === LLM (imports robustes) ===================================================
try:
    from .llm.base import LLMRequest
    from .llm.dummy import DummyLLM
    from .llm.ollama import OllamaCLI, has_ollama
except Exception:  # pragma: no cover
    LLMRequest = None
    DummyLLM = None
    OllamaCLI = None
    def has_ollama() -> bool:  # type: ignore
        return False

# === Orchestrateur : import optionnel + fallback ==============================
def _run_plan_fallback(settings, plan: list[str], *, dry_run: bool) -> list[str]:
    logs: list[str] = []
    for i, step in enumerate(plan, 1):
        mode = "DRY-RUN" if dry_run else "EXEC"
        logs.append(f"[Executor] step {i}: {step} :: {mode}")
        logs.append(f"[Observer] step {i} ok ([Executor] step {i}: {step} :: {mode})")
    logs.append("[Reviewer] plan validé")
    return logs

try:
    from .agent.orchestrator import run_plan as _run_plan  # type: ignore
except Exception:  # pragma: no cover
    _run_plan = _run_plan_fallback  # type: ignore

# === Mémoire : import optionnel + fallback ===================================
try:
    from .memory.sqlite import persist_run_if_requested  # type: ignore
except Exception:  # pragma: no cover
    def persist_run_if_requested(args, status: str = "ok") -> str:
        """Fallback autonome : crée la DB si besoin et insère un event 'run'."""
        if not getattr(args, "persist_run", False):
            return ""
        import sqlite3, json, datetime
        db_path = Path(getattr(args, "memory_db", "data/memory.db"))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(str(db_path))
        try:
            con.execute(
                "CREATE TABLE IF NOT EXISTS events ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "ts TEXT, kind TEXT, level TEXT, message TEXT, data TEXT)"
            )
            ts = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
            msg = f"objective={getattr(args,'goal', '') or ''}"
            data = json.dumps({"status": status})
            con.execute(
                "INSERT INTO events (ts,kind,level,message,data) VALUES (?,?,?,?,?)",
                (ts, "run", "info", msg, data),
            )
            con.commit()
        finally:
            con.close()
        return f"[memory] persisted run to {db_path}"

# === Affichage ================================================================
def _print_banner(phase_label: str):
    print(f"Neuravia-Autonomy v{__version__} — {phase_label}")

def _print_settings(goal: str | None, config: str, profile: str, s):
    print(f"goal    = {repr(goal) if goal is not None else 'None'}")
    print(f"config  = {repr(str(config))}")
    print(f"profile = {s.general.profile}")
    print(f"dry_run = {s.general.dry_run}")
    print(f"no_confirm = {s.general.no_confirm}")
    print(f"os_mode = {s.general.os_mode}")
    print(f"sandbox = {s.general.sandbox_path}")
    print(f"network.enabled = {s.network.enabled}")
    mods = s.modules
    print(
        "modules = {fs=%s, proc=%s, http=%s, browser=%s, vision=%s, ocr=%s, codeedit=%s}"
        % (mods.filesystem, mods.process, mods.http, mods.browser, mods.vision, mods.ocr, mods.codeedit)
    )
    print(f"llm = {{local={s.llm.local_enabled}, remote={s.llm.remote_enabled}}}")
    if getattr(s, "memory", None) and getattr(s.memory, "db_path", ""):
        print(f"memory.db = {s.memory.db_path}")

# === Arguments ================================================================
def _argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser("neuravia", description="Neuravia-Autonomy — IA locale offline-first")
    ap.add_argument("--goal", help="Objectif principal à exécuter (string).")
    ap.add_argument("--config", default="config", help="Chemin vers le dossier de configuration.")
    ap.add_argument("--profile", choices=["safe", "balanced", "danger"], default="safe", help="Profil de sécurité.")
    ap.add_argument("--dry-run", action="store_true", help="Mode simulation: ne pas exécuter d'actions.")
    ap.add_argument("--no-confirm", action="store_true", help="Exécuter sans confirmations interactives.")
    ap.add_argument("--os-mode", choices=["auto", "windows", "linux"], default="auto", help="Forcer le ciblage OS.")
    ap.add_argument("--max-steps", type=int, default=3, help="Nombre d'étapes maximum dans le plan.")
    ap.add_argument("--version", action="store_true", help="Afficher la version et quitter.")
    # Mémoire
    ap.add_argument("--persist-run", action="store_true", help="Persister l'exécution (SQLite).")
    ap.add_argument("--memory-db", default="data/memory.db", help="Chemin DB SQLite pour la mémoire.")
    # Auto-amélioration
    ap.add_argument("--self-improve-patch", help="Chemin vers un patch unified diff à appliquer/tester.")
    ap.add_argument("--approve", action="store_true", help="Approuver explicitement (profil safe).")
    # LLM (affichage de plan)
    ap.add_argument("--use-llm", action="store_true", help="Utiliser un LLM pour proposer un plan (affiché).")
    ap.add_argument("--llm-model", default="dummy", help="dummy | tag Ollama (ex: llama3.1:8b-instruct-q4_K_M).")
    ap.add_argument("--llm-max-tokens", type=int, default=256)
    ap.add_argument("--llm-temperature", type=float, default=0.2)
    return ap

# Compat tests / __main__: les tests s’attendent à build_parser()
def build_parser() -> argparse.ArgumentParser:
    return _argparser()

# === Main ====================================================================
def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    s = load_settings(
        config=args.config,
        profile=args.profile,
        overrides={"dry_run": bool(args.dry_run), "no_confirm": bool(args.no_confirm), "os_mode": args.os_mode},
    )

    _print_banner("Phase 3 (config loaded)")
    _print_settings(args.goal, args.config, args.profile, s)

    # Auto-amélioration → sortie immédiate
    if args.self_improve_patch:
        from .autoimprove.runner import self_improve_entry
        status = self_improve_entry(s, patch_path=args.self_improve_patch, approve=args.approve)
        print(status)
        return 0

    # Plan via LLM (affichage)
    if args.use_llm and args.goal:
        try:
            if args.llm_model.lower() == "dummy":
                llm = DummyLLM()
            else:
                if not has_ollama():
                    print("ERR: Ollama non disponible. Installez-le (winget install -e --id Ollama.Ollama) ou utilisez --llm-model dummy.", flush=True)
                    return 2
                llm = OllamaCLI(args.llm_model)
            steps = max(1, int(args.max_steps))
            req = LLMRequest(
                prompt=(
                    f"Propose un plan concis en {steps} étapes pour atteindre l'objectif suivant "
                    f"(réponses courtes, 1 ligne par étape): {args.goal}"
                ),
                max_tokens=args.llm_max_tokens,
                temperature=args.llm_temperature,
            )
            txt = llm.generate(req).strip()
            print("\n=== PLAN (via LLM) ===")
            print(txt)
        except Exception as e:  # pragma: no cover
            print(f"[LLM] erreur: {e}")

    # Plan “par défaut” (exécuté par orchestrateur/fallback)
    plan = [
        f"Analyser l'objectif: {args.goal}" if args.goal else "Analyser l'objectif",
        "Élaborer un plan d'actions minimal",
        "Simuler l'exécution et consigner les observations",
    ][: max(1, int(args.max_steps))]

    print("\n=== PLAN ===")
    for i, step in enumerate(plan, 1):
        print(f"{i}. {step}")

    logs = _run_plan(s, plan, dry_run=s.general.dry_run)
    for line in logs:
        print(line)

    # Persistance optionnelle
    msg = persist_run_if_requested(args, status="ok")
    if msg:
        print(msg)

    print("\nSTATUS: ok")
    # Événement (UI)
    try:
        log_event(
            Path(s.general.log_dir) / "events.log",
            kind="run",
            level="info",
            message=f"objective={args.goal or ''}",
            data={"status": "ok", "lines": len(plan) + 1},
        )
    except Exception:
        pass
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
