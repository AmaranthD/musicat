from pathlib import Path

from mutagen import File as MutagenFile

SUPPORTED_EXTENSIONS = {
    ".mp3",
    ".flac",
    ".m4a",
    ".mp4",
    ".aac",
    ".ogg",
    ".oga",
    ".opus",
    ".wav",
}


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def read_metadata(path: Path, fallback_title: str, fmt: str) -> dict:
    audio = MutagenFile(path, easy=True)
    if audio is None:
        raise ValueError("formato de áudio não reconhecido")

    def first(key: str) -> str | None:
        if not audio.tags:
            return None
        values = audio.tags.get(key)
        return values[0] if values else None

    return {
        "title": first("title") or fallback_title,
        "artist": first("artist"),
        "album": first("album"),
        "duration": getattr(audio.info, "length", None),
        "format": fmt,
    }


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
