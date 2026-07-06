from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from watchless_app.config import APP_SUPPORT_DIR


DEFAULT_SERVER_URL = "http://127.0.0.1:5000"


class LocalVoiceRunner:
    def __init__(self, server_url: str = ""):
        self.server_url = (server_url or f"http://{self.host()}:{self.port()}").rstrip("/")
        parsed = urlparse(self.server_url)
        self.server_host = parsed.hostname or self.host()
        self.server_port = str(parsed.port or self.port())
        self.process: subprocess.Popen | None = None
        self.log_file = None
        self.last_error: str = ""

    @staticmethod
    def watchless_root() -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parents[1] / "Resources"
        return Path(__file__).resolve().parents[2]

    @staticmethod
    def app_container_dir() -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parents[3]
        return Path(__file__).resolve().parents[3]

    @classmethod
    def local_voice_script_path(cls) -> Path:
        return cls.watchless_root() / "watchless_app" / "local_voice_server.py"

    @classmethod
    def style_bert_candidates(cls) -> list[Path]:
        configured = os.environ.get("WATCHLESS_LOCAL_VOICE_REPO", "").strip()
        candidates = []
        if configured:
            candidates.append(Path(configured).expanduser())
        candidates.extend(
            [
                APP_SUPPORT_DIR / "Style-Bert-VITS2",
                APP_SUPPORT_DIR / "local_voice" / "Style-Bert-VITS2",
                cls.app_container_dir() / "Style-Bert-VITS2",
                Path.home() / "Style-Bert-VITS2",
                Path.home() / "style-bert-vits2-local",
            ]
        )
        unique = []
        seen = set()
        for candidate in candidates:
            resolved = candidate.expanduser()
            key = str(resolved)
            if key not in seen:
                unique.append(resolved)
                seen.add(key)
        return unique

    @staticmethod
    def is_style_bert_root(path: Path) -> bool:
        return (path / ".venv" / "bin" / "python").exists() and (path / "model_assets").exists()

    @classmethod
    def style_bert_root(cls) -> Path:
        configured = os.environ.get("WATCHLESS_LOCAL_VOICE_REPO", "").strip()
        if configured:
            return Path(configured).expanduser()
        for candidate in cls.style_bert_candidates():
            if cls.is_style_bert_root(candidate):
                return candidate
        return Path.home() / "Style-Bert-VITS2"

    @classmethod
    def style_bert_python(cls) -> Path:
        return cls.style_bert_root() / ".venv" / "bin" / "python"

    @classmethod
    def assets_root(cls) -> Path:
        configured = os.environ.get("WATCHLESS_LOCAL_VOICE_ASSETS_ROOT", "").strip()
        return Path(configured).expanduser() if configured else (cls.style_bert_root() / "model_assets")

    @staticmethod
    def host() -> str:
        return os.environ.get("WATCHLESS_LOCAL_VOICE_HOST", "127.0.0.1").strip() or "127.0.0.1"

    @staticmethod
    def port() -> str:
        return os.environ.get("WATCHLESS_LOCAL_VOICE_PORT", "5000").strip() or "5000"

    @staticmethod
    def log_path() -> Path:
        return APP_SUPPORT_DIR / "logs" / "local_voice_server.log"

    @staticmethod
    def fallback_log_path() -> Path:
        return Path(tempfile.gettempdir()) / "watchless_local_voice_server.log"

    @classmethod
    def open_log_file(cls):
        primary = cls.log_path()
        try:
            primary.parent.mkdir(parents=True, exist_ok=True)
            return primary.open("a", encoding="utf-8"), primary
        except OSError:
            fallback = cls.fallback_log_path()
            return fallback.open("a", encoding="utf-8"), fallback

    def status_url(self) -> str:
        return f"{self.server_url}/status"

    def is_running(self) -> bool:
        try:
            with urlopen(self.status_url(), timeout=1.5) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return payload.get("service") == "watchless-local-voice" and bool(payload.get("ok"))
        except Exception:
            return False

    def command(self) -> list[str]:
        return [
            str(self.style_bert_python()),
            str(self.local_voice_script_path()),
            "--style-bert-dir",
            str(self.style_bert_root()),
            "--assets-root",
            str(self.assets_root()),
            "--host",
            self.server_host,
            "--port",
            self.server_port,
            "--device",
            "cpu",
        ]

    def ensure_started(self, wait_timeout: float = 3.0) -> bool:
        if self.is_running():
            self.last_error = ""
            return True
        if self.process and self.process.poll() is None:
            return self._wait_until_ready(wait_timeout)

        python_path = self.style_bert_python()
        script_path = self.local_voice_script_path()
        if not python_path.exists():
            searched = ", ".join(str(path) for path in self.style_bert_candidates())
            self.last_error = (
                f"Style-Bert Python was not found at {python_path}. "
                f"WatchLess searched these folders: {searched}."
            )
            return False
        if not script_path.exists():
            self.last_error = f"Local voice server script was not found at {script_path}."
            return False

        self.log_file, log_path = self.open_log_file()
        self.process = subprocess.Popen(
            self.command(),
            stdout=self.log_file,
            stderr=subprocess.STDOUT,
            cwd=self.watchless_root(),
            start_new_session=True,
        )
        if self._wait_until_ready(wait_timeout):
            self.last_error = ""
            return True
        self.last_error = (
            "WatchLess tried to start the local voice server, but it did not become ready in time. "
            f"Check the log at {log_path}."
        )
        if self.process and self.process.poll() is not None:
            self._close_log_file()
        return False

    def _wait_until_ready(self, wait_timeout: float) -> bool:
        deadline = time.time() + wait_timeout
        while time.time() < deadline:
            if self.is_running():
                return True
            if self.process and self.process.poll() is not None:
                return False
            time.sleep(0.2)
        return self.is_running()

    def stop(self) -> None:
        if not self.process or self.process.poll() is not None:
            self._close_log_file()
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=2)
        self._close_log_file()

    def _close_log_file(self) -> None:
        if self.log_file:
            self.log_file.close()
            self.log_file = None
