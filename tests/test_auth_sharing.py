import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from musicat import auth, config


def _upload(client, paths, headers=None):
    files = [
        ("files", (path.name, path.read_bytes(), "audio/mpeg")) for path in paths
    ]
    return client.post("/api/import", files=files, headers=headers or {})


def _track_id(client, headers=None):
    return client.get("/api/library", headers=headers or {}).json()["tracks"][0]["id"]


@pytest.fixture
def signed_client(anonymous_client, monkeypatch):
    key = ec.generate_private_key(ec.SECP256R1())
    jwk = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(key.public_key()))
    jwk.update({"kid": "test-kid", "use": "sig", "alg": "ES256"})
    monkeypatch.setattr(auth, "_fetch_jwks", lambda url: {"keys": [jwk]})
    auth._jwks_cache.update({"url": None, "fetched_at": 0.0, "keys": {}})

    def token_for(user_id: str, email: str) -> str:
        now = int(time.time())
        return jwt.encode(
            {
                "sub": user_id,
                "email": email,
                "aud": "authenticated",
                "iss": f"{config.supabase_url()}/auth/v1",
                "iat": now,
                "exp": now + 3600,
            },
            key,
            algorithm="ES256",
            headers={"kid": "test-kid"},
        )

    return anonymous_client, token_for


def test_api_requires_session(anonymous_client):
    assert anonymous_client.get("/api/library").status_code == 401
    assert anonymous_client.get("/api/playlists").status_code == 401
    assert anonymous_client.get("/api/me").status_code == 401
    assert anonymous_client.post("/api/playlists", json={"name": "x"}).status_code == 401


def test_verifies_supabase_jwt_and_returns_me(signed_client):
    client, token_for = signed_client
    token = token_for("real-user", "real@example.com")

    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {"id": "real-user", "email": "real@example.com"}


def test_rejects_invalid_token(anonymous_client):
    response = anonymous_client.get(
        "/api/me", headers={"Authorization": "Bearer not-a-token"}
    )

    assert response.status_code == 401


def test_tracks_are_private_to_owner(client, as_user, make_mp3):
    as_user("user-a", "a@example.com")
    _upload(client, [make_mp3("a.mp3", freq=440)])
    a_track = _track_id(client)

    as_user("user-b", "b@example.com")
    assert client.get("/api/library").json()["tracks"] == []
    assert client.patch(f"/api/tracks/{a_track}", json={"title": "x"}).status_code == 404
    assert client.get(f"/api/tracks/{a_track}/stream").status_code == 404


def test_same_audio_can_be_imported_by_two_users(client, as_user, make_mp3):
    audio = make_mp3("song.mp3", freq=440)
    as_user("user-a", "a@example.com")
    assert len(_upload(client, [audio]).json()["imported"]) == 1

    as_user("user-b", "b@example.com")
    result = _upload(client, [audio]).json()

    assert len(result["imported"]) == 1
    assert len(client.get("/api/library").json()["tracks"]) == 1


def test_public_playlist_is_visible_and_editable_by_anyone(
    client, as_user, make_mp3
):
    as_user("user-a", "a@example.com")
    _upload(client, [make_mp3("a.mp3", freq=440)])
    a_track = _track_id(client)
    playlist = client.post(
        "/api/playlists", json={"name": "Pública", "visibility": "public"}
    ).json()
    client.post(f"/api/playlists/{playlist['id']}/tracks", json={"track_id": a_track})

    as_user("user-b", "b@example.com")
    listed = client.get("/api/playlists").json()["playlists"]
    assert listed[0]["id"] == playlist["id"]
    assert listed[0]["role"] == "editor"

    detail = client.get(f"/api/playlists/{playlist['id']}").json()
    assert [t["id"] for t in detail["tracks"]] == [a_track]

    _upload(client, [make_mp3("b.mp3", freq=550)])
    b_track = _track_id(client)
    assert (
        client.post(
            f"/api/playlists/{playlist['id']}/tracks", json={"track_id": b_track}
        ).status_code
        == 200
    )
    assert (
        client.delete(f"/api/playlists/{playlist['id']}/tracks/{a_track}").status_code
        == 200
    )

    assert (
        client.patch(
            f"/api/playlists/{playlist['id']}", json={"name": "Invadida"}
        ).status_code
        == 403
    )
    assert client.delete(f"/api/playlists/{playlist['id']}").status_code == 403


def test_private_playlist_requires_invite(client, as_user, make_mp3):
    as_user("user-a", "a@example.com")
    _upload(client, [make_mp3("a.mp3", freq=440)])
    a_track = _track_id(client)
    playlist = client.post("/api/playlists", json={"name": "Privada"}).json()
    client.post(f"/api/playlists/{playlist['id']}/tracks", json={"track_id": a_track})

    as_user("user-b", "b@example.com")
    assert client.get("/api/playlists").json()["playlists"] == []
    assert client.get(f"/api/playlists/{playlist['id']}").status_code == 404
    assert (
        client.post(
            f"/api/playlists/{playlist['id']}/tracks", json={"track_id": a_track}
        ).status_code
        == 404
    )

    as_user("user-a", "a@example.com")
    invited = client.post(
        f"/api/playlists/{playlist['id']}/invites", json={"email": "B@example.com"}
    )
    assert invited.status_code == 200
    assert invited.json()["email"] == "b@example.com"

    as_user("user-b", "b@example.com")
    detail = client.get(f"/api/playlists/{playlist['id']}").json()
    assert detail["role"] == "editor"
    assert detail["is_owner"] is False
    assert (
        client.post(
            f"/api/playlists/{playlist['id']}/tracks", json={"track_id": a_track}
        ).status_code
        == 200
    )

    as_user("user-a", "a@example.com")
    client.delete(f"/api/playlists/{playlist['id']}/invites/b@example.com")

    as_user("user-b", "b@example.com")
    assert client.get(f"/api/playlists/{playlist['id']}").status_code == 404


def test_invite_requires_existing_user_and_owner(client, as_user):
    as_user("user-a", "a@example.com")
    playlist = client.post("/api/playlists", json={"name": "Privada"}).json()

    unknown = client.post(
        f"/api/playlists/{playlist['id']}/invites", json={"email": "ghost@example.com"}
    )
    assert unknown.status_code == 404

    as_user("user-b", "b@example.com")
    forbidden = client.post(
        f"/api/playlists/{playlist['id']}/invites", json={"email": "a@example.com"}
    )
    assert forbidden.status_code == 404


def test_only_owner_can_change_visibility(client, as_user):
    as_user("user-a", "a@example.com")
    playlist = client.post(
        "/api/playlists", json={"name": "Pública", "visibility": "public"}
    ).json()

    as_user("user-b", "b@example.com")
    assert (
        client.patch(
            f"/api/playlists/{playlist['id']}", json={"visibility": "private"}
        ).status_code
        == 403
    )

    as_user("user-a", "a@example.com")
    updated = client.patch(
        f"/api/playlists/{playlist['id']}", json={"visibility": "private"}
    ).json()
    assert updated["visibility"] == "private"


def test_player_state_is_per_user(client, as_user, make_mp3):
    as_user("user-a", "a@example.com")
    _upload(client, [make_mp3("a.mp3", freq=440)])
    track_id = _track_id(client)
    client.put(
        "/api/player",
        json={"queue": [track_id], "current_index": 0, "position": 3.0, "volume": 0.5},
    )

    as_user("user-b", "b@example.com")
    state = client.get("/api/player").json()
    assert state["queue"] == []
    assert state["volume"] == 1.0


def test_media_cookie_allows_get_but_not_writes(signed_client, make_mp3):
    client, token_for = signed_client
    token = token_for("media-user", "media@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    _upload(client, [make_mp3("song.mp3", freq=440)], headers=headers)
    track_id = _track_id(client, headers=headers)

    session = client.post("/api/auth/session", headers=headers)
    assert session.status_code == 200

    assert client.get(f"/api/tracks/{track_id}/stream").status_code == 200
    assert client.get("/api/library").status_code == 200
    assert _upload(client, [make_mp3("other.mp3", freq=550)]).status_code == 401


def test_cover_is_private_per_owner(client, as_user, make_mp3):
    audio = make_mp3("song.mp3", freq=440)
    as_user("user-a", "a@example.com")
    _upload(client, [audio])
    a_track = _track_id(client)
    png_a = b"\x89PNG\r\n\x1a\n" + b"A" * 16
    client.put(
        f"/api/tracks/{a_track}/cover",
        files={"cover": ("a.png", png_a, "image/png")},
    )
    assert client.get(f"/api/tracks/{a_track}/cover").content == png_a

    as_user("user-b", "b@example.com")
    _upload(client, [audio])
    b_track = _track_id(client)
    assert client.get("/api/library").json()["tracks"][0]["has_cover"] is False

    png_b = b"\x89PNG\r\n\x1a\n" + b"B" * 16
    client.put(
        f"/api/tracks/{b_track}/cover",
        files={"cover": ("b.png", png_b, "image/png")},
    )
    assert client.get(f"/api/tracks/{b_track}/cover").content == png_b

    as_user("user-a", "a@example.com")
    assert client.get(f"/api/tracks/{a_track}/cover").content == png_a


def test_session_cookie_is_secure_behind_https_proxy(signed_client):
    client, token_for = signed_client
    token = token_for("proxy-user", "proxy@example.com")

    response = client.post(
        "/api/auth/session",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Forwarded-Proto": "https",
        },
    )

    assert response.status_code == 200
    assert "secure" in response.headers["set-cookie"].lower()


def test_healthz_is_public(anonymous_client):
    response = anonymous_client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
