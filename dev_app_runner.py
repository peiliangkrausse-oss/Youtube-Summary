import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WATCHED_SUFFIXES = {".py", ".html", ".css", ".js"}
WATCHED_DIRS = (
    ROOT / "watchless_app",
    ROOT / "desktop_app.py",
)
POLL_INTERVAL_SECONDS = 1.0


def iter_watched_files() -> list[Path]:
    files: list[Path] = []

    for entry in WATCHED_DIRS:
        if entry.is_file():
            files.append(entry)
            continue

        if not entry.exists():
            continue

        for path in entry.rglob("*"):
            if path.is_file() and path.suffix in WATCHED_SUFFIXES:
                files.append(path)

    return files


def snapshot_mtimes() -> dict[Path, int]:
    mtimes: dict[Path, int] = {}

    for path in iter_watched_files():
        try:
            mtimes[path] = path.stat().st_mtime_ns
        except FileNotFoundError:
            continue

    return mtimes


def start_app() -> subprocess.Popen[bytes]:
    print("Launching WatchLess desktop app from source...")
    return subprocess.Popen([sys.executable, "desktop_app.py"], cwd=ROOT)


def stop_app(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return

    process.terminate()

    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> None:
    previous_snapshot = snapshot_mtimes()
    process = start_app()

    try:
        while True:
            if process.poll() is not None:
                print("Desktop app closed. Stopping dev watcher.")
                break

            time.sleep(POLL_INTERVAL_SECONDS)
            current_snapshot = snapshot_mtimes()

            if current_snapshot != previous_snapshot:
                print("Change detected. Restarting desktop app...")
                stop_app(process)
                process = start_app()
                previous_snapshot = current_snapshot
    except KeyboardInterrupt:
        print("\nStopping WatchLess dev app watcher.")
    finally:
        stop_app(process)


if __name__ == "__main__":
    main()
