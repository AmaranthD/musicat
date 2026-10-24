import sqlite3
from contextlib import closing, contextmanager

from .. import config

SCHEMA_VERSION = 2

TRACKS_TABLE = """
CREATE TABLE IF NOT EXISTS tracks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id     TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    filename     TEXT NOT NULL,
    stored_name  TEXT NOT NULL,
    title        TEXT,
    artist       TEXT,
    album        TEXT,
    duration     REAL,
    format       TEXT,
    imported_at  TEXT NOT NULL,
    UNIQUE (owner_id, content_hash)
);
"""

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id         TEXT PRIMARY KEY,
    email      TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS unrecognized (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id    TEXT NOT NULL,
    filename    TEXT NOT NULL,
    stored_name TEXT,
    reason      TEXT NOT NULL,
    imported_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS playlists (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id   TEXT NOT NULL,
    name       TEXT NOT NULL,
    visibility TEXT NOT NULL DEFAULT 'private'
               CHECK (visibility IN ('public', 'private')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS playlist_tracks (
    playlist_id INTEGER NOT NULL,
    track_id    INTEGER NOT NULL,
    position    INTEGER NOT NULL,
    PRIMARY KEY (playlist_id, track_id)
);

CREATE TABLE IF NOT EXISTS playlist_invites (
    playlist_id INTEGER NOT NULL,
    user_id     TEXT NOT NULL,
    email       TEXT NOT NULL,
    invited_by  TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    PRIMARY KEY (playlist_id, user_id),
    FOREIGN KEY (playlist_id) REFERENCES playlists (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS player_state (
    user_id       TEXT PRIMARY KEY,
    queue         TEXT NOT NULL,
    current_index INTEGER NOT NULL,
    position      REAL NOT NULL,
    volume        REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_tracks_owner ON tracks (owner_id);
CREATE INDEX IF NOT EXISTS idx_unrecognized_owner ON unrecognized (owner_id);
CREATE INDEX IF NOT EXISTS idx_playlists_owner ON playlists (owner_id);
CREATE INDEX IF NOT EXISTS idx_playlists_visibility ON playlists (visibility);
CREATE INDEX IF NOT EXISTS idx_playlist_tracks_track ON playlist_tracks (track_id);
CREATE INDEX IF NOT EXISTS idx_playlist_invites_user ON playlist_invites (user_id);
"""


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(config.db_path(), timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection


@contextmanager
def connection():
    handle = connect()
    try:
        yield handle
    finally:
        handle.close()


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
    ).fetchone()
    return row is not None


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {
        row["name"] for row in connection.execute(f"PRAGMA table_info({table})")
    }


def _rebuild_tracks(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = OFF")
    connection.executescript(
        """
        BEGIN;
        CREATE TABLE tracks_new (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id     TEXT,
            content_hash TEXT NOT NULL,
            filename     TEXT NOT NULL,
            stored_name  TEXT NOT NULL,
            title        TEXT,
            artist       TEXT,
            album        TEXT,
            duration     REAL,
            format       TEXT,
            imported_at  TEXT NOT NULL,
            UNIQUE (owner_id, content_hash)
        );
        INSERT INTO tracks_new
            (id, owner_id, content_hash, filename, stored_name, title, artist,
             album, duration, format, imported_at)
        SELECT id, NULL, content_hash, filename, stored_name, title, artist,
               album, duration, format, imported_at
        FROM tracks;
        DROP TABLE tracks;
        ALTER TABLE tracks_new RENAME TO tracks;
        COMMIT;
        """
    )
    connection.execute("PRAGMA foreign_keys = ON")


def _migrate(connection: sqlite3.Connection) -> None:
    if "owner_id" not in _columns(connection, "tracks"):
        _rebuild_tracks(connection)

    if "owner_id" not in _columns(connection, "unrecognized"):
        connection.execute("ALTER TABLE unrecognized ADD COLUMN owner_id TEXT")

    playlist_columns = _columns(connection, "playlists")
    if "owner_id" not in playlist_columns:
        connection.execute("ALTER TABLE playlists ADD COLUMN owner_id TEXT")
    if "visibility" not in playlist_columns:
        connection.execute(
            "ALTER TABLE playlists ADD COLUMN visibility TEXT NOT NULL DEFAULT 'private'"
        )
    if "updated_at" not in playlist_columns:
        connection.execute("ALTER TABLE playlists ADD COLUMN updated_at TEXT")
        connection.execute(
            "UPDATE playlists SET updated_at = created_at WHERE updated_at IS NULL"
        )

    if "user_id" not in _columns(connection, "player_state"):
        connection.execute("DROP TABLE IF EXISTS player_state")

    if _table_exists(connection, "playlist_invites") and "user_id" not in _columns(
        connection, "playlist_invites"
    ):
        connection.execute("DROP TABLE playlist_invites")


def init_db() -> None:
    with closing(connect()) as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        if not _table_exists(connection, "tracks"):
            connection.executescript(TRACKS_TABLE + SCHEMA)
        else:
            _migrate(connection)
            connection.executescript(SCHEMA)
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        connection.commit()
