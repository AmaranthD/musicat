from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create(connection, name: str):
    cursor = connection.execute(
        "INSERT INTO playlists (name, created_at) VALUES (?, ?)", (name, _now())
    )
    connection.commit()
    return connection.execute(
        "SELECT * FROM playlists WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()


def list_all(connection):
    return connection.execute(
        """
        SELECT p.*, COUNT(pt.track_id) AS track_count
        FROM playlists p
        LEFT JOIN playlist_tracks pt ON pt.playlist_id = p.id
        GROUP BY p.id
        ORDER BY p.created_at DESC
        """
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
        "UPDATE playlists SET name = ? WHERE id = ?", (name, playlist_id)
    )
    connection.commit()
    return connection.execute(
        "SELECT * FROM playlists WHERE id = ?", (playlist_id,)
    ).fetchone()


def delete(connection, playlist_id: int) -> None:
    connection.execute(
        "DELETE FROM playlist_tracks WHERE playlist_id = ?", (playlist_id,)
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
    connection.commit()


def remove_track(connection, playlist_id: int, track_id: int) -> None:
    connection.execute(
        "DELETE FROM playlist_tracks WHERE playlist_id = ? AND track_id = ?",
        (playlist_id, track_id),
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
    connection.commit()
