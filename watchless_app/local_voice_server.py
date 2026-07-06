from __future__ import annotations

import argparse
import json
import socket
import sys
import threading
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen


CPU_ONNX_PROVIDERS = [("CPUExecutionProvider", {"arena_extend_strategy": "kSameAsRequested"})]


def existing_server_status_url(host: str, port: int) -> str:
    return f"http://{host}:{port}/status"


def existing_compatible_server(host: str, port: int) -> bool:
    try:
        with urlopen(existing_server_status_url(host, port), timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload.get("service") == "watchless-local-voice" and bool(payload.get("ok"))
    except Exception:
        return False


class LocalVoiceServerError(Exception):
    def __init__(self, message: str, error_type: str = "local_voice_server_error", status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.status_code = status_code


class LocalVoiceRuntime:
    def __init__(self, style_bert_dir: Path, assets_root: Path, device: str = "cpu"):
        self.style_bert_dir = style_bert_dir.expanduser().resolve()
        self.assets_root = assets_root.expanduser().resolve()
        self.device = device
        self.current_model_name: str | None = None
        self.current_model_path: str | None = None
        self.inference_lock = threading.Lock()
        self._bootstrap()
        self.refresh()

    def _bootstrap(self) -> None:
        if not self.style_bert_dir.exists():
            raise LocalVoiceServerError(
                f"Style-Bert repo was not found at {self.style_bert_dir}.",
                "local_voice_missing_repo",
                500,
            )
        if str(self.style_bert_dir) not in sys.path:
            sys.path.insert(0, str(self.style_bert_dir))
        try:
            from style_bert_vits2.constants import Languages
            from style_bert_vits2.tts_model import TTSModelHolder
        except Exception as exc:  # pragma: no cover - startup failure path
            raise LocalVoiceServerError(
                (
                    "Could not import Style-Bert-VITS2. "
                    "Make sure you start this server with the Style-Bert virtual environment."
                ),
                "local_voice_import_failed",
                500,
            ) from exc
        self.Languages = Languages
        self.TTSModelHolder = TTSModelHolder

    def refresh(self) -> None:
        if not self.assets_root.exists():
            raise LocalVoiceServerError(
                f"Model assets folder was not found at {self.assets_root}.",
                "local_voice_missing_assets_root",
                500,
            )
        self.model_holder = self.TTSModelHolder(
            self.assets_root,
            self.device,
            CPU_ONNX_PROVIDERS,
            ignore_onnx=True,
        )
        self.current_model_name = None
        self.current_model_path = None

    def _config_payload(self, model_name: str) -> dict:
        config_path = self.assets_root / model_name / "config.json"
        return json.loads(config_path.read_text(encoding="utf-8"))

    def models_info(self) -> dict[str, dict]:
        info: dict[str, dict] = {}
        for index, model_name in enumerate(self.model_holder.model_names):
            config = self._config_payload(model_name)
            data = config.get("data", {})
            model_path = self.model_holder.model_files_dict[model_name][0]
            info[str(index)] = {
                "config_path": str(self.assets_root / model_name / "config.json"),
                "model_path": str(model_path),
                "device": self.device,
                "model_name": config.get("model_name") or model_name,
                "use_jp_extra": data.get("use_jp_extra"),
                "spk2id": data.get("spk2id") or {},
                "style2id": data.get("style2id") or {},
            }
        return info

    def status(self) -> dict:
        return {
            "ok": True,
            "service": "watchless-local-voice",
            "device": self.device,
            "style_bert_dir": str(self.style_bert_dir),
            "assets_root": str(self.assets_root),
            "model_count": len(self.model_holder.model_names),
            "current_model_name": self.current_model_name,
            "current_model_path": self.current_model_path,
        }

    def _resolve_model_name(self, model_name: str = "", model_id: str = "") -> str:
        names = self.model_holder.model_names
        if not names:
            raise LocalVoiceServerError(
                f"No local voice models were found in {self.assets_root}.",
                "local_voice_no_models",
                404,
            )
        if model_name:
            if model_name not in names:
                raise LocalVoiceServerError(
                    f"Model '{model_name}' was not found in {self.assets_root}.",
                    "local_voice_model_not_found",
                    400,
                )
            return model_name
        if model_id:
            try:
                index = int(model_id)
            except ValueError as exc:
                raise LocalVoiceServerError("model_id must be a number.", "local_voice_invalid_model_id", 400) from exc
            if index < 0 or index >= len(names):
                raise LocalVoiceServerError(
                    f"model_id {index} is out of range.",
                    "local_voice_invalid_model_id",
                    400,
                )
            return names[index]
        return names[0]

    @staticmethod
    def _parse_bool(value: str | None, default: bool = True) -> bool:
        if value is None or value == "":
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    def synthesize(self, payload: dict[str, str]) -> tuple[bytes, str]:
        text = (payload.get("text") or "").strip()
        if not text:
            raise LocalVoiceServerError("Text is required.", "missing_narration_text", 400)
        if len(text) > 5000:
            raise LocalVoiceServerError(
                "Text is too long for one local narration request. Keep it under 5000 characters.",
                "local_voice_text_too_long",
                400,
            )

        model_name = self._resolve_model_name(payload.get("model_name", ""), payload.get("model_id", ""))
        model_path = str(self.model_holder.model_files_dict[model_name][0])
        model = self.model_holder.get_model(model_name, model_path)
        self.current_model_name = model_name
        self.current_model_path = model_path

        speaker_name = (payload.get("speaker_name") or "").strip()
        if speaker_name:
            if speaker_name not in model.spk2id:
                raise LocalVoiceServerError(
                    f"Speaker '{speaker_name}' was not found in model '{model_name}'.",
                    "local_voice_speaker_not_found",
                    400,
                )
            speaker_id = model.spk2id[speaker_name]
        else:
            speaker_id = next(iter(model.id2spk.keys()), 0)

        style = (payload.get("style") or "").strip() or next(iter(model.style2id.keys()), "Neutral")
        if style not in model.style2id:
            raise LocalVoiceServerError(
                f"Style '{style}' was not found in model '{model_name}'.",
                "local_voice_style_not_found",
                400,
            )

        language_name = (payload.get("language") or "EN").upper()
        if not hasattr(self.Languages, language_name):
            raise LocalVoiceServerError(
                f"Language '{language_name}' is not supported. Use EN, JP, or ZH.",
                "local_voice_language_not_supported",
                400,
            )
        config = self._config_payload(model_name)
        if (config.get("data") or {}).get("use_jp_extra") is True and language_name != "JP":
            raise LocalVoiceServerError(
                (
                    f"Model '{model_name}' is JP-Extra, so it only accepts JP narration requests. "
                    "Choose an English-capable model for English summaries."
                ),
                "local_voice_language_incompatible",
                400,
            )
        language = getattr(self.Languages, language_name)

        try:
            length = float(payload.get("length") or 1.0)
        except ValueError as exc:
            raise LocalVoiceServerError("length must be a number.", "local_voice_invalid_length", 400) from exc

        with self.inference_lock:
            sample_rate, audio = model.infer(
                text=text,
                language=language,
                speaker_id=speaker_id,
                style=style,
                length=length,
                line_split=self._parse_bool(payload.get("auto_split"), default=True),
            )
        with BytesIO() as buffer:
            with wave.open(buffer, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio.tobytes())
            return buffer.getvalue(), model_name


class LocalVoiceRequestHandler(BaseHTTPRequestHandler):
    runtime: LocalVoiceRuntime
    server_version = "WatchLessLocalVoice/1.0"

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._send_common_headers()
        self.end_headers()

    def do_GET(self) -> None:
        self._dispatch()

    def do_POST(self) -> None:
        self._dispatch()

    def log_message(self, format: str, *args) -> None:  # pragma: no cover - console only
        return

    def _send_common_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _send_json(self, status_code: int, payload: dict) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self._send_common_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_audio(self, payload: bytes) -> None:
        self.send_response(200)
        self._send_common_headers()
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _read_json_body(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise LocalVoiceServerError("Request body must be valid JSON.", "local_voice_invalid_json", 400) from exc
        if not isinstance(payload, dict):
            raise LocalVoiceServerError("JSON body must be an object.", "local_voice_invalid_json", 400)
        return {str(key): "" if value is None else str(value) for key, value in payload.items()}

    @staticmethod
    def _query_payload(parsed) -> dict[str, str]:
        return {key: values[-1] for key, values in parse_qs(parsed.query, keep_blank_values=True).items()}

    def _dispatch(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path in {"", "/"}:
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "service": "watchless-local-voice",
                        "message": "Use /status, /models/info, /models/refresh, or /voice.",
                    },
                )
                return
            if parsed.path == "/health":
                self._send_json(200, self.runtime.status())
                return
            if parsed.path == "/status":
                self._send_json(200, self.runtime.status())
                return
            if parsed.path == "/models/info":
                self._send_json(200, self.runtime.models_info())
                return
            if parsed.path == "/models/refresh":
                if self.command != "POST":
                    raise LocalVoiceServerError("Use POST for /models/refresh.", "method_not_allowed", 405)
                self.runtime.refresh()
                self._send_json(200, self.runtime.models_info())
                return
            if parsed.path == "/voice":
                payload = self._query_payload(parsed)
                if self.command == "POST":
                    payload = {**self._read_json_body(), **payload}
                audio, model_name = self.runtime.synthesize(payload)
                print(f"[local-voice] generated narration with {model_name}", flush=True)
                self._send_audio(audio)
                return
            raise LocalVoiceServerError(
                f"Route '{parsed.path}' was not found.",
                "not_found",
                404,
            )
        except LocalVoiceServerError as exc:
            self._send_json(exc.status_code, {"ok": False, "error": exc.message, "error_type": exc.error_type})
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._send_json(500, {"ok": False, "error": str(exc), "error_type": "local_voice_server_error"})


def main() -> int:
    parser = argparse.ArgumentParser(description="WatchLess local voice server for Style-Bert-VITS2 models.")
    parser.add_argument("--style-bert-dir", required=True, help="Path to the Style-Bert-VITS2 repo.")
    parser.add_argument("--assets-root", required=True, help="Path to the Style-Bert model_assets folder.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind. Default: 127.0.0.1")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind. Default: 5000")
    parser.add_argument("--device", default="cpu", help="Inference device. Default: cpu")
    args = parser.parse_args()

    runtime = LocalVoiceRuntime(
        style_bert_dir=Path(args.style_bert_dir),
        assets_root=Path(args.assets_root),
        device=args.device,
    )
    LocalVoiceRequestHandler.runtime = runtime
    try:
        server = ThreadingHTTPServer((args.host, args.port), LocalVoiceRequestHandler)
    except OSError as exc:
        if exc.errno == 48 and existing_compatible_server(args.host, args.port):
            print(f"[local-voice] server is already running at http://{args.host}:{args.port}", flush=True)
            return 0
        if exc.errno == 48:
            print(
                f"[local-voice] port {args.port} is already being used by another app. "
                f"Close that app or choose another port with WATCHLESS_LOCAL_VOICE_PORT.",
                flush=True,
            )
            return 1
        raise
    print(f"[local-voice] server ready at http://{args.host}:{args.port}", flush=True)
    print(f"[local-voice] using Style-Bert repo: {runtime.style_bert_dir}", flush=True)
    print(f"[local-voice] using model assets: {runtime.assets_root}", flush=True)
    print(f"[local-voice] loaded model folders: {', '.join(runtime.model_holder.model_names) or 'none'}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover - manual shutdown path
        print("\n[local-voice] shutting down", flush=True)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
