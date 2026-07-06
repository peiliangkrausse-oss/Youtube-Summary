from pathlib import Path


APP_NAME = "WatchLess"
PORT = 5055
LM_STUDIO_PORT = 1234
LM_STUDIO_BASE_URL = f"http://127.0.0.1:{LM_STUDIO_PORT}/v1"
LM_STUDIO_NATIVE_BASE_URL = f"http://127.0.0.1:{LM_STUDIO_PORT}/api/v1"
OLLAMA_BASE_URL = "http://127.0.0.1:11434"

SUPPORTED_TRANSCRIPT_LANGUAGES = [
    "en",
    "de",
    "fr",
    "es",
    "it",
    "pt",
    "nl",
    "pl",
    "ru",
    "ja",
    "ko",
    "zh",
]

APP_SUPPORT_DIR = (
    Path.home() / "Library" / "Application Support" / APP_NAME
)
PROMPT_PRESET_FILE = APP_SUPPORT_DIR / "prompt_preset.json"
PROMPT_PRESETS_DIR = APP_SUPPORT_DIR / "prompt_presets"
HISTORY_DIR = APP_SUPPORT_DIR / "history"
CHAT_DIR = APP_SUPPORT_DIR / "chat"
FEEDBACK_EMAIL = "peiliangkrausse@gmail.com"
DONATION_URL = "https://ko-fi.com/peiliang_krausse"

MAX_TRANSCRIPT_WORDS = 50000
MAX_HISTORY_ITEMS = 80
JOB_RETENTION_LIMIT = 50

DEFAULT_PROMPT = """You are summarizing a YouTube transcript for maximum compression and minimum brain strain.

Goal:
Give me the shortest useful summary possible so I can immediately understand the essence of the video, the valuable takeaways, and whether it is worth watching fully.

Core principle:
Do not summarize what the video says. Extract what the video means and what is actually useful.

Instructions:
- Remove filler, repetition, intros, outros, sponsor sections, anecdotes, obvious examples, and low-value details.
- Ignore points that are merely mentioned but not central or useful.
- Prioritize ideas that change my understanding, decision, or actions.
- Keep the output as short as possible without losing the core value.
- Fewer bullets are better if the video has little substance.
- You may include reasonable interpretations, but only when strongly supported by the transcript.
- Do not hallucinate or add external facts.
- If something is unclear, say "I am not sure" or "I do not know."
- Avoid generic summaries, vague advice, overexplaining, repetition, bias, and exaggerated certainty.

Return format:

Essence:
Write 1-3 short sentences capturing the core meaning of the video.

Key Takeaways:
Write only the most valuable takeaways.
Use short bullets.
Do not include more than 5 bullets unless the transcript is unusually information-dense.

Pros and Cons:
Only include this section if applicable.

Pros:
- What the video explains well or makes useful.

Cons:
- Weaknesses, missing nuance, overclaims, fluff, or reasons the video may not be worth watching.

Watch Decision:
Choose exactly one:
- Worth watching fully: high density of useful or nuanced information.
- Skim only: some useful points, but much of the video is filler or repetitive.
- Probably skip: little unique value beyond the summary.

Give one short sentence explaining the decision."""
