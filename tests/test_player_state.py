def test_player_state_round_trip(client, make_mp3, upload):
    upload([make_mp3("a.mp3", freq=440)])
    track = client.get("/api/library").json()["tracks"][0]

    client.put(
        "/api/player",
        json={"queue": [track["id"]], "current_index": 0, "position": 12.5, "volume": 0.4},
    )

    state = client.get("/api/player").json()

    assert [t["id"] for t in state["queue"]] == [track["id"]]
    assert state["current_index"] == 0
    assert state["position"] == 12.5
    assert state["volume"] == 0.4


def test_player_state_defaults_when_empty(client):
    state = client.get("/api/player").json()

    assert state["queue"] == []
    assert state["volume"] == 1.0
