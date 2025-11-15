from __future__ import annotations
import argparse, sys
from pathlib import Path
from . import __version__
from .config import load_settings, PROFILES, OS_MODES
from .core.orchestrator import run_goal

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="neuravia",
        description="Neuravia-Autonomy — IA locale offline-first (Phase 3/7).",
    )
    parser.add_argument("--goal", type=str, default=None, help="Objectif principal à exécuter (string).")
    parser.add_argument("--config", type=str, default=None, help="Chemin fichier/dossier config (defaults + profiles).")
    parser.add_argument("--profile", choices=PROFILES, default="safe", help="Profil: safe|balanced|danger.")
    parser.add_argument("--dry-run", action="store_true", help="Simulation: ne pas exécuter d'actions.")
    parser.add_argument("--no-confirm", action="store_true", help="Exécution sans confirmations.")
    parser.add_argument("--os-mode", choices=OS_MODES, default="auto", help="Ciblage OS (auto|windows|linux).")
    parser.add_argument("--max-steps", type=int, default=3, help="Nombre max d'étapes planifiées.")
    # Phase 5 options
    parser.add_argument("--persist-run", action="store_true", help="Écrire un événement de run dans SQLite.")
    parser.add_argument("--memory-db", type=str, default=None, help="Chemin SQLite (sinon config.memory.db_path).")
    # Phase 7 options
    parser.add_argument("--self-improve-patch", type=str, default=None, help="Chemin vers un patch unified-diff à appliquer/tester.")
    parser.add_argument("--approve", action="store_true", help="Approbation explicite de l'application du patch (profil safe).")
    parser.add_argument("--version", action="version", version=f"Neuravia {__version__}")
    return parser

def run_skeleton(args: argparse.Namespace) -> int:
    settings = load_settings(
        config=args.config,
        profile=args.profile,
        overrides={
            "profile": args.profile,
            "dry_run": bool(args.dry_run),
            "no_confirm": bool(args.no_confirm),
            "os_mode": args.os_mode,
        },
    )

    # 🔧 Rétabli pour compatibilité avec le test: "Phase 3 (config loaded)"
    header = (
        f"Neuravia-Autonomy v{__version__} — Phase 3 (config loaded)\n"
        f"goal    = {args.goal!r}\n"
        f"config  = {args.config!r}\n"
        f"profile = {settings.general.profile}\n"
        f"dry_run = {settings.general.dry_run}\n"
        f"no_confirm = {settings.general.no_confirm}\n"
        f"os_mode = {settings.general.os_mode}\n"
        f"sandbox = {settings.general.sandbox_path}\n"
        f"network.enabled = {settings.network.enabled}\n"
        f"modules = {{fs={settings.modules.filesystem}, proc={settings.modules.process}, http={settings.modules.http}, browser={settings.modules.browser}, vision={settings.modules.vision}, ocr={settings.modules.ocr}, codeedit={settings.modules.codeedit}}}\n"
        f"llm = {{local={settings.llm.local_enabled}, remote={settings.llm.remote_enabled}}}\n"
        f"memory.db = {settings.memory.db_path}"
    )
    print(header)

    # Mode auto-amélioration (Phase 7)
    if args.self_improve_patch:
        from .autoimprove.workflow import self_improve_from_text
        patch_path = Path(args.self_improve_patch)
        if not patch_path.exists():
            print(f"[self-improve] Patch introuvable: {patch_path}", file=sys.stderr)
            return 2
        patch_text = patch_path.read_text(encoding="utf-8")
        outcome = self_improve_from_text(
            settings,
            patch_text,
            base_dir=Path.cwd(),
            require_approval_safe=True,
            approve=bool(args.approve),
            run_tests=True,
            db_path=Path(args.memory_db) if args.memory_db else None,
        )
        print(f"[self-improve] status={outcome.status} detail={outcome.detail}")
        return 0 if outcome.status in ("applied_ok","need_approval") else 1

    # Exécution "classique"
    if args.goal:
        result = run_goal(settings, args.goal, max_steps=max(args.max_steps, 1))
        print("\n=== PLAN ===")
        for i, step in enumerate(result.plan.steps, 1):
            print(f"{i}. {step.description}")
        print("\n=== LOGS ===")
        for line in result.logs:
            print(line)
        print(f"\nSTATUS: {result.status}")
        if args.persist_run:
            from .memory.db import MemoryDB, persist_run
            db_path = args.memory_db or settings.memory.db_path
            db = MemoryDB(db_path)
            try:
                persist_run(db, args.goal, result.status, result.logs)
                print(f"[memory] persisted run to {db_path}")
            finally:
                db.close()
    return 0
