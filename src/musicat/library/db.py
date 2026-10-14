import sqlite3
from contextlib import closing

from .. import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS tracks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    content_hash TEXT UNIQUE NOT NULL,
    filename     TEXT NOT NULL,
    stored_name  TEXT NOT NULL,
    title        TEXT,
    artist       TEXT,
    album        TEXT,
    duration     REAL,
    format       TEXT,
    imported_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS unrecognized (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    filename    TEXT NOT NULL,
    reason      TEXT NOT NULL,
    imported_at TEXT NOT NULL
);
"""


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(config.db_path())
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with closing(connect()) as connection:
        connection.executescript(SCHEMA)
        connection.commit()
