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
    preferred = config.port()
    port = preferred if config.strict_port() else pick_port(host, preferred)
    display_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    url = f"http://{display_host}:{port}/"
    if config.open_browser():
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    uvicorn.run(create_app(), host=host, port=port, proxy_headers=True)


if __name__ == "__main__":
    main()
