import socket
import threading
import webbrowser

import uvicorn

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
    host = "127.0.0.1"
    port = pick_port(host, 8000)
    url = f"http://{host}:{port}/"
    threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    uvicorn.run(create_app(), host=host, port=port)


if __name__ == "__main__":
    main()
