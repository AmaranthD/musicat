from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    config.ensure_dirs()

    app = FastAPI(title="Musicat")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return app
