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
