from fastapi import HTTPException

from ..auth import CurrentUser


def playlist_access_where(alias: str, user: CurrentUser) -> tuple[str, list]:
    return (
        f"({alias}.owner_id = ? OR {alias}.visibility = 'public' OR EXISTS ("
        f"SELECT 1 FROM playlist_invites i "
        f"WHERE i.playlist_id = {alias}.id AND i.user_id = ?))",
        [user.id, user.id],
    )


def track_access_where(alias: str, user: CurrentUser) -> tuple[str, list]:
    playlist_sql, playlist_params = playlist_access_where("p", user)
    return (
        f"({alias}.owner_id = ? OR {alias}.id IN ("
        f"SELECT pt.track_id FROM playlist_tracks pt "
        f"JOIN playlists p ON p.id = pt.playlist_id "
        f"WHERE {playlist_sql}))",
        [user.id, *playlist_params],
    )


def playlist_role(connection, playlist, user: CurrentUser) -> str | None:
    if playlist is None:
        return None
    if playlist["owner_id"] == user.id:
        return "owner"
    if playlist["visibility"] == "public":
        return "editor"
    invited = connection.execute(
        "SELECT 1 FROM playlist_invites WHERE playlist_id = ? AND user_id = ?",
        (playlist["id"], user.id),
    ).fetchone()
    if invited:
        return "editor"
    return None


def require_playlist(
    connection, playlist_id: int, user: CurrentUser
) -> tuple[object, str]:
    playlist = connection.execute(
        "SELECT * FROM playlists WHERE id = ?", (playlist_id,)
    ).fetchone()
    role = playlist_role(connection, playlist, user)
    if role is None:
        raise HTTPException(status_code=404, detail="playlist não encontrada")
    return playlist, role


def require_playlist_owner(playlist, user: CurrentUser) -> None:
    if playlist["owner_id"] != user.id:
        raise HTTPException(
            status_code=403, detail="só o dono pode alterar esta playlist"
        )


def visible_track(connection, track_id: int, user: CurrentUser):
    where, params = track_access_where("t", user)
    return connection.execute(
        f"SELECT t.* FROM tracks t WHERE t.id = ? AND {where}", [track_id, *params]
    ).fetchone()


def require_visible_track(connection, track_id: int, user: CurrentUser):
    row = visible_track(connection, track_id, user)
    if row is None:
        raise HTTPException(status_code=404, detail="faixa não encontrada")
    return row


def require_owned_track(connection, track_id: int, user: CurrentUser):
    row = connection.execute(
        "SELECT * FROM tracks WHERE id = ?", (track_id,)
    ).fetchone()
    if row is None or visible_track(connection, track_id, user) is None:
        raise HTTPException(status_code=404, detail="faixa não encontrada")
    if row["owner_id"] != user.id:
        raise HTTPException(
            status_code=403, detail="só o dono pode editar esta faixa"
        )
    return row


def owned_track(connection, track_id: int, user: CurrentUser):
    row = connection.execute(
        "SELECT * FROM tracks WHERE id = ? AND owner_id = ?", (track_id, user.id)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="faixa não encontrada")
    return row
