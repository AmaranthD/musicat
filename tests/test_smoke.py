from fastapi.testclient import TestClient

from musicat.app import create_app


def test_serves_index(tmp_path, monkeypatch):
    monkeypatch.setenv("MUSICAT_DATA_DIR", str(tmp_path / "data"))
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "Musicat" in response.text


def test_creates_data_dir_on_startup(tmp_path, monkeypatch):
    data = tmp_path / "data"
    monkeypatch.setenv("MUSICAT_DATA_DIR", str(data))

    create_app()

    assert data.is_dir()
