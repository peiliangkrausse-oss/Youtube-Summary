import json
import mimetypes
import os
from pathlib import Path
import re
import subprocess
import ssl
import sys
from secrets import token_hex
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
import webbrowser

from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context

from watchless_app.config import DONATION_URL, FEEDBACK_EMAIL
from watchless_app.errors import AppError
from watchless_app.services.job_queue import serialize_job
from watchless_app.services.local_voice_runner import LocalVoiceRunner

try:
    import certifi
except Exception:  # pragma: no cover - certifi is installed through requests in normal app installs.
    certifi = None


api_bp = Blueprint("api", __name__, url_prefix="/api")
legacy_bp = Blueprint("legacy_api", __name__)
ALLOWED_VOICE_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".webm"}
ALLOWED_VOICE_MIME_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/aac",
    "audio/flac",
    "audio/ogg",
    "audio/webm",
}
VOICE_FILE_TYPE_MESSAGE = "Upload an audio file in one of these formats: MP3, WAV, M4A, AAC, FLAC, OGG, or WEBM."
ELEVENLABS_CERTIFICATE_MESSAGE = (
    "WatchLess could not verify ElevenLabs' secure HTTPS certificate. "
    "This means your local Python certificate bundle is missing or outdated; your API key was not tested yet. "
    "Fix on macOS: open the Python folder in Applications and run Install Certificates.command, then restart WatchLess."
)
LOCAL_VOICE_SPACE_RESOLVE_ROOT = "https://huggingface.co/spaces/Kit-Lemonfoot/Hololive-Style-Bert-VITS2/resolve/main/model_assets"
LOCAL_VOICE_DEFAULT_SERVER = "http://127.0.0.1:5000"
ELEVENLABS_VOICES_URL = "https://api.elevenlabs.io/v2/voices"
LOCAL_VOICE_MODELS = [
    {
        "id": "SBV2_HoloHi",
        "name": "HoloHi shared pack",
        "folder": "SBV2_HoloHi",
        "primary_language": "EN",
        "languages": ["EN"],
        "style": "Higher-pitched English anime voices: Gura, Fauna, Ina, Mumei, IRyS, Amelia, Shiori.",
        "voice_type": "English anime-style",
        "files": [
            "config.json",
            "style_vectors.npy",
            "SBV2_HoloHi.safetensors",
        ],
    },
    {
        "id": "SBV2_HoloLow",
        "name": "HoloLow shared pack",
        "folder": "SBV2_HoloLow",
        "primary_language": "EN",
        "languages": ["EN"],
        "style": "Lower-pitched English anime voices: Calliope, Kronii, Nerissa.",
        "voice_type": "English anime-style",
        "files": [
            "config.json",
            "style_vectors.npy",
            "SBV2_HoloLow.safetensors",
        ],
    },
    {
        "id": "SBV2_HoloAus",
        "name": "HoloAus shared pack",
        "folder": "SBV2_HoloAus",
        "primary_language": "EN",
        "languages": ["EN"],
        "style": "Australian English anime voices: Baelz and Sana.",
        "voice_type": "English anime-style",
        "files": [
            "config.json",
            "style_vectors.npy",
            "SBV2_HoloAus.safetensors",
        ],
    },
    {
        "id": "SBV2_KosekiBijou",
        "name": "Koseki Bijou",
        "folder": "SBV2_KosekiBijou",
        "primary_language": "EN",
        "languages": ["EN"],
        "style": "Bright English anime voice with normal, scared, angry, and excited styles.",
        "voice_type": "English anime-style",
        "files": [
            "config.json",
            "style_vectors.npy",
            "SBV2_KosekiBijou.safetensors",
        ],
    },
    {
        "id": "SBV2_TakanashiKiara",
        "name": "Takanashi Kiara",
        "folder": "SBV2_TakanashiKiara",
        "primary_language": "EN",
        "languages": ["EN", "JP-style"],
        "style": "Bright anime idol voice with strong English support.",
        "voice_type": "English anime-style",
        "files": [
            "config.json",
            "style_vectors.npy",
            "SBV2_TakanashiKiara.safetensors",
        ],
    },
    {
        "id": "SBV2_HoloESL",
        "name": "HoloESL shared pack",
        "folder": "SBV2_HoloESL",
        "primary_language": "ESL",
        "languages": ["EN", "ID"],
        "style": "English-as-second-language anime voices: Risu, Moona, Iofi, Anya.",
        "voice_type": "ESL anime-style",
        "files": [
            "config.json",
            "style_vectors.npy",
            "SBV2_HoloESL.safetensors",
        ],
    },
    {
        "id": "SBV2_HoloIDFlu",
        "name": "HoloID fluent pack",
        "folder": "SBV2_HoloIDFlu",
        "primary_language": "ESL",
        "languages": ["EN", "ID"],
        "style": "Indonesian/English anime voices: Ollie and Zeta.",
        "voice_type": "ESL anime-style",
        "files": [
            "config.json",
            "style_vectors.npy",
            "SBV2_HoloIDFlu.safetensors",
        ],
    },
    {
        "id": "SBV2_HoloJPBaby",
        "name": "HoloJP baby pack",
        "folder": "SBV2_HoloJPBaby",
        "primary_language": "JP",
        "languages": ["JP"],
        "style": "Japanese anime voices: Sakura Miko and Himemori Luna.",
        "voice_type": "Japanese anime-style",
        "files": [
            "config.json",
            "style_vectors.npy",
            "SBV2_HoloJPBaby.safetensors",
        ],
    },
    {
        "id": "SBV2_HoloJPTest",
        "name": "HoloJP shared pack 1",
        "folder": "SBV2_HoloJPTest",
        "primary_language": "JP",
        "languages": ["JP"],
        "style": "Japanese anime voices including Okayu, Flare, Noel, Marine, Laplus, and Ririka.",
        "voice_type": "Japanese anime-style",
        "files": [
            "config.json",
            "style_vectors.npy",
            "SBV2_HoloJPTest.safetensors",
        ],
    },
    {
        "id": "SBV2_HoloJPTest2",
        "name": "HoloJP shared pack 2",
        "folder": "SBV2_HoloJPTest2",
        "primary_language": "JP",
        "languages": ["JP"],
        "style": "Japanese anime voices including Sora, Suisei, Aqua, Ayame, Towa, Lamy, Koyori, and Chloe.",
        "voice_type": "Japanese anime-style",
        "files": [
            "config.json",
            "style_vectors.npy",
            "SBV2_HoloJPTest2.safetensors",
        ],
    },
    {
        "id": "SBV2_HoloJPTest2.5",
        "name": "HoloJP shared pack 2.5",
        "folder": "SBV2_HoloJPTest2.5",
        "primary_language": "JP",
        "languages": ["JP"],
        "style": "Japanese anime voices including AZKi, Mel, Matsuri, Aki, Haato, and Lui.",
        "voice_type": "Japanese anime-style",
        "files": [
            "config.json",
            "style_vectors.npy",
            "SBV2_HoloJPTest2.5.safetensors",
        ],
    },
    {
        "id": "SBV2_HoloJPTest3",
        "name": "HoloJP shared pack 3",
        "folder": "SBV2_HoloJPTest3",
        "primary_language": "JP",
        "languages": ["JP"],
        "style": "Japanese anime voices including Fubuki, Subaru, Rushia, Kanata, Watame, Nene, Polka, and Raden.",
        "voice_type": "Japanese anime-style",
        "files": [
            "config.json",
            "style_vectors.npy",
            "SBV2_HoloJPTest3.safetensors",
        ],
    },
    {
        "id": "SBV2_UsadaPekora",
        "name": "Usada Pekora",
        "folder": "SBV2_UsadaPekora",
        "primary_language": "JP",
        "languages": ["JP"],
        "style": "Japanese anime voice with excited, thoughtful, explaining, mama, and sad styles.",
        "voice_type": "Japanese anime-style",
        "files": [
            "config.json",
            "style_vectors.npy",
            "SBV2_UsadaPekora.safetensors",
        ],
    },
]


def _json_error(exc: Exception, status_code: int = 500):
    if isinstance(exc, AppError):
        return jsonify({"ok": False, "error": exc.message, "error_type": exc.error_type}), exc.status_code
    return jsonify({"ok": False, "error": str(exc), "error_type": "unexpected_error"}), status_code


def _open_external_url(url: str) -> bool:
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", url])
            return True
        if os.name == "nt":
            os.startfile(url)  # type: ignore[attr-defined]
            return True
        subprocess.Popen(["xdg-open", url])
        return True
    except Exception:
        return bool(webbrowser.open(url, new=1))


def _clean_elevenlabs_api_key(api_key: str = "") -> str:
    cleaned = (api_key or "").translate({
        ord("\u200b"): None,
        ord("\u200c"): None,
        ord("\u200d"): None,
        ord("\ufeff"): None,
    }).strip().strip("\"'")
    cleaned = re.sub(r"(?i)^xi-api-key\s*:\s*", "", cleaned).strip()
    cleaned = re.sub(r"(?i)^bearer\s+", "", cleaned).strip()
    return cleaned.strip("\"'")


def _elevenlabs_api_key(api_key: str = "") -> str:
    api_key = _clean_elevenlabs_api_key(api_key) or _clean_elevenlabs_api_key(request.headers.get("X-ElevenLabs-Api-Key", ""))
    api_key = api_key or _clean_elevenlabs_api_key(request.form.get("api_key", ""))
    api_key = api_key or _clean_elevenlabs_api_key(os.environ.get("ELEVENLABS_API_KEY", ""))
    if not api_key:
        raise AppError(
            "Connect ElevenLabs first by adding your API key in WatchLess.",
            "anime_voice_not_configured",
            400,
        )
    return api_key


def _trusted_ssl_context():
    if certifi:
        return ssl.create_default_context(cafile=certifi.where())
    return ssl.create_default_context()


def _elevenlabs_ssl_context():
    return _trusted_ssl_context()


def _elevenlabs_json_error(exc: HTTPError, action: str, error_type: str) -> AppError:
    details = exc.read().decode("utf-8", errors="ignore")
    if exc.code in {401, 403}:
        return AppError(
            (
                "ElevenLabs received WatchLess' request, but rejected this API key. "
                "Create or copy a fresh key from the same ElevenLabs workspace, make sure the key is not restricted away from voices/text-to-speech, then paste only the key text."
            ),
            "elevenlabs_invalid_api_key",
            401,
        )
    if exc.code == 429:
        return AppError(
            "ElevenLabs says this account has hit its usage limit or rate limit. Try again later or check your ElevenLabs plan.",
            "elevenlabs_rate_limited",
            429,
        )
    return AppError(f"{action}: {details or exc.reason}", error_type, exc.code)


def _elevenlabs_connection_error(exc: URLError, action: str, error_type: str) -> AppError:
    details = str(getattr(exc, "reason", exc))
    if "CERTIFICATE_VERIFY_FAILED" in details or "certificate verify failed" in details.lower():
        return AppError(f"{ELEVENLABS_CERTIFICATE_MESSAGE} Exact issue: {details}", "elevenlabs_certificate_error", 502)
    return AppError(f"{action}: {details}", error_type, 502)


def _elevenlabs_narration_request(text: str, voice_id: str = "", api_key: str = "", stream: bool = False) -> Request:
    api_key = _elevenlabs_api_key(api_key)
    voice_id = voice_id.strip() or os.environ.get("WATCHLESS_ANIME_VOICE_ID", "").strip()
    model_id = os.environ.get("WATCHLESS_TTS_MODEL", "eleven_multilingual_v2").strip()
    if not voice_id:
        raise AppError(
            "Choose or upload an anime voice first.",
            "anime_voice_missing_voice_id",
            400,
        )
    if not text:
        raise AppError("There is nothing to narrate yet.", "missing_narration_text", 400)
    if len(text) > 5000:
        text = text[:5000]

    payload = json.dumps({
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.35,
            "similarity_boost": 0.75,
            "style": 0.35,
            "use_speaker_boost": True,
        },
    }).encode("utf-8")
    path = f"text-to-speech/{voice_id}{'/stream' if stream else ''}"
    return Request(
        f"https://api.elevenlabs.io/v1/{path}",
        data=payload,
        headers={
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key,
        },
        method="POST",
    )


def _elevenlabs_narration(text: str, voice_id: str = "", api_key: str = "") -> bytes:
    req = _elevenlabs_narration_request(text, voice_id, api_key)
    try:
        with urlopen(req, timeout=45, context=_elevenlabs_ssl_context()) as response:
            return response.read()
    except HTTPError as exc:
        raise _elevenlabs_json_error(exc, "Anime voice request failed", "anime_voice_request_failed")
    except URLError as exc:
        raise _elevenlabs_connection_error(exc, "Could not reach the anime voice service", "anime_voice_connection_failed")


def _elevenlabs_voices(api_key: str = "") -> list[dict]:
    api_key = _elevenlabs_api_key(api_key)
    query = urlencode({"page_size": "100"})
    req = Request(
        f"{ELEVENLABS_VOICES_URL}?{query}",
        headers={
            "Accept": "application/json",
            "xi-api-key": api_key,
        },
        method="GET",
    )
    try:
        with urlopen(req, timeout=30, context=_elevenlabs_ssl_context()) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise _elevenlabs_json_error(exc, "Could not load ElevenLabs voices", "elevenlabs_voice_list_failed")
    except URLError as exc:
        raise _elevenlabs_connection_error(exc, "Could not reach ElevenLabs", "elevenlabs_connection_failed")

    voices = payload.get("voices", []) if isinstance(payload, dict) else []
    return [
        {
            "voice_id": voice.get("voice_id", ""),
            "name": voice.get("name", "ElevenLabs voice"),
            "category": voice.get("category", ""),
            "description": voice.get("description", ""),
            "labels": voice.get("labels", {}),
            "created_at_unix": voice.get("created_at_unix") or voice.get("date_unix") or voice.get("created_at") or 0,
            "is_owner": bool(voice.get("is_owner")),
        }
        for voice in voices
        if isinstance(voice, dict) and voice.get("voice_id")
    ]


def _multipart_body(fields: dict[str, str], files: list[tuple[str, str, bytes, str]]) -> tuple[bytes, str]:
    boundary = f"----WatchLess{token_hex(16)}"
    chunks = []
    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        chunks.append(str(value).encode("utf-8"))
        chunks.append(b"\r\n")
    for field_name, filename, data, content_type in files:
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(
            f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode("utf-8")
        )
        chunks.append(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        chunks.append(data)
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), boundary


def _voice_file_extension(filename: str) -> str:
    return Path(filename or "").suffix.lower()


def _normalize_local_voice_server_url(server_url: str = "") -> str:
    cleaned = (server_url or "").strip() or LOCAL_VOICE_DEFAULT_SERVER
    return cleaned.rstrip("/")


def _local_voice_connection_message(server_url: str) -> str:
    normalized = _normalize_local_voice_server_url(server_url)
    return (
        f"Could not reach the local voice server at {normalized}. "
        "Start it from the WatchLess folder with ./run-dev.sh voice, then test the connection again."
    )


def _local_voice_error_details(raw_details: str) -> str:
    details = (raw_details or "").strip()
    if not details:
        return ""
    try:
        payload = json.loads(details)
    except Exception:
        return details
    if isinstance(payload, dict):
        if isinstance(payload.get("error"), str) and payload.get("error").strip():
            return payload["error"].strip()
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()
        if isinstance(detail, list) and detail:
            first = detail[0]
            if isinstance(first, dict):
                loc = first.get("loc") or []
                location = ".".join(str(part) for part in loc if part not in {"query", "body"}) or "request"
                message = str(first.get("msg") or "Request validation failed.").strip()
                return f"{location}: {message}" if location else message
            return str(first).strip()
    return details


def _local_voice_http_error(server_url: str, path: str, exc: HTTPError, fallback_type: str) -> AppError:
    details = _local_voice_error_details(exc.read().decode("utf-8", errors="ignore"))
    if exc.code == 404:
        return AppError(
            (
                f"WatchLess reached {_normalize_local_voice_server_url(server_url)}, but that server does not expose {path}. "
                "It is probably the wrong server or the local voice server is not running. "
                "Start it from the WatchLess folder with ./run-dev.sh voice."
            ),
            "local_voice_wrong_server",
            502,
        )
    if exc.code in {400, 422} and details:
        return AppError(f"Local voice request needs attention: {details}", "local_voice_invalid_request", 400)
    return AppError(f"Local voice server error: {details or exc.reason}", fallback_type, exc.code)


def _local_voice_request(server_url: str, path: str, method: str = "GET", data: bytes | None = None, headers: dict | None = None) -> Request:
    return Request(
        f"{_normalize_local_voice_server_url(server_url)}{path}",
        data=data,
        headers=headers or {},
        method=method,
    )


def _local_voice_json(server_url: str, path: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = _local_voice_request(server_url, path, method=method, data=data, headers=headers)
    try:
        with urlopen(req, timeout=60) as response:
            raw = response.read().decode("utf-8")
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                raise AppError(
                    (
                        f"WatchLess reached {_normalize_local_voice_server_url(server_url)}, but {path} did not return JSON. "
                        "This usually means the URL points to the wrong local server. "
                        "Start the WatchLess local voice server with ./run-dev.sh voice."
                    ),
                    "local_voice_wrong_server",
                    502,
                )
    except HTTPError as exc:
        raise _local_voice_http_error(server_url, path, exc, "local_voice_server_error")
    except URLError as exc:
        raise AppError(_local_voice_connection_message(server_url), "local_voice_connection_failed", 502)


def _local_voice_audio(server_url: str, payload: dict) -> bytes:
    query = urlencode(payload)
    req = _local_voice_request(server_url, f"/voice?{query}", method="POST")
    try:
        with urlopen(req, timeout=300) as response:
            return response.read()
    except HTTPError as exc:
        raise _local_voice_http_error(server_url, "/voice", exc, "local_voice_request_failed")
    except URLError as exc:
        raise AppError(_local_voice_connection_message(server_url), "local_voice_connection_failed", 502)


def _local_voice_catalog() -> list[dict]:
    return [
        {
            **item,
            "source_url": f"{LOCAL_VOICE_SPACE_RESOLVE_ROOT}/{quote(item['folder'])}",
            "license_note": "Check the Hugging Face Space and character/voice rights before product use.",
        }
        for item in LOCAL_VOICE_MODELS
    ]


def _local_voice_config_payload(info: dict) -> dict:
    config_path = Path(str(info.get("config_path") or ""))
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _local_voice_language_meta(model_name: str, info: dict) -> tuple[str, list[str]]:
    normalized = (model_name or "").lower()
    catalog_item = next((item for item in LOCAL_VOICE_MODELS if item["folder"].lower() == normalized), None)
    if catalog_item:
        return catalog_item["primary_language"], catalog_item.get("languages") or [catalog_item["primary_language"]]
    config = _local_voice_config_payload(info)
    data = config.get("data") or {}
    use_jp_extra = info.get("use_jp_extra")
    if use_jp_extra is None:
        use_jp_extra = data.get("use_jp_extra")
    if use_jp_extra is True or normalized.endswith("-jp") or "jvnv" in normalized:
        return "JP", ["JP"]
    if "holoesl" in normalized or "idflu" in normalized:
        return "ESL", ["EN", "ID"]
    if "jp" in normalized or "pekora" in normalized:
        return "JP", ["JP"]
    return "Unknown", []


def _local_voice_model_summary(server_url: str, refresh: bool = False) -> dict:
    if refresh:
        _local_voice_json(server_url, "/models/refresh", method="POST", payload={})
    models_info = _local_voice_json(server_url, "/models/info")
    status_payload = _local_voice_json(server_url, "/status")
    models = []
    for model_id, info in sorted(models_info.items(), key=lambda item: int(item[0])):
        config_path = Path(str(info.get("config_path") or ""))
        model_path = Path(str(info.get("model_path") or ""))
        model_name = config_path.parent.name or model_path.stem or f"Model {model_id}"
        primary_language, languages = _local_voice_language_meta(model_name, info)
        styles = list((info.get("style2id") or {}).keys())
        speakers = [
            {"id": value, "name": key}
            for key, value in sorted((info.get("spk2id") or {}).items(), key=lambda item: item[1])
        ]
        models.append(
            {
                "id": int(model_id),
                "name": model_name,
                "config_path": str(config_path),
                "model_path": str(model_path),
                "primary_language": primary_language,
                "languages": languages,
                "language_note": "English-capable" if "EN" in languages else "Japanese-only. Not usable for English narration.",
                "styles": styles,
                "speakers": speakers,
                "device": info.get("device") or "cpu",
            }
        )
    return {
        "server_url": _normalize_local_voice_server_url(server_url),
        "models": models,
        "status": status_payload,
    }


def _local_voice_model_summary_with_autostart(server_url: str, refresh: bool = False) -> dict:
    try:
        return _local_voice_model_summary(server_url, refresh=refresh)
    except AppError as exc:
        if exc.error_type != "local_voice_connection_failed":
            raise
        runner = LocalVoiceRunner(_normalize_local_voice_server_url(server_url))
        if runner.ensure_started():
            return _local_voice_model_summary(server_url, refresh=refresh)
        raise AppError(
            (
                f"{exc.message} WatchLess also tried to start the local voice server automatically. "
                f"{runner.last_error}"
            ),
            "local_voice_autostart_failed",
            502,
        )


def _download_local_voice_model(folder: str, assets_root: str, files: list[str]) -> list[str]:
    root = Path(assets_root).expanduser()
    if not root.name:
        raise AppError("Choose a valid local model folder first.", "local_voice_invalid_assets_root", 400)
    root.mkdir(parents=True, exist_ok=True)
    model_dir = root / folder
    model_dir.mkdir(parents=True, exist_ok=True)
    downloaded = []
    for filename in files:
        url = f"{LOCAL_VOICE_SPACE_RESOLVE_ROOT}/{quote(folder)}/{quote(filename)}"
        destination = model_dir / filename
        with urlopen(url, timeout=120, context=_trusted_ssl_context()) as response, destination.open("wb") as target:
            target.write(response.read())
        downloaded.append(str(destination))
    return downloaded


def _validate_voice_file(uploaded_file) -> tuple[str, str]:
    filename = uploaded_file.filename or ""
    extension = _voice_file_extension(filename)
    guessed_type = mimetypes.guess_type(filename)[0] or ""
    content_type = uploaded_file.mimetype or guessed_type
    if extension not in ALLOWED_VOICE_EXTENSIONS:
        raise AppError(VOICE_FILE_TYPE_MESSAGE, "unsupported_voice_file_type", 400)
    if content_type and content_type != "application/octet-stream" and content_type not in ALLOWED_VOICE_MIME_TYPES:
        raise AppError(VOICE_FILE_TYPE_MESSAGE, "unsupported_voice_file_type", 400)
    return filename, content_type or "application/octet-stream"


def _create_elevenlabs_voice(uploaded_file, voice_name: str, api_key: str = "") -> dict:
    api_key = _elevenlabs_api_key(api_key)
    filename, content_type = _validate_voice_file(uploaded_file)
    data = uploaded_file.read()
    if not data:
        raise AppError("Choose an audio file first.", "missing_voice_sample", 400)
    if len(data) > 25 * 1024 * 1024:
        raise AppError("Voice sample is too large. Use an audio file under 25 MB.", "voice_sample_too_large", 400)

    body, boundary = _multipart_body(
        {
            "name": voice_name or "WatchLess Anime Voice",
            "description": "User-provided WatchLess narration voice.",
            "remove_background_noise": "true",
        },
        [("files[]", filename, data, content_type)],
    )
    req = Request(
        "https://api.elevenlabs.io/v1/voices/add",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "xi-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=60, context=_elevenlabs_ssl_context()) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise _elevenlabs_json_error(exc, "Could not create anime voice", "anime_voice_upload_failed")
    except URLError as exc:
        raise _elevenlabs_connection_error(exc, "Could not reach the anime voice service", "anime_voice_connection_failed")


@api_bp.route("/health")
def health():
    return jsonify({"ok": True})


@api_bp.route("/narration/anime", methods=["POST"])
def anime_narration():
    try:
        payload = request.json or {}
        audio = _elevenlabs_narration(
            (payload.get("text") or "").strip(),
            payload.get("voice_id") or "",
            payload.get("api_key") or "",
        )
        return Response(audio, content_type="audio/mpeg")
    except Exception as exc:
        return _json_error(exc)


@api_bp.route("/narration/anime/stream", methods=["POST"])
def anime_narration_stream():
    try:
        payload = request.json or {}
        req = _elevenlabs_narration_request(
            (payload.get("text") or "").strip(),
            payload.get("voice_id") or "",
            payload.get("api_key") or "",
            stream=True,
        )
        upstream = urlopen(req, timeout=45, context=_elevenlabs_ssl_context())
    except HTTPError as exc:
        return _json_error(_elevenlabs_json_error(exc, "Anime voice request failed", "anime_voice_request_failed"))
    except URLError as exc:
        return _json_error(_elevenlabs_connection_error(exc, "Could not reach the anime voice service", "anime_voice_connection_failed"))
    except Exception as exc:
        return _json_error(exc)

    def generate():
        try:
            while True:
                chunk = upstream.read(16384)
                if not chunk:
                    break
                yield chunk
        finally:
            upstream.close()

    return Response(stream_with_context(generate()), content_type="audio/mpeg")


@api_bp.route("/narration/elevenlabs/voices", methods=["POST"])
def elevenlabs_voices():
    try:
        payload = request.json or {}
        return jsonify({"ok": True, "voices": _elevenlabs_voices(payload.get("api_key") or "")})
    except Exception as exc:
        return _json_error(exc)


@api_bp.route("/narration/anime/voice", methods=["POST"])
def upload_anime_voice():
    uploaded_file = request.files.get("file")
    if not uploaded_file:
        return _json_error(AppError("Choose an audio file first.", "missing_voice_sample", 400))
    try:
        voice = _create_elevenlabs_voice(
            uploaded_file,
            (request.form.get("name") or "").strip(),
            request.form.get("api_key") or "",
        )
        return jsonify({"ok": True, "voice_id": voice.get("voice_id", ""), "requires_verification": bool(voice.get("requires_verification"))})
    except Exception as exc:
        return _json_error(exc)


@api_bp.route("/narration/local/catalog")
def local_voice_catalog():
    return jsonify({"ok": True, "models": _local_voice_catalog()})


@api_bp.route("/narration/local/status", methods=["GET", "POST"])
def local_voice_status():
    try:
        payload = request.json if request.method == "POST" else {}
        payload = payload or {}
        assets_root = (payload.get("assets_root") or "").strip()
        if assets_root:
            os.environ["WATCHLESS_LOCAL_VOICE_ASSETS_ROOT"] = assets_root
            repo_root = Path(assets_root).expanduser().parent
            if (repo_root / ".venv" / "bin" / "python").exists():
                os.environ["WATCHLESS_LOCAL_VOICE_REPO"] = str(repo_root)
        return jsonify({
            "ok": True,
            "server": _local_voice_model_summary_with_autostart(
                payload.get("server_url") or "",
                refresh=bool(payload.get("refresh")),
            ),
        })
    except Exception as exc:
        return _json_error(exc)


@api_bp.route("/narration/local/download", methods=["POST"])
def local_voice_download():
    try:
        payload = request.json or {}
        model_id = (payload.get("model_id") or "").strip()
        assets_root = (payload.get("assets_root") or "").strip()
        model = next((item for item in LOCAL_VOICE_MODELS if item["id"] == model_id), None)
        if not model:
            raise AppError("Choose a supported local voice model first.", "local_voice_unknown_model", 400)
        if not assets_root:
            raise AppError("Choose the local model folder on your Mac first.", "local_voice_missing_assets_root", 400)
        downloaded = _download_local_voice_model(model["folder"], assets_root, model["files"])
        server_summary = None
        if payload.get("server_url"):
            try:
                server_summary = _local_voice_model_summary(payload.get("server_url") or "", refresh=True)
            except Exception:
                server_summary = None
        return jsonify({"ok": True, "downloaded": downloaded, "server": server_summary, "model": model})
    except Exception as exc:
        return _json_error(exc)


@api_bp.route("/narration/local", methods=["POST"])
def local_voice_narration():
    try:
        payload = request.json or {}
        text = (payload.get("text") or "").strip()
        if not text:
            raise AppError("There is nothing to narrate yet.", "missing_narration_text", 400)
        audio = _local_voice_audio(
            payload.get("server_url") or "",
            {
                "text": text[:5000],
                "model_name": payload.get("model_name") or "",
                "speaker_name": payload.get("speaker_name") or "",
                "style": payload.get("style") or "Neutral",
                "language": (payload.get("language") or "EN").upper(),
                "length": payload.get("length") or 1,
                "auto_split": "true",
            },
        )
        return Response(audio, content_type="audio/wav")
    except Exception as exc:
        return _json_error(exc)


@api_bp.route("/models")
def models():
    return jsonify(current_app.services["lm_studio"].model_inventory())


@api_bp.route("/settings")
def settings():
    return jsonify({"ok": True, "settings": current_app.services["settings_store"].load()})


@api_bp.route("/settings/lm-studio-port", methods=["POST"])
def update_lm_studio_port():
    try:
        payload = request.json or {}
        settings_store = current_app.services["settings_store"]
        settings = settings_store.save_lm_studio_port(payload.get("port"))
        if payload.get("provider"):
            settings = settings_store.save_provider(payload.get("provider"))
        return jsonify({"ok": True, "settings": settings, "models": current_app.services["lm_studio"].test_connection()})
    except Exception as exc:
        return _json_error(exc)


@api_bp.route("/settings/test-lm-studio", methods=["POST"])
def test_lm_studio_connection():
    try:
        payload = request.json or {}
        settings_store = current_app.services["settings_store"]
        if payload.get("port"):
            settings_store.save_lm_studio_port(payload.get("port"))
        if payload.get("provider"):
            settings_store.save_provider(payload.get("provider"))
        return jsonify({"ok": True, "models": current_app.services["lm_studio"].test_connection()})
    except Exception as exc:
        return _json_error(exc)


@api_bp.route("/models/load", methods=["POST"])
def load_model():
    try:
        payload = request.json or {}
        result = current_app.services["lm_studio"].load_model(payload.get("model", ""))
        return jsonify({"ok": True, "result": result, "models": current_app.services["lm_studio"].model_inventory()})
    except Exception as exc:
        return _json_error(exc)


@api_bp.route("/models/unload", methods=["POST"])
def unload_model():
    try:
        payload = request.json or {}
        result = current_app.services["lm_studio"].unload_model(payload.get("instance_id") or payload.get("model", ""))
        return jsonify({"ok": True, "result": result, "models": current_app.services["lm_studio"].model_inventory()})
    except Exception as exc:
        return _json_error(exc)


@api_bp.route("/prompt")
def get_prompt():
    prompt, is_default = current_app.services["prompt_store"].load()
    return jsonify({"ok": True, "prompt": prompt, "is_default": is_default})


@api_bp.route("/prompt", methods=["POST"])
def set_prompt():
    try:
        payload = request.json or {}
        prompt = current_app.services["prompt_store"].save(payload.get("prompt", ""), payload.get("preset_id", ""))
        return jsonify({"ok": True, "prompt": prompt, "is_default": False})
    except Exception as exc:
        return _json_error(AppError(f"Could not save prompt preset: {exc}", "prompt_save_error", 400))


@api_bp.route("/prompt/reset", methods=["POST"])
def reset_prompt():
    try:
        prompt = current_app.services["prompt_store"].reset()
        return jsonify({"ok": True, "prompt": prompt, "is_default": True})
    except Exception as exc:
        return _json_error(AppError(f"Could not reset prompt preset: {exc}", "prompt_reset_error", 500))


@api_bp.route("/prompt/presets")
def prompt_presets():
    presets = current_app.services["prompt_store"].list_presets()
    return jsonify({"ok": True, "presets": presets})


@api_bp.route("/prompt/presets", methods=["POST"])
def save_prompt_preset():
    try:
        payload = request.json or {}
        preset = current_app.services["prompt_store"].save_preset(
            payload.get("name", ""),
            payload.get("prompt", ""),
        )
        return jsonify({"ok": True, "preset": preset})
    except Exception as exc:
        return _json_error(AppError(f"Could not save prompt preset: {exc}", "prompt_preset_save_error", 400))


@api_bp.route("/prompt/presets/<preset_id>")
def get_prompt_preset(preset_id):
    try:
        preset = current_app.services["prompt_store"].get_preset(preset_id)
        return jsonify({"ok": True, "preset": preset})
    except FileNotFoundError:
        return jsonify({"ok": False, "error": "Prompt preset not found.", "error_type": "not_found"}), 404
    except Exception as exc:
        return _json_error(exc)


@api_bp.route("/prompt/presets/<preset_id>", methods=["PUT"])
def rename_prompt_preset(preset_id):
    try:
        payload = request.json or {}
        preset = current_app.services["prompt_store"].rename_preset(preset_id, payload.get("name", ""))
        return jsonify({"ok": True, "preset": preset})
    except FileNotFoundError:
        return jsonify({"ok": False, "error": "Prompt preset not found.", "error_type": "not_found"}), 404
    except Exception as exc:
        return _json_error(AppError(f"Could not rename prompt preset: {exc}", "prompt_preset_rename_error", 400))


@api_bp.route("/prompt/presets/<preset_id>/rename", methods=["POST"])
def rename_prompt_preset_post(preset_id):
    return rename_prompt_preset(preset_id)


@api_bp.route("/prompt/presets/<preset_id>", methods=["DELETE"])
def delete_prompt_preset(preset_id):
    try:
        current_app.services["prompt_store"].delete_preset(preset_id)
        return jsonify({"ok": True})
    except FileNotFoundError:
        return jsonify({"ok": False, "error": "Prompt preset not found.", "error_type": "not_found"}), 404
    except Exception as exc:
        return _json_error(AppError(f"Could not delete prompt preset: {exc}", "prompt_preset_delete_error", 400))


@api_bp.route("/prompt/presets/<preset_id>/delete", methods=["POST"])
def delete_prompt_preset_post(preset_id):
    return delete_prompt_preset(preset_id)


@api_bp.route("/videos/metadata", methods=["POST"])
def video_metadata():
    payload = request.json or {}
    raw_urls = payload.get("urls", [])
    if isinstance(raw_urls, str):
        raw_urls = [raw_urls]
    urls = [url.strip() for url in raw_urls if isinstance(url, str) and url.strip()]
    items = []
    for url in urls:
        try:
            items.append(current_app.services["transcript_service"].fetch_metadata(url))
        except Exception:
            items.append({"url": url, "title": "New Summary"})
    return jsonify({"ok": True, "items": items})


@api_bp.route("/chat", methods=["POST"])
def chat():
    try:
        payload = request.json or {}
        question = payload.get("question", "")
        answer = current_app.services["lm_studio"].chat(
            summary=payload.get("summary", ""),
            question=question,
            model=payload.get("model", ""),
        )
        history_id = payload.get("history_id", "")
        messages = current_app.services["chat_store"].append_pair(history_id, question, answer) if history_id else []
        return jsonify({"ok": True, "answer": answer, "messages": messages})
    except Exception as exc:
        return _json_error(exc)


@api_bp.route("/chat/history/<history_id>")
def chat_history(history_id):
    messages = current_app.services["chat_store"].load(history_id)
    return jsonify({"ok": True, "messages": messages})


@api_bp.route("/files/ingest", methods=["POST"])
def ingest_file():
    uploaded_file = request.files.get("file")
    if not uploaded_file:
        return _json_error(AppError("Choose a file first.", "missing_file", 400))
    try:
        return jsonify({"ok": True, "file": current_app.services["file_ingestion"].extract_text(uploaded_file)})
    except Exception as exc:
        return _json_error(exc)


@api_bp.route("/feedback/email", methods=["POST"])
def open_feedback_email():
    payload = request.json or {}
    body = (payload.get("body") or "").strip() or "I want to share feedback about WatchLess."
    subject = (payload.get("subject") or "WatchLess Feedback").strip()
    mailto = f"mailto:{FEEDBACK_EMAIL}?subject={quote(subject)}&body={quote(body)}"
    try:
        opened = _open_external_url(mailto)
    except Exception as exc:
        return _json_error(AppError(f"Could not open your default email app: {exc}", "email_open_error", 500))
    return jsonify({"ok": True, "opened": bool(opened), "email": FEEDBACK_EMAIL, "mailto": mailto})


@api_bp.route("/support/donation", methods=["POST"])
def open_donation():
    if not DONATION_URL:
        return _json_error(AppError("Donation link is not configured.", "donation_link_missing", 400))
    try:
        opened = _open_external_url(DONATION_URL)
    except Exception as exc:
        return _json_error(AppError(f"Could not open Ko-fi: {exc}", "donation_open_error", 500))
    return jsonify({"ok": True, "opened": bool(opened), "url": DONATION_URL})


@api_bp.route("/chat/stream", methods=["POST"])
def chat_stream():
    payload = request.json or {}
    question = payload.get("question", "")
    history_id = payload.get("history_id", "")

    def generate():
        answer_parts = []
        try:
            for chunk in current_app.services["lm_studio"].stream_chat(
                summary=payload.get("summary", ""),
                question=question,
                model=payload.get("model", ""),
            ):
                answer_parts.append(chunk)
                yield f"data: {json.dumps({'delta': chunk}, ensure_ascii=False)}\n\n"
            answer = "".join(answer_parts)
            messages = current_app.services["chat_store"].append_pair(history_id, question, answer) if history_id else []
            yield f"data: {json.dumps({'done': True, 'answer': answer, 'messages': messages}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            message = exc.message if isinstance(exc, AppError) else str(exc)
            yield f"data: {json.dumps({'error': message}, ensure_ascii=False)}\n\n"

    return Response(stream_with_context(generate()), content_type="text/event-stream; charset=utf-8")


@api_bp.route("/jobs", methods=["POST"])
def create_jobs():
    payload = request.json or {}
    raw_urls = payload.get("urls")
    if raw_urls is None:
        raw_urls = [payload.get("url", "")]
    if isinstance(raw_urls, str):
        raw_urls = [raw_urls]

    urls = [url.strip() for url in raw_urls if isinstance(url, str) and url.strip()]
    model = payload.get("model", "")
    title_map = payload.get("titles", {}) if isinstance(payload.get("titles", {}), dict) else {}
    if not urls:
        return _json_error(AppError("Paste at least one YouTube URL first.", "missing_url", 400))
    try:
        jobs = [current_app.services["job_queue"].submit(url, model, title_map.get(url, "")) for url in urls]
        return jsonify({"ok": True, "jobs": [serialize_job(job) for job in jobs]})
    except Exception as exc:
        return _json_error(exc)


@api_bp.route("/jobs")
def list_jobs():
    jobs = current_app.services["job_queue"].list()
    return jsonify({"ok": True, "jobs": [serialize_job(job) for job in jobs]})


@api_bp.route("/jobs/<job_id>")
def get_job(job_id):
    job = current_app.services["job_queue"].get(job_id)
    if not job:
        return jsonify({"ok": False, "error": "Job not found.", "error_type": "not_found"}), 404
    return jsonify({"ok": True, "job": serialize_job(job)})


@api_bp.route("/history")
def history():
    items = current_app.services["history_store"].list()
    return jsonify({"ok": True, "items": items})


@api_bp.route("/history/<history_id>")
def history_item(history_id):
    try:
        item = current_app.services["history_store"].get(history_id)
        return jsonify({"ok": True, "item": item})
    except FileNotFoundError:
        return jsonify({"ok": False, "error": "History item not found.", "error_type": "not_found"}), 404
    except Exception as exc:
        return _json_error(exc)


# Backward-compatible aliases for the previous single-file UI.
@legacy_bp.route("/models")
def legacy_models():
    return models()


@legacy_bp.route("/prompt")
def legacy_get_prompt():
    return get_prompt()


@legacy_bp.route("/prompt", methods=["POST"])
def legacy_set_prompt():
    return set_prompt()


@legacy_bp.route("/prompt/reset", methods=["POST"])
def legacy_reset_prompt():
    return reset_prompt()
