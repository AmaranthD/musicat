import subprocess

import pytest
from fastapi.testclient import TestClient

from musicat.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("MUSICAT_DATA_DIR", str(tmp_path / "data"))
    return TestClient(create_app())


@pytest.fixture
def make_mp3(tmp_path):
    def _make(name="track.mp3", title=None, artist=None, album=None, freq=440):
        out = tmp_path / name
        cmd = ["ffmpeg", "-f", "lavfi", "-i", f"sine=frequency={freq}:duration=1"]
        if title:
            cmd += ["-metadata", f"title={title}"]
        if artist:
            cmd += ["-metadata", f"artist={artist}"]
        if album:
            cmd += ["-metadata", f"album={album}"]
        cmd += ["-y", str(out)]
        subprocess.run(cmd, check=True, capture_output=True)
        return out

    return _make


@pytest.fixture
def upload(client):
    def _upload(paths):
        files = [
            ("files", (path.name, path.read_bytes(), "audio/mpeg")) for path in paths
        ]
        return client.post("/api/import", files=files)

    return _upload
