from pathlib import Path
import json
import mimetypes

from fastapi import Body, Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import auth, config
from .auth import CurrentUser, require_user
from .library import access, db, importer, playlists
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
VISIBILITIES = {"public", "private"}


def _cover_path(content_hash: str, owner_id: str) -> Path:
    return config.library_dir() / f"{content_hash}.{owner_id}.cover"


def _track_dict(row, user: CurrentUser) -> dict:
    data = Track.from_row(row).to_dict()
    owner_id = data.pop("owner_id")
    data["owned"] = owner_id == user.id
    data["shared"] = not data["owned"]
    data["has_cover"] = _cover_path(data["content_hash"], owner_id).exists()
    return data


def _playlist_dict(playlist, tracks, user: CurrentUser, role: str) -> dict:
    data = dict(playlist)
    data.pop("owner_id", None)
    data["role"] = role
    data["is_owner"] = role == "owner"
    data["tracks"] = [_track_dict(row, user) for row in tracks]
    return data


def _owned_unrecognized(connection, item_id: int, user: CurrentUser):
    row = connection.execute(
        "SELECT * FROM unrecognized WHERE id = ? AND owner_id = ?",
        (item_id, user.id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="item não encontrado")
    return row


def create_app() -> FastAPI:
    config.ensure_dirs()
    db.init_db()

    app = FastAPI(title="Musicat")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/auth/config")
    def auth_config() -> dict:
        return {
            "supabase_url": config.supabase_url(),
            "supabase_key": config.supabase_key(),
        }

    @app.post("/api/auth/session")
    def create_session(
        request: Request,
        response: Response,
        user: CurrentUser = Depends(require_user),
    ) -> dict:
        token = auth.request_token(request)
        if token:
            auth.set_session_cookie(response, request, token)
        return {"id": user.id, "email": user.email}

    @app.delete("/api/auth/session")
    def destroy_session(response: Response) -> dict:
        auth.clear_session_cookie(response)
        return {"status": "signed-out"}

    @app.get("/api/me")
    def me(user: CurrentUser = Depends(require_user)) -> dict:
        return {"id": user.id, "email": user.email}

    @app.post("/api/import")
    async def import_tracks(
        files: list[UploadFile] = File(...),
        user: CurrentUser = Depends(require_user),
    ) -> dict:
        imported: list[dict] = []
        duplicates: list[dict] = []
        unrecognized: list[dict] = []
        with db.connection() as connection:
            for upload in files:
                data = await upload.read()
                result = importer.import_file(
                    upload.filename or "sem-nome", data, connection, user.id
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
    def library(
        search: str = "",
        sort: str = "imported_at",
        user: CurrentUser = Depends(require_user),
    ) -> dict:
        column = SORT_COLUMNS.get(sort, "imported_at")
        direction = "DESC" if column == "imported_at" else "ASC"
        where, params = access.track_access_where("t", user)
        with db.connection() as connection:
            query = f"SELECT t.* FROM tracks t WHERE {where}"
            if search:
                query += (
                    " AND (t.title LIKE ? OR t.artist LIKE ? OR t.album LIKE ?)"
                )
                term = f"%{search}%"
                params.extend([term, term, term])
            query += f" ORDER BY t.{column} {direction}"
            tracks = [_track_dict(row, user) for row in connection.execute(query, params)]
            unrecognized = [
                UnrecognizedItem.from_row(row).to_dict()
                for row in connection.execute(
                    "SELECT * FROM unrecognized WHERE owner_id = ? "
                    "ORDER BY imported_at DESC",
                    (user.id,),
                )
            ]
        return {"tracks": tracks, "unrecognized": unrecognized}

    @app.patch("/api/tracks/{track_id}")
    def update_track(
        track_id: int,
        payload: dict = Body(...),
        user: CurrentUser = Depends(require_user),
    ) -> dict:
        fields = {key: value for key, value in payload.items() if key in EDITABLE_FIELDS}
        if not fields:
            raise HTTPException(status_code=400, detail="nenhum campo editável enviado")
        with db.connection() as connection:
            access.require_owned_track(connection, track_id, user)
            assignments = ", ".join(f"{key} = ?" for key in fields)
            connection.execute(
                f"UPDATE tracks SET {assignments} WHERE id = ?",
                [*fields.values(), track_id],
            )
            connection.commit()
            updated = connection.execute(
                "SELECT * FROM tracks WHERE id = ?", (track_id,)
            ).fetchone()
        return _track_dict(updated, user)

    @app.get("/api/tracks/{track_id}/stream")
    def stream_track(
        track_id: int, user: CurrentUser = Depends(require_user)
    ) -> FileResponse:
        with db.connection() as connection:
            row = access.require_visible_track(connection, track_id, user)
        audio_path = config.library_dir() / row["stored_name"]
        if not audio_path.exists():
            raise HTTPException(status_code=404, detail="arquivo indisponível")
        media_type = mimetypes.guess_type(audio_path.name)[0] or "audio/mpeg"
        return FileResponse(audio_path, media_type=media_type)

    @app.get("/api/tracks/{track_id}/cover")
    def track_cover(
        track_id: int, user: CurrentUser = Depends(require_user)
    ) -> FileResponse:
        with db.connection() as connection:
            row = access.require_visible_track(connection, track_id, user)
        cover_path = _cover_path(row["content_hash"], row["owner_id"])
        if not cover_path.exists():
            raise HTTPException(status_code=404, detail="sem capa")
        media_type = metadata_reader.guess_media_type(cover_path.read_bytes())
        return FileResponse(cover_path, media_type=media_type)

    @app.put("/api/tracks/{track_id}/cover")
    async def upload_cover(
        track_id: int,
        cover: UploadFile = File(...),
        user: CurrentUser = Depends(require_user),
    ) -> dict:
        data = await cover.read()
        if metadata_reader.guess_media_type(data) == "application/octet-stream":
            raise HTTPException(status_code=400, detail="imagem inválida")
        with db.connection() as connection:
            row = access.require_owned_track(connection, track_id, user)
        _cover_path(row["content_hash"], user.id).write_bytes(data)
        return {"status": "saved"}

    @app.delete("/api/unrecognized/{item_id}")
    def remove_unrecognized(
        item_id: int, user: CurrentUser = Depends(require_user)
    ) -> dict:
        with db.connection() as connection:
            row = _owned_unrecognized(connection, item_id, user)
            if row["stored_name"]:
                (config.unrecognized_dir() / row["stored_name"]).unlink(missing_ok=True)
            connection.execute("DELETE FROM unrecognized WHERE id = ?", (item_id,))
            connection.commit()
        return {"status": "removed"}

    @app.post("/api/unrecognized/{item_id}/reprocess")
    def reprocess_unrecognized(
        item_id: int, user: CurrentUser = Depends(require_user)
    ) -> dict:
        with db.connection() as connection:
            row = _owned_unrecognized(connection, item_id, user)
            if not row["stored_name"]:
                raise HTTPException(status_code=400, detail="arquivo indisponível")
            stored = config.unrecognized_dir() / row["stored_name"]
            if not stored.exists():
                raise HTTPException(status_code=400, detail="arquivo indisponível")
            result = importer.import_file(
                row["filename"], stored.read_bytes(), connection, user.id
            )
            if result["status"] != "unrecognized":
                stored.unlink(missing_ok=True)
                connection.execute(
                    "DELETE FROM unrecognized WHERE id = ?", (item_id,)
                )
                connection.commit()
        return result

    @app.post("/api/playlists")
    def create_playlist(
        payload: dict = Body(...), user: CurrentUser = Depends(require_user)
    ) -> dict:
        name = (payload.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="nome obrigatório")
        visibility = payload.get("visibility") or "private"
        if visibility not in VISIBILITIES:
            raise HTTPException(status_code=400, detail="visibilidade inválida")
        with db.connection() as connection:
            row = playlists.create(connection, name, user.id, visibility)
        return _playlist_dict(row, [], user, "owner")

    @app.post("/api/playlists/random")
    def random_playlist(
        payload: dict = Body(default={}),
        user: CurrentUser = Depends(require_user),
    ) -> dict:
        name = (payload.get("name") or "").strip() or "Aleatória"
        visibility = payload.get("visibility") or "private"
        if visibility not in VISIBILITIES:
            raise HTTPException(status_code=400, detail="visibilidade inválida")
        raw_size = payload.get("size")
        try:
            size = int(raw_size) if raw_size else None
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="tamanho inválido")
        if size is not None and size < 0:
            raise HTTPException(status_code=400, detail="tamanho inválido")
        artist = payload.get("artist") or None
        fmt = payload.get("format") or None
        with db.connection() as connection:
            ids = playlists.random_track_ids(
                connection, user, artist=artist, fmt=fmt, size=size
            )
            created = playlists.create(connection, name, user.id, visibility)
            playlists.add_tracks(connection, created["id"], ids)
            playlist, tracks = playlists.get(connection, created["id"])
        return _playlist_dict(playlist, tracks, user, "owner")

    @app.get("/api/playlists")
    def list_playlists(user: CurrentUser = Depends(require_user)) -> dict:
        with db.connection() as connection:
            rows = playlists.list_for_user(connection, user)
            result = []
            for row in rows:
                role = access.playlist_role(connection, row, user)
                data = dict(row)
                data.pop("owner_id", None)
                data["role"] = role
                data["is_owner"] = role == "owner"
                result.append(data)
        return {"playlists": result}

    @app.get("/api/playlists/{playlist_id}")
    def get_playlist(
        playlist_id: int, user: CurrentUser = Depends(require_user)
    ) -> dict:
        with db.connection() as connection:
            _, role = access.require_playlist(connection, playlist_id, user)
            playlist, tracks = playlists.get(connection, playlist_id)
        return _playlist_dict(playlist, tracks, user, role)

    @app.patch("/api/playlists/{playlist_id}")
    def update_playlist(
        playlist_id: int,
        payload: dict = Body(...),
        user: CurrentUser = Depends(require_user),
    ) -> dict:
        with db.connection() as connection:
            playlist, role = access.require_playlist(connection, playlist_id, user)
            access.require_playlist_owner(playlist, user)
            if "visibility" in payload:
                if payload["visibility"] not in VISIBILITIES:
                    raise HTTPException(status_code=400, detail="visibilidade inválida")
                playlist = playlists.set_visibility(
                    connection, playlist_id, payload["visibility"]
                )
            if "name" in payload:
                name = (payload.get("name") or "").strip()
                if not name:
                    raise HTTPException(status_code=400, detail="nome obrigatório")
                playlist = playlists.rename(connection, playlist_id, name)
            _, tracks = playlists.get(connection, playlist_id)
        return _playlist_dict(playlist, tracks, user, role)

    @app.delete("/api/playlists/{playlist_id}")
    def delete_playlist(
        playlist_id: int, user: CurrentUser = Depends(require_user)
    ) -> dict:
        with db.connection() as connection:
            playlist, _ = access.require_playlist(connection, playlist_id, user)
            access.require_playlist_owner(playlist, user)
            playlists.delete(connection, playlist_id)
        return {"status": "removed"}

    @app.post("/api/playlists/{playlist_id}/tracks")
    def add_playlist_track(
        playlist_id: int,
        payload: dict = Body(...),
        user: CurrentUser = Depends(require_user),
    ) -> dict:
        track_id = payload.get("track_id")
        if track_id is None:
            raise HTTPException(status_code=400, detail="track_id obrigatório")
        with db.connection() as connection:
            access.require_playlist(connection, playlist_id, user)
            access.require_visible_track(connection, track_id, user)
            playlists.add_track(connection, playlist_id, track_id)
        return {"status": "added"}

    @app.delete("/api/playlists/{playlist_id}/tracks/{track_id}")
    def remove_playlist_track(
        playlist_id: int,
        track_id: int,
        user: CurrentUser = Depends(require_user),
    ) -> dict:
        with db.connection() as connection:
            access.require_playlist(connection, playlist_id, user)
            playlists.remove_track(connection, playlist_id, track_id)
        return {"status": "removed"}

    @app.put("/api/playlists/{playlist_id}/tracks")
    def reorder_playlist_tracks(
        playlist_id: int,
        payload: dict = Body(...),
        user: CurrentUser = Depends(require_user),
    ) -> dict:
        track_ids = payload.get("track_ids") or []
        with db.connection() as connection:
            access.require_playlist(connection, playlist_id, user)
            try:
                playlists.reorder(connection, playlist_id, track_ids)
            except ValueError as error:
                raise HTTPException(status_code=400, detail=str(error))
        return {"status": "reordered"}

    @app.get("/api/playlists/{playlist_id}/invites")
    def list_playlist_invites(
        playlist_id: int, user: CurrentUser = Depends(require_user)
    ) -> dict:
        with db.connection() as connection:
            playlist, _ = access.require_playlist(connection, playlist_id, user)
            access.require_playlist_owner(playlist, user)
            rows = playlists.list_invites(connection, playlist_id)
        return {
            "invites": [
                {"email": row["email"], "created_at": row["created_at"]} for row in rows
            ]
        }

    @app.post("/api/playlists/{playlist_id}/invites")
    def add_playlist_invite(
        playlist_id: int,
        payload: dict = Body(...),
        user: CurrentUser = Depends(require_user),
    ) -> dict:
        email = (payload.get("email") or "").strip().lower()
        if "@" not in email:
            raise HTTPException(status_code=400, detail="e-mail inválido")
        with db.connection() as connection:
            playlist, _ = access.require_playlist(connection, playlist_id, user)
            access.require_playlist_owner(playlist, user)
            known = connection.execute(
                "SELECT id, email FROM users WHERE lower(email) = ?", (email,)
            ).fetchone()
            if known is None:
                raise HTTPException(status_code=404, detail="usuário não encontrado")
            if known["id"] == user.id:
                raise HTTPException(status_code=400, detail="você já é o dono")
            row = playlists.add_invite(
                connection,
                playlist_id,
                known["id"],
                known["email"] or email,
                user.id,
            )
        return {"email": row["email"], "created_at": row["created_at"]}

    @app.delete("/api/playlists/{playlist_id}/invites/{email}")
    def remove_playlist_invite(
        playlist_id: int,
        email: str,
        user: CurrentUser = Depends(require_user),
    ) -> dict:
        with db.connection() as connection:
            playlist, _ = access.require_playlist(connection, playlist_id, user)
            access.require_playlist_owner(playlist, user)
            playlists.remove_invite(connection, playlist_id, email)
        return {"status": "removed"}

    @app.get("/api/player")
    def get_player(user: CurrentUser = Depends(require_user)) -> dict:
        with db.connection() as connection:
            row = connection.execute(
                "SELECT * FROM player_state WHERE user_id = ?", (user.id,)
            ).fetchone()
            if row is None:
                return {
                    "queue": [],
                    "current_index": -1,
                    "position": 0.0,
                    "volume": 1.0,
                }
            try:
                saved_queue = json.loads(row["queue"])
            except (TypeError, ValueError):
                saved_queue = []
            tracks = []
            current_index = -1
            for position, track_id in enumerate(saved_queue):
                track_row = access.visible_track(connection, track_id, user)
                if track_row is None:
                    continue
                if position == row["current_index"]:
                    current_index = len(tracks)
                tracks.append(_track_dict(track_row, user))
        return {
            "queue": tracks,
            "current_index": current_index,
            "position": row["position"],
            "volume": row["volume"],
        }

    @app.put("/api/player")
    def save_player(
        payload: dict = Body(...), user: CurrentUser = Depends(require_user)
    ) -> dict:
        try:
            requested = [int(track_id) for track_id in payload.get("queue") or []]
            current_index = int(payload.get("current_index", -1))
            position = float(payload.get("position", 0.0))
            volume = float(payload.get("volume", 1.0))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="estado do player inválido")
        with db.connection() as connection:
            queue = []
            remapped_index = -1
            for index, track_id in enumerate(requested):
                if access.visible_track(connection, track_id, user) is None:
                    continue
                if index == current_index:
                    remapped_index = len(queue)
                queue.append(track_id)
            current_index = remapped_index if current_index >= 0 else -1
            position_value = max(0.0, position)
            volume = max(0.0, min(1.0, volume))
            encoded = json.dumps(queue)
            connection.execute(
                """
                INSERT INTO player_state
                    (user_id, queue, current_index, position, volume)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    queue = excluded.queue,
                    current_index = excluded.current_index,
                    position = excluded.position,
                    volume = excluded.volume
                """,
                (user.id, encoded, current_index, position_value, volume),
            )
            connection.commit()
        return {"status": "saved"}

    return app
