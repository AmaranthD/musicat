from pathlib import Path

from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .library import db, importer
from .library import metadata as metadata_reader
from .models import Track, UnrecognizedItem

STATIC_DIR = Path(__file__).parent / "static"

SORT_COLUMNS = {
    "title": "title",
    "artist": "artist",
    "duration": "duration",
    "imported_at": "imported_at",
    "date": "imported_at",
}
EDITABLE_FIELDS = {"title", "artist", "album"}


def _track_dict(row) -> dict:
    data = Track.from_row(row).to_dict()
    data["has_cover"] = (config.library_dir() / f"{data['content_hash']}.cover").exists()
    return data


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
                result = importer.import_file(
                    upload.filename or "sem-nome", data, connection
                )
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
    def library(search: str = "", sort: str = "imported_at") -> dict:
        column = SORT_COLUMNS.get(sort, "imported_at")
        direction = "DESC" if column == "imported_at" else "ASC"
        connection = db.connect()
        try:
            query = "SELECT * FROM tracks"
            params: list[str] = []
            if search:
                query += " WHERE title LIKE ? OR artist LIKE ? OR album LIKE ?"
                term = f"%{search}%"
                params = [term, term, term]
            query += f" ORDER BY {column} {direction}"
            tracks = [_track_dict(row) for row in connection.execute(query, params)]
            unrecognized = [
                UnrecognizedItem.from_row(row).to_dict()
                for row in connection.execute(
                    "SELECT * FROM unrecognized ORDER BY imported_at DESC"
                )
            ]
        finally:
            connection.close()
        return {"tracks": tracks, "unrecognized": unrecognized}

    @app.patch("/api/tracks/{track_id}")
    def update_track(track_id: int, payload: dict = Body(...)) -> dict:
        fields = {key: value for key, value in payload.items() if key in EDITABLE_FIELDS}
        if not fields:
            raise HTTPException(status_code=400, detail="nenhum campo editável enviado")
        connection = db.connect()
        try:
            row = connection.execute(
                "SELECT * FROM tracks WHERE id = ?", (track_id,)
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="faixa não encontrada")
            assignments = ", ".join(f"{key} = ?" for key in fields)
            connection.execute(
                f"UPDATE tracks SET {assignments} WHERE id = ?",
                [*fields.values(), track_id],
            )
            connection.commit()
            updated = connection.execute(
                "SELECT * FROM tracks WHERE id = ?", (track_id,)
            ).fetchone()
        finally:
            connection.close()
        return _track_dict(updated)

    @app.get("/api/tracks/{track_id}/cover")
    def track_cover(track_id: int) -> FileResponse:
        connection = db.connect()
        try:
            row = connection.execute(
                "SELECT content_hash FROM tracks WHERE id = ?", (track_id,)
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise HTTPException(status_code=404, detail="faixa não encontrada")
        cover_path = config.library_dir() / f"{row['content_hash']}.cover"
        if not cover_path.exists():
            raise HTTPException(status_code=404, detail="sem capa")
        media_type = metadata_reader.guess_media_type(cover_path.read_bytes())
        return FileResponse(cover_path, media_type=media_type)

    @app.delete("/api/unrecognized/{item_id}")
    def remove_unrecognized(item_id: int) -> dict:
        connection = db.connect()
        try:
            row = connection.execute(
                "SELECT * FROM unrecognized WHERE id = ?", (item_id,)
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="item não encontrado")
            if row["stored_name"]:
                (config.unrecognized_dir() / row["stored_name"]).unlink(missing_ok=True)
            connection.execute("DELETE FROM unrecognized WHERE id = ?", (item_id,))
            connection.commit()
        finally:
            connection.close()
        return {"status": "removed"}

    @app.post("/api/unrecognized/{item_id}/reprocess")
    def reprocess_unrecognized(item_id: int) -> dict:
        connection = db.connect()
        try:
            row = connection.execute(
                "SELECT * FROM unrecognized WHERE id = ?", (item_id,)
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="item não encontrado")
            if not row["stored_name"]:
                raise HTTPException(status_code=400, detail="arquivo indisponível")
            stored = config.unrecognized_dir() / row["stored_name"]
            if not stored.exists():
                raise HTTPException(status_code=400, detail="arquivo indisponível")
            result = importer.import_file(row["filename"], stored.read_bytes(), connection)
            if result["status"] != "unrecognized":
                stored.unlink(missing_ok=True)
                connection.execute(
                    "DELETE FROM unrecognized WHERE id = ?", (item_id,)
                )
                connection.commit()
        finally:
            connection.close()
        return result

    return app
