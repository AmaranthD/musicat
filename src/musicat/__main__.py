import socket
import threading
import webbrowser

import uvicorn

from . import config
from .app import create_app


def pick_port(host: str, preferred: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, preferred))
            return preferred
        except OSError:
            sock.bind((host, 0))
            return sock.getsockname()[1]


def main() -> None:
    host = config.host()
    port = pick_port(host, config.port())
    url = f"http://{'127.0.0.1' if host == '0.0.0.0' else host}:{port}/"
    threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    uvicorn.run(create_app(), host=host, port=port)


if __name__ == "__main__":
    main()
