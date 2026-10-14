from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .library import db, importer
from .models import Track, UnrecognizedItem

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    config.ensure_dirs()
    db.init_db()

    app = FastAPI(title="Musicat")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.post("/api/import")
    async def import_tracks(files: list[UploadFile] = File(...)) -> dict:
        imported: list[dict] = []
        duplicates: list[dict] = []
        unrecognized: list[dict] = []
        connection = db.connect()
        try:
            for upload in files:
                data = await upload.read()
                result = importer.import_file(upload.filename or "sem-nome", data, connection)
                {
                    "imported": imported,
                    "duplicate": duplicates,
                    "unrecognized": unrecognized,
                }[result["status"]].append(result)
        finally:
            connection.close()
        return {
            "imported": imported,
            "duplicates": duplicates,
            "unrecognized": unrecognized,
        }

    @app.get("/api/library")
    def library() -> dict:
        connection = db.connect()
        try:
            tracks = [
                Track.from_row(row).to_dict()
                for row in connection.execute(
                    "SELECT * FROM tracks ORDER BY imported_at DESC"
                )
            ]
            unrecognized = [
                UnrecognizedItem.from_row(row).to_dict()
                for row in connection.execute(
                    "SELECT * FROM unrecognized ORDER BY imported_at DESC"
                )
            ]
        finally:
            connection.close()
        return {"tracks": tracks, "unrecognized": unrecognized}

    return app
