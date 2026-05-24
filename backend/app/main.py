from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import APP_NAME, PROJECT_ROOT, ensure_runtime_dirs
from app.db.database import init_db


def create_app() -> FastAPI:
    ensure_runtime_dirs()
    init_db()
    app = FastAPI(title=APP_NAME, version="2.0.0-dev")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api")
    _mount_frontend_dist(app)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "message": f"系统内部错误：{exc}", "data": None},
        )

    return app


def _mount_frontend_dist(app: FastAPI) -> None:
    dist_dir = PROJECT_ROOT / "frontend" / "dist"
    index_file = dist_dir / "index.html"
    assets_dir = dist_dir / "assets"
    if not index_file.exists():
        return
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    favicon_headers = {"Cache-Control": "no-store, max-age=0"}

    @app.get("/favicon.ico", include_in_schema=False)
    def serve_favicon_ico() -> FileResponse:
        return FileResponse(
            dist_dir / "favicon.ico",
            media_type="image/x-icon",
            headers=favicon_headers,
        )

    @app.get("/favicon.svg", include_in_schema=False)
    def serve_favicon_svg() -> FileResponse:
        return FileResponse(
            dist_dir / "favicon.svg",
            media_type="image/svg+xml",
            headers=favicon_headers,
        )

    @app.get("/favicon.png", include_in_schema=False)
    def serve_favicon_png() -> FileResponse:
        return FileResponse(
            dist_dir / "favicon.png",
            media_type="image/png",
            headers=favicon_headers,
        )

    @app.get("/")
    def serve_index() -> FileResponse:
        return FileResponse(index_file)

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str) -> FileResponse:
        requested_file = (dist_dir / full_path).resolve()
        if requested_file.exists() and requested_file.is_file() and str(requested_file).startswith(str(dist_dir.resolve())):
            return FileResponse(requested_file)
        return FileResponse(index_file)


app = create_app()
