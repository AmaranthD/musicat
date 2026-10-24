from datetime import datetime, timezone
import random

from . import access


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create(
    connection, name: str, owner_id: str, visibility: str = "private"
) -> object:
    now = _now()
    cursor = connection.execute(
        """
        INSERT INTO playlists (owner_id, name, visibility, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (owner_id, name, visibility, now, now),
    )
    connection.commit()
    return connection.execute(
        "SELECT * FROM playlists WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()


def list_for_user(connection, user):
    where, params = access.playlist_access_where("p", user)
    return connection.execute(
        f"""
        SELECT p.*, COUNT(pt.track_id) AS track_count
        FROM playlists p
        LEFT JOIN playlist_tracks pt ON pt.playlist_id = p.id
        WHERE {where}
        GROUP BY p.id
        ORDER BY p.created_at DESC
        """,
        params,
    ).fetchall()


def get(connection, playlist_id: int):
    playlist = connection.execute(
        "SELECT * FROM playlists WHERE id = ?", (playlist_id,)
    ).fetchone()
    if playlist is None:
        return None, None
    tracks = connection.execute(
        """
        SELECT t.* FROM playlist_tracks pt
        JOIN tracks t ON t.id = pt.track_id
        WHERE pt.playlist_id = ?
        ORDER BY pt.position
        """,
        (playlist_id,),
    ).fetchall()
    return playlist, tracks


def rename(connection, playlist_id: int, name: str):
    connection.execute(
        "UPDATE playlists SET name = ?, updated_at = ? WHERE id = ?",
        (name, _now(), playlist_id),
    )
    connection.commit()
    return connection.execute(
        "SELECT * FROM playlists WHERE id = ?", (playlist_id,)
    ).fetchone()


def set_visibility(connection, playlist_id: int, visibility: str):
    connection.execute(
        "UPDATE playlists SET visibility = ?, updated_at = ? WHERE id = ?",
        (visibility, _now(), playlist_id),
    )
    connection.commit()
    return connection.execute(
        "SELECT * FROM playlists WHERE id = ?", (playlist_id,)
    ).fetchone()


def delete(connection, playlist_id: int) -> None:
    connection.execute(
        "DELETE FROM playlist_tracks WHERE playlist_id = ?", (playlist_id,)
    )
    connection.execute(
        "DELETE FROM playlist_invites WHERE playlist_id = ?", (playlist_id,)
    )
    connection.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
    connection.commit()


def add_track(connection, playlist_id: int, track_id: int) -> None:
    row = connection.execute(
        """
        SELECT COALESCE(MAX(position), -1) + 1 AS next
        FROM playlist_tracks WHERE playlist_id = ?
        """,
        (playlist_id,),
    ).fetchone()
    connection.execute(
        """
        INSERT OR IGNORE INTO playlist_tracks (playlist_id, track_id, position)
        VALUES (?, ?, ?)
        """,
        (playlist_id, track_id, row["next"]),
    )
    connection.execute(
        "UPDATE playlists SET updated_at = ? WHERE id = ?", (_now(), playlist_id)
    )
    connection.commit()


def remove_track(connection, playlist_id: int, track_id: int) -> None:
    connection.execute(
        "DELETE FROM playlist_tracks WHERE playlist_id = ? AND track_id = ?",
        (playlist_id, track_id),
    )
    connection.execute(
        "UPDATE playlists SET updated_at = ? WHERE id = ?", (_now(), playlist_id)
    )
    connection.commit()


def reorder(connection, playlist_id: int, track_ids: list[int]) -> None:
    current = {
        row["track_id"]
        for row in connection.execute(
            "SELECT track_id FROM playlist_tracks WHERE playlist_id = ?",
            (playlist_id,),
        )
    }
    if set(track_ids) != current:
        raise ValueError("lista de faixas não corresponde à playlist")
    for position, track_id in enumerate(track_ids):
        connection.execute(
            """
            UPDATE playlist_tracks SET position = ?
            WHERE playlist_id = ? AND track_id = ?
            """,
            (position, playlist_id, track_id),
        )
    connection.execute(
        "UPDATE playlists SET updated_at = ? WHERE id = ?", (_now(), playlist_id)
    )
    connection.commit()


def random_track_ids(
    connection,
    user,
    artist: str | None = None,
    fmt: str | None = None,
    size: int | None = None,
) -> list[int]:
    where, params = access.track_access_where("t", user)
    query = f"SELECT t.id FROM tracks t WHERE {where}"
    if artist:
        query += " AND t.artist LIKE ?"
        params.append(f"%{artist}%")
    if fmt:
        query += " AND t.format = ?"
        params.append(fmt)

    ids = [row["id"] for row in connection.execute(query, params)]
    random.shuffle(ids)
    if size is not None:
        ids = ids[:size]
    return ids


def add_tracks(connection, playlist_id: int, track_ids: list[int]) -> None:
    for position, track_id in enumerate(track_ids):
        connection.execute(
            """
            INSERT OR IGNORE INTO playlist_tracks (playlist_id, track_id, position)
            VALUES (?, ?, ?)
            """,
            (playlist_id, track_id, position),
        )
    connection.execute(
        "UPDATE playlists SET updated_at = ? WHERE id = ?", (_now(), playlist_id)
    )
    connection.commit()


def add_invite(
    connection,
    playlist_id: int,
    user_id: str,
    email: str,
    invited_by: str,
) -> object:
    normalized = email.strip().lower()
    connection.execute(
        """
        INSERT INTO playlist_invites
            (playlist_id, user_id, email, invited_by, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(playlist_id, user_id) DO UPDATE SET
            email = excluded.email,
            invited_by = excluded.invited_by
        """,
        (playlist_id, user_id, normalized, invited_by, _now()),
    )
    connection.commit()
    return connection.execute(
        "SELECT * FROM playlist_invites WHERE playlist_id = ? AND user_id = ?",
        (playlist_id, user_id),
    ).fetchone()


def list_invites(connection, playlist_id: int):
    return connection.execute(
        "SELECT * FROM playlist_invites WHERE playlist_id = ? ORDER BY email",
        (playlist_id,),
    ).fetchall()


def remove_invite(connection, playlist_id: int, email: str) -> None:
    connection.execute(
        "DELETE FROM playlist_invites WHERE playlist_id = ? AND email = ?",
        (playlist_id, email.strip().lower()),
    )
    connection.commit()
