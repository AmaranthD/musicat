import os
from pathlib import Path


def data_dir() -> Path:
    raw = os.environ.get("MUSICAT_DATA_DIR")
    return Path(raw) if raw else Path.cwd() / "data"


def library_dir() -> Path:
    return data_dir() / "library"


def db_path() -> Path:
    return data_dir() / "musicat.db"


def ensure_dirs() -> None:
    library_dir().mkdir(parents=True, exist_ok=True)
