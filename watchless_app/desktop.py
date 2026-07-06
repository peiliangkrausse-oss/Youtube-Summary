import socket
import sys
import threading
import time
from pathlib import Path
from urllib.request import urlopen

import webview

from watchless_app.app import create_app
from watchless_app.config import APP_NAME, PORT
from watchless_app.services.local_voice_runner import LocalVoiceRunner

APP_ICON_FILENAME = "WatchLess.icns"


def local_voice_routes_loaded(host: str, port: int) -> bool:
    try:
        with urlopen(f"http://{host}:{port}/api/narration/local/catalog", timeout=1) as response:
            return response.status == 200
    except Exception:
        return False


def wait_for_server(host: str = "127.0.0.1", port: int = PORT, timeout: int = 10) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        if local_voice_routes_loaded(host, port):
            return True
        time.sleep(0.2)
    return False


def port_is_available(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((host, port))
            return True
    except OSError:
        return False


def available_port(host: str = "127.0.0.1", preferred: int = PORT) -> int:
    if port_is_available(host, preferred):
        return preferred
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def run_server(port: int) -> None:
    app = create_app()
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


def app_icon_path() -> str | None:
    if getattr(sys, "frozen", False):
        candidate = Path(sys.executable).resolve().parents[1] / "Resources" / APP_ICON_FILENAME
    else:
        candidate = Path(__file__).resolve().parents[1] / "App Icons" / APP_ICON_FILENAME
    return str(candidate) if candidate.exists() else None


def main() -> None:
    webview.settings["SHOW_DEFAULT_MENUS"] = True
    webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True

    local_voice_runner = LocalVoiceRunner()
    local_voice_runner.ensure_started()

    port = available_port()
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()

    if not wait_for_server(port=port):
        raise RuntimeError(f"Local server did not start on port {port}.")

    try:
        webview.create_window(
            APP_NAME,
            f"http://127.0.0.1:{port}/",
            width=1600,
            height=1000,
            min_size=(1100, 720),
            text_select=True,
        )
        webview.start(icon=app_icon_path())
    finally:
        local_voice_runner.stop()


if __name__ == "__main__":
    main()
