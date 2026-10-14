from musicat.library import metadata


def test_falls_back_to_ffprobe_when_mutagen_fails(monkeypatch, make_mp3):
    track = make_mp3("song.mp3", title="Via Probe", artist="Probe", freq=440)
    monkeypatch.setattr(metadata, "MutagenFile", lambda *args, **kwargs: None)

    meta = metadata.read_metadata(track, "fallback", "mp3")

    assert meta.title == "Via Probe"
    assert meta.duration is not None


def test_duplicate_reports_message(client, make_mp3, upload, tmp_path):
    first = make_mp3("a.mp3", freq=440)
    second = tmp_path / "b.mp3"
    second.write_bytes(first.read_bytes())

    upload([first])
    response = upload([second]).json()

    assert response["duplicates"][0]["message"] == "já está na Biblioteca"


def test_upload_cover_override(client, make_mp3, upload, tmp_path):
    upload([make_mp3("song.mp3", freq=440)])
    track = client.get("/api/library").json()["tracks"][0]
    assert track["has_cover"] is False

    png = b"\x89PNG\r\n\x1a\n" + b"0" * 16
    response = client.put(
        f"/api/tracks/{track['id']}/cover",
        files={"cover": ("cover.png", png, "image/png")},
    )

    assert response.status_code == 200
    assert client.get("/api/library").json()["tracks"][0]["has_cover"] is True
    assert client.get(f"/api/tracks/{track['id']}/cover").status_code == 200


def test_upload_invalid_cover_rejected(client, make_mp3, upload):
    upload([make_mp3("song.mp3", freq=440)])
    track = client.get("/api/library").json()["tracks"][0]

    response = client.put(
        f"/api/tracks/{track['id']}/cover",
        files={"cover": ("x.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 400


def test_queue_from_playlist_round_trip(client, make_mp3, upload):
    upload([make_mp3("a.mp3", freq=440)])
    upload([make_mp3("b.mp3", freq=550)])
    tracks = client.get("/api/library").json()["tracks"]
    playlist = client.post("/api/playlists", json={"name": "Fila"}).json()
    for track in tracks:
        client.post(
            f"/api/playlists/{playlist['id']}/tracks", json={"track_id": track["id"]}
        )

    detail = client.get(f"/api/playlists/{playlist['id']}").json()
    ids = [t["id"] for t in detail["tracks"]]
    client.put(
        "/api/player",
        json={"queue": ids, "current_index": 1, "position": 0.0, "volume": 1.0},
    )

    state = client.get("/api/player").json()
    assert [t["id"] for t in state["queue"]] == ids
    assert state["current_index"] == 1
