def upload(client, paths):
    files = [("files", (path.name, path.read_bytes(), "audio/mpeg")) for path in paths]
    return client.post("/api/import", files=files)


def test_import_valid_track(client, make_mp3):
    track = make_mp3("song.mp3", title="Faixa de Teste", artist="Artista Teste")

    response = upload(client, [track])

    assert response.status_code == 200
    assert len(response.json()["imported"]) == 1

    library = client.get("/api/library").json()
    assert len(library["tracks"]) == 1
    assert library["tracks"][0]["title"] == "Faixa de Teste"
    assert library["tracks"][0]["artist"] == "Artista Teste"


def test_import_duplicate_is_ignored(client, make_mp3, tmp_path):
    first = make_mp3("a.mp3", freq=440)
    second = tmp_path / "b.mp3"
    second.write_bytes(first.read_bytes())

    first_response = upload(client, [first])
    second_response = upload(client, [second])

    assert len(first_response.json()["imported"]) == 1
    assert second_response.json()["imported"] == []
    assert len(second_response.json()["duplicates"]) == 1

    library = client.get("/api/library").json()
    assert len(library["tracks"]) == 1


def test_import_uses_filename_when_untagged(client, make_mp3):
    track = make_mp3("plain-name.mp3", freq=660)

    upload(client, [track])

    library = client.get("/api/library").json()
    assert library["tracks"][0]["title"] == "plain-name"
    assert library["tracks"][0]["format"] == "mp3"


def test_import_invalid_file_becomes_unrecognized(client, tmp_path):
    junk = tmp_path / "notes.txt"
    junk.write_text("isto nao e audio")

    response = upload(client, [junk])

    assert response.json()["imported"] == []
    assert len(response.json()["unrecognized"]) == 1

    library = client.get("/api/library").json()
    assert library["tracks"] == []
    assert len(library["unrecognized"]) == 1
