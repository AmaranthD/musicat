import hashlib
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .. import config
from . import metadata


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def content_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _record_unrecognized(
    connection, filename: str, reason: str, data: bytes, suffix: str
) -> None:
    config.ensure_dirs()
    stored_name = f"{uuid4().hex}{suffix}"
    (config.unrecognized_dir() / stored_name).write_bytes(data)
    connection.execute(
        """
        INSERT INTO unrecognized (filename, stored_name, reason, imported_at)
        VALUES (?, ?, ?, ?)
        """,
        (filename, stored_name, reason, _now()),
    )
    connection.commit()


def import_file(filename: str, data: bytes, connection) -> dict:
    suffix = Path(filename).suffix.lower()
    if suffix not in metadata.SUPPORTED_EXTENSIONS:
        reason = f"formato não suportado: {suffix or 'sem extensão'}"
        _record_unrecognized(connection, filename, reason, data, suffix)
        return {"status": "unrecognized", "filename": filename, "reason": reason}

    config.ensure_dirs()
    incoming = config.library_dir() / f".incoming-{uuid4().hex}"
    incoming.write_bytes(data)

    digest = content_hash(incoming)
    existing = connection.execute(
        "SELECT id FROM tracks WHERE content_hash = ?", (digest,)
    ).fetchone()
    if existing:
        incoming.unlink(missing_ok=True)
        return {"status": "duplicate", "filename": filename, "track_id": existing["id"]}

    try:
        meta = metadata.read_metadata(incoming, Path(filename).stem, suffix.lstrip("."))
        cover = metadata.extract_cover(incoming)
    except Exception:
        incoming.unlink(missing_ok=True)
        reason = "não foi possível ler o áudio"
        _record_unrecognized(connection, filename, reason, data, suffix)
        return {"status": "unrecognized", "filename": filename, "reason": reason}

    stored_name = f"{digest}{suffix}"
    incoming.replace(config.library_dir() / stored_name)
    if cover:
        (config.library_dir() / f"{digest}.cover").write_bytes(cover)

    cursor = connection.execute(
        """
        INSERT INTO tracks
            (content_hash, filename, stored_name, title, artist, album, duration, format, imported_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            digest,
            filename,
            stored_name,
            meta["title"],
            meta["artist"],
            meta["album"],
            meta["duration"],
            meta["format"],
            _now(),
        ),
    )
    connection.commit()
    return {"status": "imported", "filename": filename, "track_id": cursor.lastrowid}
