import json
from pathlib import Path

from watchless_app.config import APP_SUPPORT_DIR, LM_STUDIO_PORT, OLLAMA_BASE_URL


SETTINGS_FILE = APP_SUPPORT_DIR / "settings.json"
SUPPORTED_PROVIDERS = {"lm_studio", "ollama"}


class SettingsStore:
    def __init__(self, path: Path = SETTINGS_FILE):
        self.path = path

    def load(self) -> dict:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
        has_saved_port = isinstance(payload, dict) and "lm_studio_port" in payload
        return {
            "provider": self._valid_provider(payload.get("provider")),
            "lm_studio_port": self._valid_port(payload.get("lm_studio_port"), LM_STUDIO_PORT),
            "lm_studio_port_saved": has_saved_port,
        }

    def save_lm_studio_port(self, port: int | str) -> dict:
        settings = self.load()
        settings["lm_studio_port"] = self._valid_port(port, LM_STUDIO_PORT)
        return self._save(settings)

    def save_provider(self, provider: str | None) -> dict:
        settings = self.load()
        settings["provider"] = self._valid_provider(provider)
        return self._save(settings)

    def _save(self, settings: dict) -> dict:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
        return settings

    def lm_studio_base_url(self) -> str:
        return f"http://127.0.0.1:{self.load()['lm_studio_port']}/v1"

    def lm_studio_native_base_url(self) -> str:
        return f"http://127.0.0.1:{self.load()['lm_studio_port']}/api/v1"

    def ollama_base_url(self) -> str:
        return OLLAMA_BASE_URL

    def _valid_port(self, value: int | str | None, fallback: int) -> int:
        try:
            port = int(value)
        except (TypeError, ValueError):
            return fallback
        if port < 1 or port > 65535:
            return fallback
        return port

    def _valid_provider(self, value: str | None) -> str:
        selected = str(value or "").strip().lower()
        return selected if selected in SUPPORTED_PROVIDERS else "lm_studio"
