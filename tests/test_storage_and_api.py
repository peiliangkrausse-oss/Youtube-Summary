import json
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError

import watchless_app.routes.api as api_module
import watchless_app.services.prompt_store as prompt_store_module
from watchless_app import desktop as desktop_module
from watchless_app.app import create_app
from watchless_app.services.chat_store import ChatStore
from watchless_app.services.file_ingestion import FileIngestionService
from watchless_app.services.history_store import HistoryStore
from watchless_app.services.local_voice_runner import LocalVoiceRunner
from watchless_app.services.prompt_store import PromptStore
from watchless_app.services.settings_store import SettingsStore
from watchless_app.errors import AppError, ModelError
from watchless_app.services.lm_studio_client import LMStudioClient, transcript_chunks
from watchless_app.services.transcript_service import trim_transcript_for_model


def test_chat_store_persists_messages(tmp_path: Path):
    store = ChatStore(tmp_path)

    messages = store.append_pair("history-1", "What matters?", "The useful takeaway.")

    assert len(messages) == 2
    assert store.load("history-1")[-1]["content"] == "The useful takeaway."


def test_history_store_hides_source_and_model_from_summary(tmp_path: Path):
    store = HistoryStore(tmp_path)

    saved = store.save(
        title="A Video",
        url="https://youtu.be/example12345",
        model="local-model",
        summary="Essence:\nThis is useful.",
        video_id="example12345",
    )
    item = store.get(saved["id"])

    assert "Source:" not in item["summary"]
    assert "Model:" not in item["summary"]
    assert "Essence:" in item["summary"]


def test_prompt_store_rename_and_delete(tmp_path: Path):
    original_dir = prompt_store_module.PROMPT_PRESETS_DIR
    prompt_store_module.PROMPT_PRESETS_DIR = tmp_path
    try:
        store = PromptStore()
        preset = store.save_preset("Study", "Summarize this for studying.")
        renamed = store.rename_preset(preset["id"], "Research")

        assert renamed["name"] == "Research"
        assert renamed["id"] == "research"

        store.delete_preset(renamed["id"])
        assert [item["id"] for item in store.list_presets()] == ["built-in-default"]
    finally:
        prompt_store_module.PROMPT_PRESETS_DIR = original_dir


def test_prompt_store_marks_saved_default_preset(tmp_path: Path):
    original_dir = prompt_store_module.PROMPT_PRESETS_DIR
    original_file = prompt_store_module.PROMPT_PRESET_FILE
    prompt_store_module.PROMPT_PRESETS_DIR = tmp_path / "presets"
    prompt_store_module.PROMPT_PRESET_FILE = tmp_path / "prompt_preset.json"
    try:
        store = PromptStore()
        preset = store.save_preset("Sam", "Summarize this for Sam.")
        store.save(preset["prompt"])

        presets = store.list_presets()

        assert next(item for item in presets if item["id"] == preset["id"])["is_default"] is True
        assert next(item for item in presets if item["id"] == "built-in-default")["is_default"] is False
    finally:
        prompt_store_module.PROMPT_PRESETS_DIR = original_dir
        prompt_store_module.PROMPT_PRESET_FILE = original_file


def test_prompt_store_marks_saved_default_by_preset_id(tmp_path: Path):
    original_dir = prompt_store_module.PROMPT_PRESETS_DIR
    original_file = prompt_store_module.PROMPT_PRESET_FILE
    prompt_store_module.PROMPT_PRESETS_DIR = tmp_path / "presets"
    prompt_store_module.PROMPT_PRESET_FILE = tmp_path / "prompt_preset.json"
    try:
        store = PromptStore()
        first = store.save_preset("First", "Same prompt.")
        second = store.save_preset("Second", "Same prompt.")
        store.save(second["prompt"], second["id"])

        presets = store.list_presets()

        assert next(item for item in presets if item["id"] == second["id"])["is_default"] is True
        assert next(item for item in presets if item["id"] == first["id"])["is_default"] is False
    finally:
        prompt_store_module.PROMPT_PRESETS_DIR = original_dir
        prompt_store_module.PROMPT_PRESET_FILE = original_file


def test_prompt_store_prefers_builtin_default_after_reset(tmp_path: Path):
    original_dir = prompt_store_module.PROMPT_PRESETS_DIR
    original_file = prompt_store_module.PROMPT_PRESET_FILE
    prompt_store_module.PROMPT_PRESETS_DIR = tmp_path / "presets"
    prompt_store_module.PROMPT_PRESET_FILE = tmp_path / "prompt_preset.json"
    try:
        store = PromptStore()
        preset = store.save_preset("Same As Built In", prompt_store_module.DEFAULT_PROMPT)

        presets = store.list_presets()

        assert next(item for item in presets if item["id"] == "built-in-default")["is_default"] is True
        assert next(item for item in presets if item["id"] == preset["id"])["is_default"] is False
    finally:
        prompt_store_module.PROMPT_PRESETS_DIR = original_dir
        prompt_store_module.PROMPT_PRESET_FILE = original_file


def test_app_health_and_empty_chat_question():
    app = create_app()
    client = app.test_client()

    assert client.get("/api/health").status_code == 200
    response = client.post("/api/chat", json={"summary": "A summary", "question": ""})

    assert response.status_code == 400
    assert response.json["error_type"] == "missing_chat_question"


def test_long_transcript_is_preserved_for_chunked_summary():
    words = [f"word{i}" for i in range(7000)]

    text, trimmed = trim_transcript_for_model(words)

    assert trimmed is False
    assert "word0" in text
    assert "word6999" in text
    assert len(text.split()) == len(words)


def test_transcript_chunks_keep_all_words_in_order():
    words = [f"word{i}" for i in range(5100)]

    chunks = transcript_chunks(" ".join(words), chunk_words=2500)

    assert len(chunks) == 3
    assert chunks[0].split()[0] == "word0"
    assert chunks[1].split()[0] == "word2500"
    assert chunks[-1].split()[-1] == "word5099"
    assert " ".join(chunks).split() == words


def test_long_summary_sends_each_chunk_then_combines(monkeypatch):
    client = LMStudioClient()
    calls = []

    def fake_summarize_once(transcript, system_prompt, model, progress=None, max_tokens=1500):
        calls.append(transcript)
        return {
            "text": f"summary {len(calls)}",
            "usage": {},
            "completion_tokens": 5,
            "elapsed_seconds": 0.1,
            "tokens_per_second": 50,
        }

    monkeypatch.setattr(client, "_summarize_once", fake_summarize_once)

    result = client.summarize(" ".join(f"word{i}" for i in range(5100)), "Final prompt", "local-model")

    assert len(calls) == 4
    assert calls[0].startswith("Part 1 of 3:")
    assert calls[1].startswith("Part 2 of 3:")
    assert calls[2].startswith("Part 3 of 3:")
    assert "Part 1 notes:" in calls[3]
    assert result["text"] == "summary 4"
    assert result["usage"]["chunk_count"] == 3


def test_timed_out_chunk_retries_with_smaller_parts(monkeypatch):
    client = LMStudioClient()
    calls = []

    def fake_summarize_once(transcript, system_prompt, model, progress=None, max_tokens=1500):
        calls.append(transcript)
        if transcript.startswith("Part 1 of 3:"):
            raise ModelError("Too slow", "model_timeout")
        return {
            "text": f"summary {len(calls)}",
            "usage": {},
            "completion_tokens": 5,
            "elapsed_seconds": 0.1,
            "tokens_per_second": 50,
        }

    monkeypatch.setattr(client, "_summarize_once", fake_summarize_once)

    result = client.summarize(" ".join(f"word{i}" for i in range(5100)), "Final prompt", "local-model")

    assert any(call.startswith("Part 1.1 of 3:") for call in calls)
    assert any(call.startswith("Part 1.2 of 3:") for call in calls)
    assert result["usage"]["chunk_count"] == 3


def test_lm_studio_stream_accepts_usage_event_without_choices(monkeypatch):
    class FakeResponse:
        ok = True
        encoding = "utf-8"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def iter_lines(self, decode_unicode=True):
            events = [
                {"choices": [{"delta": {"content": "Useful summary."}}]},
                {"choices": [], "usage": {"completion_tokens": 2}},
            ]
            for event in events:
                yield f"data: {json.dumps(event)}"
            yield "data: [DONE]"

    def fake_post(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr("watchless_app.services.lm_studio_client.requests.post", fake_post)

    result = LMStudioClient().summarize("short transcript", "System prompt", "local-model")

    assert result["text"] == "Useful summary."
    assert result["completion_tokens"] == 2


def test_markdown_fallback_keeps_rich_formatting_support():
    source = Path("watchless_app/static/js/modules/text.js").read_text(encoding="utf-8")

    assert "renderInlineMarkdown" in source
    assert "<strong>$1</strong>" in source
    assert "<em>$1</em>" in source
    assert "<code>$1</code>" in source
    assert "<blockquote><p>" in source
    assert "<ol>" in source


def test_homepage_exposes_sidebar_toggle():
    app = create_app()
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert 'id="sidebarToggleBtn"' in page
    assert 'aria-label="Collapse sidebar"' in page


def test_feedback_email_endpoint_opens_mailto(monkeypatch):
    opened_urls = []

    def fake_open(url):
        opened_urls.append(url)
        return True

    monkeypatch.setattr("watchless_app.routes.api._open_external_url", fake_open)
    app = create_app()
    client = app.test_client()

    response = client.post("/api/feedback/email", json={"body": "Bug report: special chars äöü", "subject": "Feedback"})

    assert response.status_code == 200
    assert response.json["opened"] is True
    assert response.json["email"] == "peiliangkrausse@gmail.com"
    assert opened_urls
    assert opened_urls[0].startswith("mailto:peiliangkrausse@gmail.com")
    assert "Bug%20report" in opened_urls[0]


def test_anime_narration_requires_voice_setup(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("WATCHLESS_ANIME_VOICE_ID", raising=False)
    app = create_app()
    client = app.test_client()

    response = client.post("/api/narration/anime", json={"text": "Read this summary."})

    assert response.status_code == 400
    assert response.json["error_type"] == "anime_voice_not_configured"


def test_anime_narration_stream_requires_voice_setup(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("WATCHLESS_ANIME_VOICE_ID", raising=False)
    app = create_app()
    client = app.test_client()

    response = client.post("/api/narration/anime/stream", json={"text": "Read this summary."})

    assert response.status_code == 400
    assert response.json["error_type"] == "anime_voice_not_configured"


def test_anime_voice_upload_requires_api_key(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/narration/anime/voice",
        data={"file": (BytesIO(b"voice sample"), "voice.mp3")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.json["error_type"] == "anime_voice_not_configured"


def test_anime_voice_upload_rejects_wrong_file_type(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/narration/anime/voice",
        data={"api_key": "test-key", "file": (BytesIO(b"not audio"), "voice.txt")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.json["error_type"] == "unsupported_voice_file_type"
    assert "MP3, WAV, M4A, AAC, FLAC, OGG, or WEBM" in response.json["error"]


def test_elevenlabs_voice_list_requires_api_key(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    app = create_app()
    client = app.test_client()

    response = client.post("/api/narration/elevenlabs/voices", json={})

    assert response.status_code == 400
    assert response.json["error_type"] == "anime_voice_not_configured"


def test_elevenlabs_voice_list_uses_current_endpoint_and_cleans_key(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({
                "voices": [
                    {
                        "voice_id": "voice-1",
                        "name": "Test Voice",
                        "category": "generated",
                        "labels": {"use_case": "narration"},
                    }
                ]
            }).encode("utf-8")

    def fake_urlopen(req, **_kwargs):
        captured["url"] = req.full_url
        captured["api_key"] = req.get_header("Xi-api-key")
        return FakeResponse()

    monkeypatch.setattr(api_module, "urlopen", fake_urlopen)

    voices = api_module._elevenlabs_voices('"xi-api-key: test-key"')

    assert captured["url"].startswith("https://api.elevenlabs.io/v2/voices?")
    assert captured["api_key"] == "test-key"
    assert voices[0]["voice_id"] == "voice-1"


def test_elevenlabs_invalid_key_message_matches_dashboard_401():
    error = api_module._elevenlabs_json_error(
        HTTPError("https://api.elevenlabs.io/v2/voices", 401, "Unauthorized", {}, BytesIO(b"unauthorized")),
        "Could not load ElevenLabs voices",
        "elevenlabs_voice_list_failed",
    )

    assert error.error_type == "elevenlabs_invalid_api_key"
    assert "received WatchLess' request" in error.message
    assert "same ElevenLabs workspace" in error.message


def test_elevenlabs_certificate_error_is_actionable():
    error = api_module._elevenlabs_connection_error(
        URLError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate"),
        "Could not reach ElevenLabs",
        "elevenlabs_connection_failed",
    )

    assert error.error_type == "elevenlabs_certificate_error"
    assert "API key was not tested" in error.message
    assert "Install Certificates.command" in error.message


def test_local_voice_wrong_server_error_is_actionable(monkeypatch):
    def fake_urlopen(req, timeout=60):
        raise HTTPError(req.full_url, 404, "Not Found", None, BytesIO(b""))

    monkeypatch.setattr(api_module, "urlopen", fake_urlopen)

    try:
        api_module._local_voice_json("http://127.0.0.1:5000", "/status")
    except Exception as exc:
        error = exc
    else:  # pragma: no cover - defensive failure path
        error = None

    assert error is not None
    assert error.error_type == "local_voice_wrong_server"
    assert "./run-dev.sh voice" in error.message


def test_local_voice_connection_error_is_actionable(monkeypatch):
    def fake_urlopen(req, timeout=60):
        raise URLError("[Errno 61] Connection refused")

    monkeypatch.setattr(api_module, "urlopen", fake_urlopen)

    try:
        api_module._local_voice_json("http://127.0.0.1:5000", "/status")
    except Exception as exc:
        error = exc
    else:  # pragma: no cover - defensive failure path
        error = None

    assert error is not None
    assert error.error_type == "local_voice_connection_failed"
    assert "./run-dev.sh voice" in error.message


def test_local_voice_language_meta_reads_jp_extra_config(tmp_path: Path):
    model_dir = tmp_path / "amitaro"
    model_dir.mkdir()
    config_path = model_dir / "config.json"
    config_path.write_text(json.dumps({"data": {"use_jp_extra": True}}), encoding="utf-8")

    primary_language, languages = api_module._local_voice_language_meta(
        "amitaro",
        {"config_path": str(config_path)},
    )

    assert primary_language == "JP"
    assert languages == ["JP"]


def test_local_voice_status_accepts_get(monkeypatch):
    monkeypatch.setattr(
        api_module,
        "_local_voice_model_summary",
        lambda server_url, refresh=False: {"server_url": server_url, "models": [], "status": {"ok": True}},
    )
    app = create_app()
    client = app.test_client()

    response = client.get("/api/narration/local/status")

    assert response.status_code == 200
    assert response.json["ok"] is True
    assert response.json["server"]["models"] == []


def test_local_voice_status_attempts_autostart(monkeypatch):
    calls = []

    def fake_summary(server_url, refresh=False):
        calls.append("summary")
        if len(calls) == 1:
            raise AppError("Could not reach local voice server.", "local_voice_connection_failed", 502)
        return {"server_url": server_url, "models": [{"name": "Voice"}], "status": {"ok": True}}

    class FakeRunner:
        last_error = ""

        def __init__(self, server_url):
            self.server_url = server_url

        def ensure_started(self):
            calls.append("start")
            return True

    monkeypatch.setattr(api_module, "_local_voice_model_summary", fake_summary)
    monkeypatch.setattr(api_module, "LocalVoiceRunner", FakeRunner)
    app = create_app()
    client = app.test_client()

    response = client.post("/api/narration/local/status", json={"server_url": "http://127.0.0.1:5000"})

    assert response.status_code == 200
    assert response.json["server"]["models"][0]["name"] == "Voice"
    assert calls == ["summary", "start", "summary"]


def test_local_voice_runner_uses_default_paths(monkeypatch):
    monkeypatch.delenv("WATCHLESS_LOCAL_VOICE_REPO", raising=False)
    monkeypatch.delenv("WATCHLESS_LOCAL_VOICE_ASSETS_ROOT", raising=False)

    command = LocalVoiceRunner().command()

    assert command[0].endswith("/Style-Bert-VITS2/.venv/bin/python")
    assert command[2:4] == ["--style-bert-dir", str(Path.home() / "Style-Bert-VITS2")]
    assert command[4:6] == ["--assets-root", str(Path.home() / "Style-Bert-VITS2" / "model_assets")]


def test_local_voice_runner_honors_env_overrides(monkeypatch):
    monkeypatch.setenv("WATCHLESS_LOCAL_VOICE_REPO", "/tmp/custom-style-bert")
    monkeypatch.setenv("WATCHLESS_LOCAL_VOICE_ASSETS_ROOT", "/tmp/custom-assets")
    monkeypatch.setenv("WATCHLESS_LOCAL_VOICE_HOST", "127.0.0.2")
    monkeypatch.setenv("WATCHLESS_LOCAL_VOICE_PORT", "5050")

    command = LocalVoiceRunner().command()

    assert command[0] == "/tmp/custom-style-bert/.venv/bin/python"
    assert command[2:4] == ["--style-bert-dir", "/tmp/custom-style-bert"]
    assert command[4:6] == ["--assets-root", "/tmp/custom-assets"]
    assert command[6:10] == ["--host", "127.0.0.2", "--port", "5050"]


def test_desktop_uses_available_port_when_preferred_is_busy(monkeypatch):
    class FakeSocket:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def bind(self, address):
            self.address = address

        def getsockname(self):
            return ("127.0.0.1", 61234)

    monkeypatch.setattr(desktop_module, "port_is_available", lambda host, port: False)
    monkeypatch.setattr(desktop_module.socket, "socket", lambda *args, **kwargs: FakeSocket())

    port = desktop_module.available_port(preferred=5055)

    assert port == 61234


def test_settings_store_saves_valid_port(tmp_path: Path):
    store = SettingsStore(tmp_path / "settings.json")

    settings = store.save_lm_studio_port("4321")

    assert settings["lm_studio_port"] == 4321
    assert store.lm_studio_base_url() == "http://127.0.0.1:4321/v1"


def test_settings_store_saves_provider(tmp_path: Path):
    store = SettingsStore(tmp_path / "settings.json")

    settings = store.save_provider("ollama")

    assert settings["provider"] == "ollama"
    assert store.load()["provider"] == "ollama"


def test_file_ingestion_reads_text_file():
    class Uploaded:
        filename = "notes.txt"

        def read(self):
            return b"These are useful notes."

    result = FileIngestionService().extract_text(Uploaded())

    assert result["filename"] == "notes.txt"
    assert result["text"] == "These are useful notes."
