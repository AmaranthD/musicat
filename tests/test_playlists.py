def make_library(client, make_mp3, upload):
    upload([make_mp3("a.mp3", title="Primeira", artist="Gato", freq=440)])
    upload([make_mp3("b.mp3", title="Segunda", artist="Gato", freq=550)])
    return client.get("/api/library").json()["tracks"]


def test_create_add_and_get_playlist(client, make_mp3, upload):
    tracks = make_library(client, make_mp3, upload)
    playlist = client.post("/api/playlists", json={"name": "Favoritas"}).json()

    for track in tracks:
        client.post(f"/api/playlists/{playlist['id']}/tracks", json={"track_id": track["id"]})

    detail = client.get(f"/api/playlists/{playlist['id']}").json()

    assert detail["name"] == "Favoritas"
    assert [t["id"] for t in detail["tracks"]] == [t["id"] for t in tracks]


def test_reorder_playlist(client, make_mp3, upload):
    tracks = make_library(client, make_mp3, upload)
    playlist = client.post("/api/playlists", json={"name": "Ordem"}).json()
    for track in tracks:
        client.post(f"/api/playlists/{playlist['id']}/tracks", json={"track_id": track["id"]})

    reversed_ids = [t["id"] for t in reversed(tracks)]
    client.put(f"/api/playlists/{playlist['id']}/tracks", json={"track_ids": reversed_ids})

    detail = client.get(f"/api/playlists/{playlist['id']}").json()
    assert [t["id"] for t in detail["tracks"]] == reversed_ids


def test_rename_and_delete_playlist(client):
    playlist = client.post("/api/playlists", json={"name": "Antiga"}).json()

    renamed = client.patch(f"/api/playlists/{playlist['id']}", json={"name": "Nova"}).json()
    assert renamed["name"] == "Nova"

    client.delete(f"/api/playlists/{playlist['id']}")
    assert client.get("/api/playlists").json()["playlists"] == []


def test_remove_track_from_playlist(client, make_mp3, upload):
    tracks = make_library(client, make_mp3, upload)
    playlist = client.post("/api/playlists", json={"name": "Mix"}).json()
    client.post(f"/api/playlists/{playlist['id']}/tracks", json={"track_id": tracks[0]["id"]})

    client.delete(f"/api/playlists/{playlist['id']}/tracks/{tracks[0]['id']}")

    detail = client.get(f"/api/playlists/{playlist['id']}").json()
    assert detail["tracks"] == []


def test_playlists_list_reports_counts(client, make_mp3, upload):
    tracks = make_library(client, make_mp3, upload)
    playlist = client.post("/api/playlists", json={"name": "Count"}).json()
    client.post(f"/api/playlists/{playlist['id']}/tracks", json={"track_id": tracks[0]["id"]})

    listed = client.get("/api/playlists").json()["playlists"]

    assert listed[0]["track_count"] == 1
