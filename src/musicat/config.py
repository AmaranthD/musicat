import os
from pathlib import Path


def _load_env(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


_load_env()

DEFAULT_SUPABASE_URL = "https://zcvnfxelcgcydopcdayc.supabase.co"
DEFAULT_SUPABASE_KEY = "sb_publishable_ZNUKILLmvAS91xx9lY-BDA_waMMuHVC"


def data_dir() -> Path:
    raw = os.environ.get("MUSICAT_DATA_DIR")
    return Path(raw) if raw else Path.cwd() / "data"


def library_dir() -> Path:
    return data_dir() / "library"


def unrecognized_dir() -> Path:
    return data_dir() / "unrecognized"


def db_path() -> Path:
    return data_dir() / "musicat.db"


def supabase_url() -> str:
    return os.environ.get("MUSICAT_SUPABASE_URL", DEFAULT_SUPABASE_URL).rstrip("/")


def supabase_key() -> str:
    return os.environ.get("MUSICAT_SUPABASE_KEY", DEFAULT_SUPABASE_KEY)


def claim_legacy_data() -> bool:
    raw = os.environ.get("MUSICAT_CLAIM_LEGACY", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def host() -> str:
    return os.environ.get("MUSICAT_HOST", "127.0.0.1")


def port() -> int:
    return int(os.environ.get("MUSICAT_PORT", "8000"))


def ensure_dirs() -> None:
    library_dir().mkdir(parents=True, exist_ok=True)
    unrecognized_dir().mkdir(parents=True, exist_ok=True)
