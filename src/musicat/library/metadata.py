import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from mutagen import File as MutagenFile

SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wav"}


@dataclass
class TrackMetadata:
    title: str
    artist: str | None
    album: str | None
    duration: float | None
    format: str


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def _from_mutagen(path: Path, fallback_title: str, fmt: str) -> TrackMetadata:
    audio = MutagenFile(path, easy=True)
    if audio is None:
        raise ValueError("formato de áudio não reconhecido")

    def first(key: str) -> str | None:
        if not audio.tags:
            return None
        values = audio.tags.get(key)
        return values[0] if values else None

    return TrackMetadata(
        title=first("title") or fallback_title,
        artist=first("artist"),
        album=first("album"),
        duration=getattr(audio.info, "length", None),
        format=fmt,
    )


def _from_ffprobe(path: Path, fallback_title: str, fmt: str) -> TrackMetadata | None:
    try:
        completed = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    data = json.loads(completed.stdout or "{}")
    container = data.get("format") or {}
    tags = {key.lower(): value for key, value in (container.get("tags") or {}).items()}
    duration = container.get("duration")
    return TrackMetadata(
        title=tags.get("title") or fallback_title,
        artist=tags.get("artist"),
        album=tags.get("album"),
        duration=float(duration) if duration else None,
        format=fmt,
    )


def read_metadata(path: Path, fallback_title: str, fmt: str) -> TrackMetadata:
    try:
        meta = _from_mutagen(path, fallback_title, fmt)
    except Exception:
        meta = _from_ffprobe(path, fallback_title, fmt)
        if meta is None:
            raise ValueError("formato de áudio não reconhecido")

    if meta.duration is None:
        probed = _from_ffprobe(path, fallback_title, fmt)
        if probed is not None and probed.duration is not None:
            meta.duration = probed.duration
    return meta


def extract_cover(path: Path) -> bytes | None:
    audio = MutagenFile(path)
    if audio is None:
        return None

    tags = audio.tags
    if tags is not None:
        getall = getattr(tags, "getall", None)
        if getall is not None:
            frames = getall("APIC")
            if frames:
                return frames[0].data
        if hasattr(tags, "get"):
            cover_frames = tags.get("covr")
            if cover_frames:
                return bytes(cover_frames[0])

    pictures = getattr(audio, "pictures", None)
    if pictures:
        return pictures[0].data
    return None


def guess_media_type(data: bytes) -> str:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"GIF8"):
        return "image/gif"
    return "application/octet-stream"
