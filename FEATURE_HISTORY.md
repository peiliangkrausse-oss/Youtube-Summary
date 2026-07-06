# WatchLess Feature History

This file records the app's feature evolution, additions, removals, and current product state. It is written so a future developer or LLM can understand what exists, what was intentionally removed, and why the app looks and behaves the way it does.

## Current Version

- Version tag: `v1.0.1`
- Current main commit: this release commit
- App type: local macOS desktop app backed by Flask, LM Studio, and a browser-based UI.
- Primary goal: paste one or more YouTube URLs, summarize them with a locally running LM Studio model, save Markdown history, and chat with the local model about saved summaries.

## Major Feature Timeline

### Architecture Refactor And Tabbed Workflow

- Split the app into a Flask package under `watchless_app/`.
- Added an app factory in `watchless_app/app.py`.
- Added route blueprints under `watchless_app/routes/`.
- Added service modules under `watchless_app/services/`.
- Moved away from a single-file prototype toward a maintainable app structure.
- Added tabbed summary workflow in the browser UI.
- Added saved history tabs and per-tab state.

### Summary Panel Tabs And LM Studio Status

- Moved browser-style tabs into the summary panel.
- Added clearer LM Studio connection and model status.
- Added model inventory handling and model mismatch protection.
- Added guardrails around using exactly one loaded local model.
- Added model load and unload actions when LM Studio native API is available.

### Prompt Presets And Queue Progress

- Added editable default summarization prompt.
- Added saved prompt presets with create, load, rename, and delete flows.
- Added queue-based summary jobs.
- Added per-tab progress bars.
- Added queue display in the sidebar.
- Added job serialization for API polling.

### Streaming Chat, Feedback, Donation, Zoom, Tests

- Added chat panel for asking a local model questions about the current summary.
- Added streaming chat responses over Server-Sent Events.
- Added persisted chat history keyed to saved summary history IDs.
- Added file ingestion for chat context:
  - PDF
  - TXT
  - Markdown
  - CSV
  - JSON
- Added a file text limit to keep chat context bounded.
- Added feedback email copy action.
- Added donation link action.
- Added summary zoom controls persisted in `localStorage`.
- Added focused storage and API tests in `tests/test_storage_and_api.py`.

### Guide Assets, App Icon, And Copy Polish

- Added LM Studio setup guide content and images.
- Added app icons under `App Icons/`.
- Updated feedback copy and support area.
- Tuned guide heading layout.
- Fixed macOS app icon transparency.
- Stabilized summary copy toolbar spacing.

### v1.0.0 Checkpoint

- Added editable LM Studio port setting.
- Added `SettingsStore` for persisted LM Studio port configuration.
- Added `FileIngestionService`.
- Added tests for settings, file ingestion, feedback email, and chat empty-question validation.
- Removed the old legacy single-file HTML prototype from the repository:
  - `yt_summarizer_final_readability_updated.html`
- Added local fallback Markdown rendering and removed the external Markdown CDN dependency.
- Disabled image upload in the chat UI until backend image ingestion is implemented.

## Added Capabilities

- Local-only summary generation through LM Studio.
- Multi-URL queue summarization.
- Job polling with progress states.
- Summary tabs with saved history loading.
- Markdown summary rendering.
- Copy summary action.
- Narration via browser speech synthesis.
- Chat with local model about a summary.
- Streaming chat answer rendering.
- Text/PDF-style file attachment for chat context.
- Prompt preset management.
- Custom default prompt persistence.
- LM Studio model load/unload controls.
- LM Studio port setting.
- Donation and feedback affordances.
- Built-in LM Studio setup guide with screenshots.
- Focused automated tests.
- PyInstaller build path for a macOS app and DMG.

## Removed Or Intentionally Not Included

- Removed `yt_summarizer_final_readability_updated.html`.
  - Reason: the app no longer uses the single-file prototype as source of truth.
- Image upload is visible but disabled.
  - Reason: the UI had an image button, but backend ingestion only supports readable documents. Keeping it disabled avoids promising unsupported behavior.
- No cloud model support.
  - Reason: app goal is local LM Studio use.
- No external frontend CDN dependency.
  - Google Fonts were removed in favor of system fonts.
  - The external `marked` CDN was removed.
  - Markdown renders through the built-in basic fallback parser.

## Known Risks And Gaps

- `watchless_app/static/js/app.js` is large and owns many workflows. It should eventually be split by workflow:
  - tabs
  - queue
  - models/settings
  - prompt presets
  - chat
  - support actions
- `watchless_app/static/css/styles.css` is dense and would benefit from section comments or smaller files.
- For richer Markdown, a local vendored parser could replace the current basic fallback parser.
- The app is packaged for macOS but unsigned/notarized builds may trigger Gatekeeper warnings.
- File ingestion is text extraction only; multimodal image understanding is not implemented.
- Queue jobs are in-memory and reset when the app restarts.
- Tests are focused but not exhaustive.

## Rebuild Priorities If The App Is Lost

1. Recreate the Flask package structure.
2. Recreate service modules for LM Studio, transcripts, summarization, history, chat, prompts, settings, file ingestion, and job queue.
3. Recreate the single-page HTML shell.
4. Recreate the dark desktop UI from `DESIGN.md`.
5. Recreate the frontend workflows from `APP_BLUEPRINT.md`.
6. Recreate tests from current behavior.
7. Rebuild the macOS launcher and PyInstaller spec.
