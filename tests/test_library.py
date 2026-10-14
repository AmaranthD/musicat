def test_search_filters_by_artist(client, make_mp3, upload):
    upload([make_mp3("a.mp3", title="Primeira", artist="Gatinho", freq=440)])
    upload([make_mp3("b.mp3", title="Segunda", artist="Cachorro", freq=550)])

    found = client.get("/api/library", params={"search": "Gatinho"}).json()["tracks"]

    assert [t["title"] for t in found] == ["Primeira"]


def test_sort_by_title(client, make_mp3, upload):
    upload([make_mp3("a.mp3", title="Zebra", freq=440)])
    upload([make_mp3("b.mp3", title="Abelha", freq=550)])

    ordered = client.get("/api/library", params={"sort": "title"}).json()["tracks"]

    assert [t["title"] for t in ordered] == ["Abelha", "Zebra"]


def test_edit_metadata_creates_override(client, make_mp3, upload):
    upload([make_mp3("song.mp3", title="Original", artist="Antigo")])
    track = client.get("/api/library").json()["tracks"][0]

    updated = client.patch(
        f"/api/tracks/{track['id']}",
        json={"title": "Corrigido", "artist": "Novo"},
    ).json()

    assert updated["title"] == "Corrigido"
    assert updated["artist"] == "Novo"
    assert client.get("/api/library").json()["tracks"][0]["title"] == "Corrigido"


def test_cover_endpoint_returns_404_when_missing(client, make_mp3, upload):
    upload([make_mp3("song.mp3", freq=440)])
    track = client.get("/api/library").json()["tracks"][0]

    assert client.get(f"/api/tracks/{track['id']}/cover").status_code == 404


def test_unrecognized_can_be_removed(client, tmp_path, upload):
    junk = tmp_path / "notes.txt"
    junk.write_text("isto nao e audio")
    upload([junk])
    item = client.get("/api/library").json()["unrecognized"][0]

    response = client.delete(f"/api/unrecognized/{item['id']}")

    assert response.status_code == 200
    assert client.get("/api/library").json()["unrecognized"] == []
