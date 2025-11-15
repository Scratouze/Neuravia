from __future__ import annotations
import argparse
import uvicorn
from ..config import load_settings
from .app import create_app

def main() -> None:
    parser = argparse.ArgumentParser(description="Neuravia Local UI (FastAPI)")
    parser.add_argument("--config", type=str, default="config", help="Dossier ou fichier config (par défaut: ./config)")
    parser.add_argument("--profile", type=str, default="safe", help="Profil config (safe|balanced|danger)")
    parser.add_argument("--db", type=str, default=None, help="Chemin base SQLite (défaut: config.memory.db_path)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Hôte (par défaut: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Port (défaut: 8765)")
    args = parser.parse_args()

    settings = load_settings(args.config, args.profile)
    db_path = args.db or settings.memory.db_path
    app = create_app(
        db_path=db_path,
        sandbox_path=settings.general.sandbox_path,
        log_dir=settings.general.log_dir,
        profile=settings.general.profile,
        kill_switch_path=settings.general.kill_switch_path,
    )

    uvicorn.run(app, host=args.host, port=int(args.port), log_level="info")

if __name__ == "__main__":
    main()
