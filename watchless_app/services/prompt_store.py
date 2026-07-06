import json
import re
from datetime import datetime, timezone

from watchless_app.config import DEFAULT_PROMPT, PROMPT_PRESET_FILE, PROMPT_PRESETS_DIR


def _slugify(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z_-]+", "-", value or "").strip("-").lower()
    return slug[:70] or "prompt-preset"


class PromptStore:
    def load(self) -> tuple[str, bool]:
        try:
            with PROMPT_PRESET_FILE.open("r", encoding="utf-8") as preset_file:
                payload = json.load(preset_file)
            prompt = payload.get("prompt", "") if isinstance(payload, dict) else ""
            if isinstance(prompt, str) and prompt.strip():
                return prompt.strip(), False
        except FileNotFoundError:
            pass
        except Exception:
            pass
        return DEFAULT_PROMPT, True

    def save(self, prompt: str, preset_id: str = "") -> str:
        cleaned = (prompt or "").strip()
        if not cleaned:
            raise ValueError("Prompt cannot be empty.")
        safe_preset_id = _slugify(preset_id) if preset_id else ""
        PROMPT_PRESET_FILE.parent.mkdir(parents=True, exist_ok=True)
        with PROMPT_PRESET_FILE.open("w", encoding="utf-8") as preset_file:
            json.dump({"prompt": cleaned, "preset_id": safe_preset_id}, preset_file, ensure_ascii=False, indent=2)
        return cleaned

    def reset(self) -> str:
        try:
            PROMPT_PRESET_FILE.unlink()
        except FileNotFoundError:
            pass
        return DEFAULT_PROMPT

    def list_presets(self) -> list[dict]:
        active_prompt, is_builtin_default = self.load()
        active_prompt = active_prompt.strip()
        active_preset_id = ""
        try:
            with PROMPT_PRESET_FILE.open("r", encoding="utf-8") as preset_file:
                payload = json.load(preset_file)
            active_preset_id = _slugify(payload.get("preset_id", "")) if isinstance(payload, dict) else ""
        except Exception:
            active_preset_id = ""
        presets = [
            {
                "id": "built-in-default",
                "name": "Built-in default",
                "prompt": DEFAULT_PROMPT,
                "created_at": "",
                "is_builtin": True,
                "is_default": False,
            }
        ]
        matching_custom_default = ""
        try:
            PROMPT_PRESETS_DIR.mkdir(parents=True, exist_ok=True)
        except OSError:
            presets[0]["is_default"] = DEFAULT_PROMPT.strip() == active_prompt
            return presets
        for path in sorted(PROMPT_PRESETS_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                prompt = payload.get("prompt", "")
                name = payload.get("name", path.stem)
                if isinstance(prompt, str) and prompt.strip():
                    presets.append({
                        "id": path.stem,
                        "name": name,
                        "prompt": prompt,
                        "created_at": payload.get("created_at", ""),
                        "is_builtin": False,
                        "is_default": False,
                    })
                    if not matching_custom_default and prompt.strip() == active_prompt:
                        matching_custom_default = path.stem
            except Exception:
                continue
        if active_preset_id and not is_builtin_default and any(preset["id"] == active_preset_id for preset in presets):
            for preset in presets:
                preset["is_default"] = preset["id"] == active_preset_id
        elif matching_custom_default and not is_builtin_default:
            for preset in presets:
                preset["is_default"] = preset["id"] == matching_custom_default
        else:
            presets[0]["is_default"] = DEFAULT_PROMPT.strip() == active_prompt
        return presets

    def save_preset(self, name: str, prompt: str) -> dict:
        cleaned_prompt = (prompt or "").strip()
        cleaned_name = (name or "").strip() or "Custom prompt"
        if not cleaned_prompt:
            raise ValueError("Prompt cannot be empty.")
        try:
            PROMPT_PRESETS_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ValueError(f"Could not create prompt preset folder: {PROMPT_PRESETS_DIR}") from exc
        preset_id = _slugify(cleaned_name)
        path = PROMPT_PRESETS_DIR / f"{preset_id}.json"
        if path.exists():
            preset_id = f"{preset_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            path = PROMPT_PRESETS_DIR / f"{preset_id}.json"
        payload = {
            "id": preset_id,
            "name": cleaned_name,
            "prompt": cleaned_prompt,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload

    def get_preset(self, preset_id: str) -> dict:
        if preset_id == "built-in-default":
            return {
                "id": "built-in-default",
                "name": "Built-in default",
                "prompt": DEFAULT_PROMPT,
                "is_builtin": True,
            }
        safe_id = _slugify(preset_id)
        path = PROMPT_PRESETS_DIR / f"{safe_id}.json"
        if not path.exists():
            raise FileNotFoundError("Prompt preset not found.")
        return json.loads(path.read_text(encoding="utf-8"))

    def rename_preset(self, preset_id: str, name: str) -> dict:
        if preset_id == "built-in-default":
            raise ValueError("The built-in preset cannot be renamed.")
        cleaned_name = (name or "").strip()
        if not cleaned_name:
            raise ValueError("Preset name cannot be empty.")
        preset = self.get_preset(preset_id)
        old_path = PROMPT_PRESETS_DIR / f"{_slugify(preset_id)}.json"
        new_id = _slugify(cleaned_name)
        new_path = PROMPT_PRESETS_DIR / f"{new_id}.json"
        if new_path.exists() and new_path != old_path:
            new_id = f"{new_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            new_path = PROMPT_PRESETS_DIR / f"{new_id}.json"
        preset["id"] = new_id
        preset["name"] = cleaned_name
        preset["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        new_path.write_text(json.dumps(preset, ensure_ascii=False, indent=2), encoding="utf-8")
        if new_path != old_path:
            old_path.unlink(missing_ok=True)
        return preset

    def delete_preset(self, preset_id: str) -> None:
        if preset_id == "built-in-default":
            raise ValueError("The built-in preset cannot be deleted.")
        path = PROMPT_PRESETS_DIR / f"{_slugify(preset_id)}.json"
        if not path.exists():
            raise FileNotFoundError("Prompt preset not found.")
        path.unlink()
