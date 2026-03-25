from __future__ import annotations

import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
UI_DIR = BASE_DIR / "ui"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8030


def get_server_address() -> tuple[str, int]:
    host = os.getenv("SHELL_HOST", DEFAULT_HOST).strip() or DEFAULT_HOST
    port_value = os.getenv("SHELL_PORT", str(DEFAULT_PORT)).strip() or str(DEFAULT_PORT)

    try:
        port = int(port_value)
    except ValueError as error:
        raise ValueError(f"Invalid SHELL_PORT value: {port_value}") from error

    return host, port


def main() -> None:
    handler = partial(SimpleHTTPRequestHandler, directory=str(UI_DIR))
    host, port = get_server_address()
    server = ThreadingHTTPServer((host, port), handler)

    print(f"Shell UI serving {UI_DIR} at http://{host}:{port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shell UI stopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
