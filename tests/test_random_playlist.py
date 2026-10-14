def test_random_playlist_respects_size(client, make_mp3, upload):
    for index, freq in enumerate([440, 550, 660, 770]):
        upload([make_mp3(f"t{index}.mp3", freq=freq)])

    playlist = client.post("/api/playlists/random", json={"size": 2, "name": "Sorte"}).json()

    assert playlist["name"] == "Sorte"
    assert len(playlist["tracks"]) == 2


def test_random_playlist_respects_artist_filter(client, make_mp3, upload):
    upload([make_mp3("a.mp3", artist="Gato", freq=440)])
    upload([make_mp3("b.mp3", artist="Cachorro", freq=550)])

    playlist = client.post("/api/playlists/random", json={"artist": "Gato"}).json()

    assert [t["artist"] for t in playlist["tracks"]] == ["Gato"]


def test_random_playlist_is_saved_as_normal_playlist(client, make_mp3, upload):
    upload([make_mp3("a.mp3", freq=440)])

    client.post("/api/playlists/random", json={})

    assert len(client.get("/api/playlists").json()["playlists"]) == 1
