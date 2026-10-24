import json
import shutil
import threading
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone

import jwt
from fastapi import HTTPException, Request, Response

from . import config
from .library import db

COOKIE_NAME = "musicat_session"
ALLOWED_ALGORITHMS = {"ES256", "RS256", "EdDSA"}
JWKS_TTL_SECONDS = 300


class AuthError(Exception):
    pass


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str


_jwks_lock = threading.Lock()
_jwks_cache: dict = {"url": None, "fetched_at": 0.0, "keys": {}}


def _fetch_jwks(url: str) -> dict:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _load_keys(force: bool = False) -> dict:
    url = f"{config.supabase_url()}/auth/v1/.well-known/jwks.json"
    now = time.monotonic()
    with _jwks_lock:
        stale = (
            _jwks_cache["url"] != url
            or force
            or now - _jwks_cache["fetched_at"] > JWKS_TTL_SECONDS
        )
        if stale:
            payload = _fetch_jwks(url)
            keys = {}
            for entry in payload.get("keys", []):
                kid = entry.get("kid")
                if kid:
                    keys[kid] = jwt.PyJWK(entry).key
            _jwks_cache.update({"url": url, "fetched_at": now, "keys": keys})
        return dict(_jwks_cache["keys"])


def verify_token(token: str) -> dict:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as error:
        raise AuthError("token inválido") from error

    algorithm = header.get("alg")
    if algorithm not in ALLOWED_ALGORITHMS:
        raise AuthError("algoritmo de assinatura não suportado")

    kid = header.get("kid")
    try:
        keys = _load_keys()
        key = keys.get(kid)
        if key is None:
            key = _load_keys(force=True).get(kid)
        if key is None:
            raise AuthError("chave de assinatura desconhecida")

        payload = jwt.decode(
            token,
            key=key,
            algorithms=[algorithm],
            audience="authenticated",
            issuer=f"{config.supabase_url()}/auth/v1",
            options={"require": ["exp", "sub", "aud", "iss"]},
        )
    except AuthError:
        raise
    except jwt.PyJWTError as error:
        raise AuthError("sessão inválida ou expirada") from error
    except (OSError, ValueError) as error:
        raise AuthError("não foi possível validar a sessão") from error

    if not payload.get("sub"):
        raise AuthError("sessão sem usuário")
    return payload


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def request_token(request: Request) -> str | None:
    token = _bearer_token(request)
    if token:
        return token
    if request.method in {"GET", "HEAD"}:
        return request.cookies.get(COOKIE_NAME)
    return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def register_user(connection, user: CurrentUser) -> None:
    existing = connection.execute(
        "SELECT email FROM users WHERE id = ?", (user.id,)
    ).fetchone()
    if existing is not None and (existing["email"] or "") == (user.email or ""):
        return
    connection.execute(
        """
        INSERT INTO users (id, email, created_at) VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET email = excluded.email
        """,
        (user.id, user.email or None, _now()),
    )
    if existing is None and config.claim_legacy_data():
        total = connection.execute("SELECT COUNT(*) AS total FROM users").fetchone()[
            "total"
        ]
        if total == 1:
            unowned = connection.execute(
                "SELECT content_hash FROM tracks WHERE owner_id IS NULL"
            ).fetchall()
            legacy_covers = []
            for row in unowned:
                legacy_cover = (
                    config.library_dir() / f"{row['content_hash']}.cover"
                )
                if legacy_cover.exists():
                    destination = (
                        config.library_dir()
                        / f"{row['content_hash']}.{user.id}.cover"
                    )
                    if not destination.exists():
                        shutil.copy2(legacy_cover, destination)
                    legacy_covers.append(legacy_cover)
            connection.execute(
                "UPDATE tracks SET owner_id = ? WHERE owner_id IS NULL", (user.id,)
            )
            connection.execute(
                "UPDATE playlists SET owner_id = ? WHERE owner_id IS NULL", (user.id,)
            )
            connection.execute(
                "UPDATE unrecognized SET owner_id = ? WHERE owner_id IS NULL",
                (user.id,),
            )
            connection.commit()
            for legacy_cover in legacy_covers:
                legacy_cover.unlink(missing_ok=True)
            return
    connection.commit()


def require_user(request: Request) -> CurrentUser:
    token = request_token(request)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="sessão necessária",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = verify_token(token)
    except AuthError as error:
        raise HTTPException(
            status_code=401,
            detail=str(error),
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = CurrentUser(
        id=payload["sub"],
        email=(payload.get("email") or "").strip().lower(),
    )
    with db.connection() as connection:
        register_user(connection, user)
    return user


def _is_secure_request(request: Request) -> bool:
    forwarded = (
        request.headers.get("x-forwarded-proto", "").split(",")[0].strip().lower()
    )
    return request.url.scheme == "https" or forwarded == "https"


def set_session_cookie(response: Response, request: Request, token: str) -> None:
    try:
        payload = verify_token(token)
        max_age = max(60, min(3600, int(payload["exp"] - time.time())))
    except (AuthError, KeyError, TypeError):
        max_age = 3600
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=_is_secure_request(request),
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")
