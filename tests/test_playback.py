def test_stream_returns_audio(client, make_mp3, upload):
    upload([make_mp3("song.mp3", freq=440)])
    track = client.get("/api/library").json()["tracks"][0]

    response = client.get(f"/api/tracks/{track['id']}/stream")

    assert response.status_code == 200
    assert len(response.content) > 0


def test_stream_supports_range(client, make_mp3, upload):
    upload([make_mp3("song.mp3", freq=440)])
    track = client.get("/api/library").json()["tracks"][0]

    response = client.get(
        f"/api/tracks/{track['id']}/stream",
        headers={"Range": "bytes=0-99"},
    )

    assert response.status_code == 206
    assert len(response.content) == 100


def test_stream_missing_track_is_404(client):
    assert client.get("/api/tracks/999/stream").status_code == 404
