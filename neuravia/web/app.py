from __future__ import annotations
import json, mimetypes, asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncIterator
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from ..memory.db import MemoryDB

def _norm(p: Path) -> Path:
    return p.resolve()

def _is_under(target: Path, root: Path) -> bool:
    try:
        _norm(target).relative_to(_norm(root))
        return True
    except Exception:
        return False

def create_app(db_path: str, sandbox_path: str, log_dir: str, *, profile: str = "safe", kill_switch_path: str | None = None) -> FastAPI:
    app = FastAPI(title="Neuravia Dashboard", docs_url=None, redoc_url=None)

    static_dir = Path(__file__).parent / "static"
    tmpl_dir = Path(__file__).parent / "templates"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    templates = Jinja2Templates(directory=str(tmpl_dir))

    app.state.db_path = db_path
    app.state.sandbox = _norm(Path(sandbox_path))
    app.state.log_dir = _norm(Path(log_dir))
    app.state.profile = profile
    app.state.kill_switch_path = kill_switch_path

    def _with_db() -> MemoryDB:
        return MemoryDB(app.state.db_path)

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/api/kill")
    def kill() -> dict:
        if not app.state.kill_switch_path:
            raise HTTPException(status_code=400, detail="Kill-switch file path non configuré")
        p = Path(app.state.kill_switch_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("KILLED", encoding="utf-8")
        return {"status": "engaged", "path": str(p)}

    @app.get("/api/stats")
    def stats() -> dict:
        db = _with_db()
        try:
            cur = db.conn.cursor()
            cur.execute("SELECT COUNT(*) FROM events")
            ev = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM actions")
            ac = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM artifacts")
            ar = cur.fetchone()[0]
            return {"events": ev, "actions": ac, "artifacts": ar}
        finally:
            db.close()

    @app.get("/api/events")
    def list_events(limit: int = 50) -> list[dict]:
        db = _with_db()
        try:
            return db.list_events(limit=max(1, min(500, limit)))
        finally:
            db.close()

    async def _sse_generator(last_id: int | None, once: bool = False):
        poll_interval = 1.0
        _last = last_id or 0
        while True:
            db = _with_db()
            try:
                cur = db.conn.cursor()
                cur.execute("SELECT id, ts, kind, level, message, data FROM events WHERE id>? ORDER BY id ASC LIMIT 100", (_last,))
                rows = cur.fetchall()
            finally:
                db.close()
            if rows:
                for r in rows:
                    _last = int(r[0])
                    payload = {"id": r[0], "ts": r[1], "kind": r[2], "level": r[3], "message": r[4], "data": r[5]}
                    chunk = f"id: {_last}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")
                    yield chunk
                if once:
                    break
            else:
                if once:
                    break
                await asyncio.sleep(poll_interval)

    @app.get("/api/events/stream")
    async def events_stream(last_id: int | None = Query(default=None), once: bool = Query(default=False)) -> StreamingResponse:
        gen = _sse_generator(last_id=last_id, once=once)
        return StreamingResponse(gen, media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon():
        icon = static_dir / "favicon.ico"
        if icon.exists():
            return FileResponse(icon)
        return HTMLResponse(status_code=404, content="")

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        db = _with_db()
        try:
            cur = db.conn.cursor()
            cur.execute("SELECT COUNT(*) FROM events")
            ev = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM actions")
            ac = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM artifacts")
            ar = cur.fetchone()[0]
            latest = db.list_events(limit=10)
        finally:
            db.close()
        return templates.TemplateResponse(
            request,
            "index.html",
            {"stats": {"events": ev, "actions": ac, "artifacts": ar}, "latest": latest, "title": "Neuravia Dashboard", "profile": app.state.profile},
        )

    # -------- FICHIERS (sandbox) --------
    ALLOWED_EXTS = {".txt",".log",".json",".png",".jpg",".jpeg",".bmp",".tif",".tiff",".csv",".md",".pdf"}
    MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024  # 20 MB

    def _safe_join_sandbox(relpath: str) -> Path:
        p = Path(relpath)
        full = _norm(app.state.sandbox / p) if not p.is_absolute() else _norm(p)
        if not _is_under(full, app.state.sandbox):
            raise HTTPException(status_code=403, detail="Chemin hors sandbox")
        return full

    def _iter_files(root: Path) -> list[dict]:
        out: list[dict] = []
        for f in root.rglob("*"):
            if f.is_file():
                rel = f.relative_to(root).as_posix()
                out.append({"path": rel, "size": f.stat().st_size, "ext": f.suffix.lower()})
        out.sort(key=lambda x: x["path"])
        return out

    @app.get("/api/files")
    def api_files() -> dict:
        root = app.state.sandbox
        root.mkdir(parents=True, exist_ok=True)
        files = [x for x in _iter_files(root) if (not ALLOWED_EXTS or x["ext"] in ALLOWED_EXTS)]
        return {"root": str(root), "count": len(files), "items": files[:2000]}

    @app.get("/files", response_class=HTMLResponse)
    def files_page(request: Request):
        return templates.TemplateResponse(request, "files.html", {"title": "Fichiers (sandbox)", "profile": app.state.profile})

    @app.get("/files/download")
    def download(path: str):
        target = _safe_join_sandbox(path)
        if not target.exists() or not target.is_file():
            raise HTTPException(status_code=404, detail="Fichier introuvable")
        if target.suffix.lower() not in ALLOWED_EXTS:
            raise HTTPException(status_code=403, detail="Extension non autorisée")
        if target.stat().st_size > MAX_DOWNLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Fichier trop volumineux")
        mime, _ = mimetypes.guess_type(target.name)
        return FileResponse(str(target), media_type=mime or "application/octet-stream", filename=target.name)

    return app
