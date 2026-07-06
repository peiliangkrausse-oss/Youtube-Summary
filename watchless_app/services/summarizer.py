from watchless_app.errors import AppError
from watchless_app.services.history_store import HistoryStore
from watchless_app.services.lm_studio_client import LMStudioClient
from watchless_app.services.prompt_store import PromptStore
from watchless_app.services.transcript_service import TranscriptService


class Summarizer:
    def __init__(
        self,
        transcript_service: TranscriptService,
        lm_studio: LMStudioClient,
        prompt_store: PromptStore,
        history_store: HistoryStore,
    ):
        self.transcript_service = transcript_service
        self.lm_studio = lm_studio
        self.prompt_store = prompt_store
        self.history_store = history_store

    def summarize(self, url: str, requested_model: str | None = None, progress=None) -> dict:
        provider_label = self.lm_studio.provider_label()

        def update(percent: int, message: str, **changes) -> None:
            if progress:
                progress(percent, message, **changes)

        update(10, "Checking YouTube URL...")
        self.transcript_service.extract_video_id(url)

        update(16, "Reading video title...")
        metadata = self.transcript_service.fetch_metadata(url)
        update(20, f"Checking {provider_label} model...", title=metadata["title"])
        model = self.lm_studio.resolve_model(requested_model)

        update(35, "Fetching YouTube transcript...")
        transcript = self.transcript_service.fetch(url)

        update(55, f"Sending transcript to {provider_label}...")
        system_prompt, _ = self.prompt_store.load()
        completion = self.lm_studio.summarize(transcript["text"], system_prompt, model, progress=progress)
        summary = completion["text"]

        if not summary:
            raise AppError(f"{provider_label} returned an empty summary.", "empty_summary", 500)

        update(90, "Saving Markdown history...")
        title = transcript.get("title") or metadata["title"]
        history = self.history_store.save(
            title=title,
            url=transcript["url"],
            model=model,
            summary=summary,
            video_id=transcript["video_id"],
        )

        update(100, "Summary ready.")
        return {
            "summary": summary,
            "title": title,
            "url": transcript["url"],
            "video_id": transcript["video_id"],
            "model": model,
            "tokens_per_second": completion.get("tokens_per_second"),
            "completion_tokens": completion.get("completion_tokens"),
            "elapsed_seconds": completion.get("elapsed_seconds"),
            "transcript": {
                "word_count": transcript["word_count"],
                "trimmed": transcript["trimmed"],
                "language": transcript["language"],
            },
            "history": history,
        }
