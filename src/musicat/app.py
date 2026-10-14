from pathlib import Path
import json
import mimetypes

from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .library import db, importer, playlists
from .library import metadata as metadata_reader
from .models import Track, UnrecognizedItem

STATIC_DIR = Path(__file__).parent / "static"

SORT_COLUMNS = {
    "title": "title",
    "artist": "artist",
    "duration": "duration",
    "imported_at": "imported_at",
}
EDITABLE_FIELDS = {"title", "artist", "album"}


def _track_dict(row) -> dict:
    data = Track.from_row(row).to_dict()
    data["has_cover"] = (config.library_dir() / f"{data['content_hash']}.cover").exists()
    return data


def _playlist_dict(playlist, tracks) -> dict:
    data = dict(playlist)
    data["tracks"] = [_track_dict(row) for row in tracks]
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
        with db.connection() as connection:
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
        return {
            "imported": imported,
            "duplicates": duplicates,
            "unrecognized": unrecognized,
        }

    @app.get("/api/library")
    def library(search: str = "", sort: str = "imported_at") -> dict:
        column = SORT_COLUMNS.get(sort, "imported_at")
        direction = "DESC" if column == "imported_at" else "ASC"
        with db.connection() as connection:
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
        return {"tracks": tracks, "unrecognized": unrecognized}

    @app.patch("/api/tracks/{track_id}")
    def update_track(track_id: int, payload: dict = Body(...)) -> dict:
        fields = {key: value for key, value in payload.items() if key in EDITABLE_FIELDS}
        if not fields:
            raise HTTPException(status_code=400, detail="nenhum campo editável enviado")
        with db.connection() as connection:
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
        return _track_dict(updated)

    @app.get("/api/tracks/{track_id}/stream")
    def stream_track(track_id: int) -> FileResponse:
        with db.connection() as connection:
            row = connection.execute(
                "SELECT stored_name FROM tracks WHERE id = ?", (track_id,)
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="faixa não encontrada")
        audio_path = config.library_dir() / row["stored_name"]
        if not audio_path.exists():
            raise HTTPException(status_code=404, detail="arquivo indisponível")
        media_type = mimetypes.guess_type(audio_path.name)[0] or "audio/mpeg"
        return FileResponse(audio_path, media_type=media_type)

    @app.get("/api/tracks/{track_id}/cover")
    def track_cover(track_id: int) -> FileResponse:
        with db.connection() as connection:
            row = connection.execute(
                "SELECT content_hash FROM tracks WHERE id = ?", (track_id,)
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="faixa não encontrada")
        cover_path = config.library_dir() / f"{row['content_hash']}.cover"
        if not cover_path.exists():
            raise HTTPException(status_code=404, detail="sem capa")
        media_type = metadata_reader.guess_media_type(cover_path.read_bytes())
        return FileResponse(cover_path, media_type=media_type)

    @app.put("/api/tracks/{track_id}/cover")
    async def upload_cover(track_id: int, cover: UploadFile = File(...)) -> dict:
        data = await cover.read()
        if metadata_reader.guess_media_type(data) == "application/octet-stream":
            raise HTTPException(status_code=400, detail="imagem inválida")
        with db.connection() as connection:
            row = connection.execute(
                "SELECT content_hash FROM tracks WHERE id = ?", (track_id,)
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="faixa não encontrada")
        (config.library_dir() / f"{row['content_hash']}.cover").write_bytes(data)
        return {"status": "saved"}

    @app.delete("/api/unrecognized/{item_id}")
    def remove_unrecognized(item_id: int) -> dict:
        with db.connection() as connection:
            row = connection.execute(
                "SELECT * FROM unrecognized WHERE id = ?", (item_id,)
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="item não encontrado")
            if row["stored_name"]:
                (config.unrecognized_dir() / row["stored_name"]).unlink(missing_ok=True)
            connection.execute("DELETE FROM unrecognized WHERE id = ?", (item_id,))
            connection.commit()
        return {"status": "removed"}

    @app.post("/api/unrecognized/{item_id}/reprocess")
    def reprocess_unrecognized(item_id: int) -> dict:
        with db.connection() as connection:
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
            result = importer.import_file(
                row["filename"], stored.read_bytes(), connection
            )
            if result["status"] != "unrecognized":
                stored.unlink(missing_ok=True)
                connection.execute(
                    "DELETE FROM unrecognized WHERE id = ?", (item_id,)
                )
                connection.commit()
        return result

    @app.post("/api/playlists")
    def create_playlist(payload: dict = Body(...)) -> dict:
        name = (payload.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="nome obrigatório")
        with db.connection() as connection:
            row = playlists.create(connection, name)
        return dict(row)

    @app.post("/api/playlists/random")
    def random_playlist(payload: dict = Body(default={})) -> dict:
        name = (payload.get("name") or "").strip() or "Aleatória"
        raw_size = payload.get("size")
        size = int(raw_size) if raw_size else None
        artist = payload.get("artist") or None
        fmt = payload.get("format") or None
        with db.connection() as connection:
            ids = playlists.random_track_ids(
                connection, artist=artist, fmt=fmt, size=size
            )
            created = playlists.create(connection, name)
            playlists.add_tracks(connection, created["id"], ids)
            playlist, tracks = playlists.get(connection, created["id"])
        return _playlist_dict(playlist, tracks)

    @app.get("/api/playlists")
    def list_playlists() -> dict:
        with db.connection() as connection:
            rows = playlists.list_all(connection)
        return {"playlists": [dict(row) for row in rows]}

    @app.get("/api/playlists/{playlist_id}")
    def get_playlist(playlist_id: int) -> dict:
        with db.connection() as connection:
            playlist, tracks = playlists.get(connection, playlist_id)
        if playlist is None:
            raise HTTPException(status_code=404, detail="playlist não encontrada")
        return _playlist_dict(playlist, tracks)

    @app.patch("/api/playlists/{playlist_id}")
    def rename_playlist(playlist_id: int, payload: dict = Body(...)) -> dict:
        name = (payload.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="nome obrigatório")
        with db.connection() as connection:
            row = playlists.rename(connection, playlist_id, name)
        if row is None:
            raise HTTPException(status_code=404, detail="playlist não encontrada")
        return dict(row)

    @app.delete("/api/playlists/{playlist_id}")
    def delete_playlist(playlist_id: int) -> dict:
        with db.connection() as connection:
            playlists.delete(connection, playlist_id)
        return {"status": "removed"}

    @app.post("/api/playlists/{playlist_id}/tracks")
    def add_playlist_track(playlist_id: int, payload: dict = Body(...)) -> dict:
        track_id = payload.get("track_id")
        if track_id is None:
            raise HTTPException(status_code=400, detail="track_id obrigatório")
        with db.connection() as connection:
            playlists.add_track(connection, playlist_id, track_id)
        return {"status": "added"}

    @app.delete("/api/playlists/{playlist_id}/tracks/{track_id}")
    def remove_playlist_track(playlist_id: int, track_id: int) -> dict:
        with db.connection() as connection:
            playlists.remove_track(connection, playlist_id, track_id)
        return {"status": "removed"}

    @app.put("/api/playlists/{playlist_id}/tracks")
    def reorder_playlist_tracks(playlist_id: int, payload: dict = Body(...)) -> dict:
        track_ids = payload.get("track_ids") or []
        with db.connection() as connection:
            try:
                playlists.reorder(connection, playlist_id, track_ids)
            except ValueError as error:
                raise HTTPException(status_code=400, detail=str(error))
        return {"status": "reordered"}

    @app.get("/api/player")
    def get_player() -> dict:
        with db.connection() as connection:
            row = connection.execute(
                "SELECT * FROM player_state WHERE id = 1"
            ).fetchone()
            if row is None:
                return {
                    "queue": [],
                    "current_index": -1,
                    "position": 0.0,
                    "volume": 1.0,
                }
            tracks = []
            for track_id in json.loads(row["queue"]):
                track_row = connection.execute(
                    "SELECT * FROM tracks WHERE id = ?", (track_id,)
                ).fetchone()
                if track_row is not None:
                    tracks.append(_track_dict(track_row))
        return {
            "queue": tracks,
            "current_index": row["current_index"],
            "position": row["position"],
            "volume": row["volume"],
        }

    @app.put("/api/player")
    def save_player(payload: dict = Body(...)) -> dict:
        queue = json.dumps(payload.get("queue") or [])
        current_index = int(payload.get("current_index", -1))
        position = float(payload.get("position", 0.0))
        volume = float(payload.get("volume", 1.0))
        with db.connection() as connection:
            connection.execute(
                """
                INSERT INTO player_state (id, queue, current_index, position, volume)
                VALUES (1, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    queue = excluded.queue,
                    current_index = excluded.current_index,
                    position = excluded.position,
                    volume = excluded.volume
                """,
                (queue, current_index, position, volume),
            )
            connection.commit()
        return {"status": "saved"}

    return app
