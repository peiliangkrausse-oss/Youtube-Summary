import json
import time

import requests

from watchless_app.config import LM_STUDIO_BASE_URL, LM_STUDIO_NATIVE_BASE_URL, OLLAMA_BASE_URL
from watchless_app.errors import ModelError
from watchless_app.services.settings_store import SettingsStore


MEMORY_ERROR_TRIGGERS = [
    "out of memory",
    "insufficient memory",
    "not enough memory",
    "vram",
    "ram",
    "failed to load",
    "could not load",
    "model loading",
    "unload",
    "loaded model",
    "no model",
    "model not found",
    "invalid model",
    "currently loaded",
]

SUMMARY_MAX_TOKENS = 1500
LONG_TRANSCRIPT_WORDS = 4500
TRANSCRIPT_CHUNK_WORDS = 2500
CHUNK_SUMMARY_MAX_TOKENS = 800
MIN_RETRY_CHUNK_WORDS = 1200


def is_memory_or_model_load_error(message: str) -> bool:
    text = (message or "").lower()
    return any(trigger in text for trigger in MEMORY_ERROR_TRIGGERS)


def transcript_chunks(transcript: str, chunk_words: int = TRANSCRIPT_CHUNK_WORDS) -> list[str]:
    words = transcript.split()
    if not words:
        return []
    return [
        " ".join(words[index:index + chunk_words])
        for index in range(0, len(words), chunk_words)
    ]


class LMStudioClient:
    def __init__(
        self,
        base_url: str = LM_STUDIO_BASE_URL,
        native_base_url: str = LM_STUDIO_NATIVE_BASE_URL,
        ollama_base_url: str = OLLAMA_BASE_URL,
        settings_store: SettingsStore | None = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._native_base_url = native_base_url.rstrip("/")
        self._ollama_base_url = ollama_base_url.rstrip("/")
        self.settings_store = settings_store

    @property
    def base_url(self) -> str:
        return self.settings_store.lm_studio_base_url() if self.settings_store else self._base_url

    @property
    def native_base_url(self) -> str:
        return self.settings_store.lm_studio_native_base_url() if self.settings_store else self._native_base_url

    @property
    def ollama_base_url(self) -> str:
        return self.settings_store.ollama_base_url() if self.settings_store else self._ollama_base_url

    def selected_provider(self) -> str:
        if not self.settings_store:
            return "lm_studio"
        return self.settings_store.load().get("provider", "lm_studio")

    def provider_label(self) -> str:
        return "Ollama" if self.selected_provider() == "ollama" else "LM Studio"

    def provider_status(self) -> dict:
        selected = self.selected_provider()
        statuses = {
            "lm_studio": self._lm_studio_inventory(),
            "ollama": self._ollama_inventory(),
        }
        active = statuses[selected]
        return {
            **active,
            "provider": selected,
            "available_providers": {
                name: {
                    "connected": bool(status.get("connected")),
                    "message": status.get("message", ""),
                }
                for name, status in statuses.items()
            },
        }

    def test_connection(self) -> dict:
        return self.provider_status()

    def model_inventory(self) -> dict:
        status = self.provider_status()
        return {
            **status,
            "base_url": self.base_url if status["provider"] == "lm_studio" else self.ollama_base_url,
            "native_base_url": self.native_base_url if status["provider"] == "lm_studio" else None,
            "ollama_base_url": self.ollama_base_url,
        }

    def _lm_studio_list_models(self) -> list[str]:
        response = requests.get(f"{self.base_url}/models", timeout=5)
        response.raise_for_status()
        payload = response.json()
        raw_models = payload.get("data", []) if isinstance(payload, dict) else []
        models = []
        for item in raw_models:
            if isinstance(item, dict) and item.get("id"):
                models.append(str(item["id"]))
            elif isinstance(item, str):
                models.append(item)
        return models

    def _lm_studio_list_available_models(self) -> list[dict]:
        response = requests.get(f"{self.native_base_url}/models", timeout=5)
        response.raise_for_status()
        payload = response.json()
        raw_models = payload.get("models", []) if isinstance(payload, dict) else []
        models = []
        for item in raw_models:
            if not isinstance(item, dict) or item.get("type") != "llm":
                continue
            loaded_instances = item.get("loaded_instances") or []
            models.append({
                "key": item.get("key") or item.get("id") or "",
                "display_name": item.get("display_name") or item.get("key") or "Local model",
                "type": item.get("type"),
                "publisher": item.get("publisher"),
                "params_string": item.get("params_string"),
                "quantization": item.get("quantization"),
                "size_bytes": item.get("size_bytes"),
                "max_context_length": item.get("max_context_length"),
                "loaded": bool(loaded_instances),
                "loaded_instances": [
                    {
                        "id": instance.get("id"),
                        "config": instance.get("config", {}),
                    }
                    for instance in loaded_instances
                    if isinstance(instance, dict)
                ],
            })
        return [model for model in models if model["key"]]

    def _lm_studio_inventory(self) -> dict:
        try:
            available_models = self._lm_studio_list_available_models()
            loaded_instances = [
                instance
                for model in available_models
                for instance in model["loaded_instances"]
                if instance.get("id")
            ]
            loaded_ids = [instance["id"] for instance in loaded_instances]
            if len(loaded_ids) == 1:
                return {
                    "ok": True,
                    "connected": True,
                    "status": "ready",
                    "models": available_models,
                    "loaded_models": loaded_ids,
                    "current_model": loaded_ids[0],
                    "message": f"Connected to LM Studio. Current model: {loaded_ids[0]}",
                    "source": "native_v1",
                }
            if len(loaded_ids) > 1:
                return {
                    "ok": False,
                    "connected": True,
                    "status": "multiple_models",
                    "models": available_models,
                    "loaded_models": loaded_ids,
                    "current_model": None,
                    "message": "LM Studio reports more than one loaded model. Unload extras before summarizing.",
                    "source": "native_v1",
                }
            return {
                "ok": False,
                "connected": True,
                "status": "no_model",
                "models": available_models,
                "loaded_models": [],
                "current_model": None,
                "message": "LM Studio is connected. Choose one downloaded model and click Load.",
                "source": "native_v1",
            }
        except Exception as native_exc:
            try:
                models = self._lm_studio_list_models()
            except Exception as exc:
                return {
                    "ok": False,
                    "connected": False,
                    "status": "disconnected",
                    "models": [],
                    "loaded_models": [],
                    "current_model": None,
                    "message": f"LM Studio is not reachable at {self.base_url}. Start the local server on port 1234.",
                    "details": str(exc),
                    "source": "openai_v1",
                }
            if not models:
                return {
                    "ok": False,
                    "connected": True,
                    "status": "no_model",
                    "models": [],
                    "loaded_models": [],
                    "current_model": None,
                    "message": "LM Studio is running, but no loaded model was reported.",
                    "details": str(native_exc),
                    "source": "openai_v1",
                }
            if len(models) > 1:
                return {
                    "ok": False,
                    "connected": True,
                    "status": "multiple_models",
                    "models": [
                        {
                            "key": model,
                            "display_name": model,
                            "loaded": True,
                            "loaded_instances": [{"id": model, "config": {}}],
                        }
                        for model in models
                    ],
                    "loaded_models": models,
                    "current_model": None,
                    "message": "LM Studio reports more than one model. Unload extras so the app uses one clear model.",
                    "details": str(native_exc),
                    "source": "openai_v1",
                }
            return {
                "ok": True,
                "connected": True,
                "status": "ready",
                "models": [
                    {
                        "key": models[0],
                        "display_name": models[0],
                        "loaded": True,
                        "loaded_instances": [{"id": models[0], "config": {}}],
                    }
                ],
                "loaded_models": models,
                "current_model": models[0],
                "message": f"Connected to LM Studio. Current model: {models[0]}",
                "details": str(native_exc),
                "source": "openai_v1",
            }

    def _ollama_inventory(self) -> dict:
        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
            response.raise_for_status()
            payload = response.json()
            raw_models = payload.get("models", []) if isinstance(payload, dict) else []
        except Exception as exc:
            return {
                "ok": False,
                "connected": False,
                "status": "disconnected",
                "models": [],
                "loaded_models": [],
                "current_model": None,
                "message": f"Ollama is not reachable at {self.ollama_base_url}. Open Ollama or run 'ollama serve'.",
                "details": str(exc),
                "source": "ollama",
            }

        models = []
        for item in raw_models:
            if not isinstance(item, dict) or not item.get("name"):
                continue
            details = item.get("details", {}) if isinstance(item.get("details"), dict) else {}
            models.append({
                "key": item["name"],
                "display_name": item["name"],
                "params_string": details.get("parameter_size"),
                "quantization": {"name": details.get("quantization_level")} if details.get("quantization_level") else None,
                "size_bytes": item.get("size"),
                "loaded": False,
                "loaded_instances": [],
            })

        if not models:
            return {
                "ok": False,
                "connected": True,
                "status": "no_model",
                "models": [],
                "loaded_models": [],
                "current_model": None,
                "message": "Ollama is connected, but no downloaded models were found yet.",
                "source": "ollama",
            }

        current_model = models[0]["key"]
        return {
            "ok": True,
            "connected": True,
            "status": "ready",
            "models": models,
            "loaded_models": [],
            "current_model": current_model,
            "message": f"Ollama is connected. Choose any installed model, like {current_model}.",
            "source": "ollama",
        }

    def load_model(self, model_key: str) -> dict:
        if self.selected_provider() != "lm_studio":
            raise ModelError("Ollama does not need a manual load step here. Just pick a model and summarize.", "provider_action_blocked", 400)
        selected = (model_key or "").strip()
        if not selected:
            raise ModelError("Choose a model to load first.", "missing_model", 400)
        inventory = self._lm_studio_inventory()
        loaded_models = inventory.get("loaded_models", [])
        if loaded_models and selected not in loaded_models:
            raise ModelError(
                "Unload the currently loaded model before loading another one. This prevents RAM overload on smaller laptops.",
                "model_load_blocked",
                409,
            )
        try:
            response = requests.post(
                f"{self.native_base_url}/models/load",
                json={"model": selected, "echo_load_config": True},
                timeout=600,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as exc:
            message = response.text if "response" in locals() else str(exc)
            if is_memory_or_model_load_error(message):
                raise ModelError(
                    "LM Studio could not load that model. Pick a smaller model or close other heavy apps.",
                    "model_memory",
                ) from exc
            raise ModelError(f"Could not load model: {message}", "model_load_error") from exc
        except Exception as exc:
            raise ModelError(f"Could not load model: {exc}", "model_load_error") from exc

    def unload_model(self, instance_id: str) -> dict:
        if self.selected_provider() != "lm_studio":
            raise ModelError("Ollama does not use the unload button here.", "provider_action_blocked", 400)
        selected = (instance_id or "").strip()
        if not selected:
            inventory = self._lm_studio_inventory()
            loaded = inventory.get("loaded_models", [])
            if len(loaded) == 1:
                selected = loaded[0]
        if not selected:
            raise ModelError("No loaded model was selected to unload.", "missing_model", 400)
        try:
            response = requests.post(
                f"{self.native_base_url}/models/unload",
                json={"instance_id": selected},
                timeout=60,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            raise ModelError(f"Could not unload model: {exc}", "model_unload_error") from exc

    def resolve_model(self, requested_model: str | None = None) -> str:
        status = self.provider_status()
        models = status.get("loaded_models", [])
        requested = (requested_model or "").strip()
        provider = status["provider"]

        if provider == "ollama":
            available = [model["key"] for model in status.get("models", [])]
            if requested and requested in available:
                return requested
            if available:
                return available[0]
            raise ModelError(status["message"], status["status"])

        if not status["ok"]:
            if requested and requested in models:
                return requested
            raise ModelError(status["message"], status["status"])

        current_model = status["current_model"]
        if requested and requested != current_model:
            raise ModelError(
                f"The app will not request '{requested}' because LM Studio reports '{current_model}' as the only loaded model. Select the loaded model or refresh model status.",
                "model_mismatch",
            )
        return current_model

    def summarize(self, transcript: str, system_prompt: str, model: str, progress=None) -> dict:
        if len(transcript.split()) > LONG_TRANSCRIPT_WORDS:
            return self._summarize_long_transcript(transcript, system_prompt, model, progress=progress)
        return self._summarize_once(transcript, system_prompt, model, progress=progress)

    def _summarize_once(
        self,
        transcript: str,
        system_prompt: str,
        model: str,
        progress=None,
        max_tokens: int = SUMMARY_MAX_TOKENS,
    ) -> dict:
        if self.selected_provider() == "ollama":
            return self._ollama_summarize(transcript, system_prompt, model, max_tokens=max_tokens)
        return self._lm_studio_summarize(transcript, system_prompt, model, progress=progress, max_tokens=max_tokens)

    def _summarize_long_transcript(self, transcript: str, system_prompt: str, model: str, progress=None) -> dict:
        started_at = time.monotonic()
        chunks = transcript_chunks(transcript)
        if not chunks:
            return self._summarize_once(transcript, system_prompt, model, progress=progress)

        chunk_prompt = (
            "Use this final-summary brief to decide what matters, but do not follow its final return format yet.\n\n"
            f"Final-summary brief:\n{system_prompt}\n\n"
            "You are reading one piece of a longer YouTube transcript. Create dense source notes for the final summary. "
            "Preserve concrete ideas, claims, examples, decisions, numbers, names, and useful nuance. "
            "Keep the original meaning and language unless the brief clearly asks for a translation. "
            "Remove filler and repetition. Do not write the final summary yet."
        )
        chunk_summaries = []
        total_completion_tokens = 0

        for index, chunk in enumerate(chunks, start=1):
            if progress:
                percent = min(84, 55 + int(((index - 1) / len(chunks)) * 29))
                progress(percent, f"LM Studio is reading part {index} of {len(chunks)}...", completion_tokens=total_completion_tokens)
            completion = self._summarize_chunk_part(chunk, chunk_prompt, model, index, len(chunks))
            chunk_summary = completion["text"].strip()
            if not chunk_summary:
                raise ModelError(f"{self.provider_label()} returned an empty summary for part {index}.", "empty_summary")
            chunk_summaries.append(f"Part {index} notes:\n{chunk_summary}")
            total_completion_tokens += completion.get("completion_tokens") or 0
            if progress:
                percent = min(84, 55 + int((index / len(chunks)) * 29))
                progress(percent, f"Finished part {index} of {len(chunks)}.", completion_tokens=total_completion_tokens)

        if progress:
            progress(85, "Combining part summaries...", completion_tokens=total_completion_tokens)

        final_input = (
            "Combine these notes from the full video into one final summary. "
            "Use the requested format and do not mention chunking.\n\n"
            + "\n\n".join(chunk_summaries)
        )
        final_completion = self._summarize_once(final_input, system_prompt, model, max_tokens=SUMMARY_MAX_TOKENS)
        total_completion_tokens += final_completion.get("completion_tokens") or 0
        elapsed_seconds = max(time.monotonic() - started_at, 0.01)
        return {
            **final_completion,
            "usage": {
                **(final_completion.get("usage") or {}),
                "chunk_count": len(chunks),
            },
            "completion_tokens": total_completion_tokens,
            "elapsed_seconds": round(elapsed_seconds, 2),
        }

    def _summarize_chunk_part(
        self,
        chunk: str,
        chunk_prompt: str,
        model: str,
        index: int,
        total_chunks: int,
    ) -> dict:
        try:
            return self._summarize_once(
                f"Part {index} of {total_chunks}:\n{chunk}",
                chunk_prompt,
                model,
                max_tokens=CHUNK_SUMMARY_MAX_TOKENS,
            )
        except ModelError as exc:
            if exc.error_type != "model_timeout" or len(chunk.split()) <= MIN_RETRY_CHUNK_WORDS:
                raise

        retry_chunks = transcript_chunks(chunk, chunk_words=MIN_RETRY_CHUNK_WORDS)
        retry_summaries = []
        total_completion_tokens = 0
        for retry_index, retry_chunk in enumerate(retry_chunks, start=1):
            completion = self._summarize_once(
                f"Part {index}.{retry_index} of {total_chunks}:\n{retry_chunk}",
                chunk_prompt,
                model,
                max_tokens=CHUNK_SUMMARY_MAX_TOKENS,
            )
            retry_summaries.append(completion["text"].strip())
            total_completion_tokens += completion.get("completion_tokens") or 0
        return {
            "text": "\n".join(summary for summary in retry_summaries if summary),
            "usage": {"retry_chunk_count": len(retry_chunks)},
            "completion_tokens": total_completion_tokens,
        }

    def _lm_studio_summarize(
        self,
        transcript: str,
        system_prompt: str,
        model: str,
        progress=None,
        max_tokens: int = SUMMARY_MAX_TOKENS,
    ) -> dict:
        started_at = time.monotonic()
        generated_text = []
        last_progress_at = started_at
        usage = {}
        try:
            with requests.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Transcript:\n{transcript}"},
                    ],
                    "temperature": 0.3,
                    "max_tokens": max_tokens,
                    "stream": True,
                    "stream_options": {"include_usage": True},
                },
                timeout=600,
                stream=True,
            ) as response:
                if not response.ok:
                    try:
                        payload = response.json()
                        error_message = str(payload.get("error", payload))
                    except Exception:
                        error_message = response.text
                    if is_memory_or_model_load_error(error_message):
                        raise ModelError(
                            "LM Studio could not run the selected model. Unload extra models, keep only one model loaded, and use a model that fits your RAM.",
                            "model_memory",
                        )
                    raise ModelError(f"LM Studio error: {error_message}")

                response.encoding = "utf-8"
                if progress:
                    progress(55, "LM Studio is reading and writing summary...", completion_tokens=0)
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    if line.startswith("data: "):
                        line = line[6:]
                    if line.strip() == "[DONE]":
                        break
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(event.get("usage"), dict):
                        usage = event["usage"]
                    choices = event.get("choices")
                    if not isinstance(choices, list) or not choices:
                        continue
                    first_choice = choices[0] if isinstance(choices[0], dict) else {}
                    delta = first_choice.get("delta") or {}
                    content = delta.get("content", "")
                    if not content:
                        continue
                    generated_text.append(content)
                    now = time.monotonic()
                    if progress and now - last_progress_at >= 1:
                        completion_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or 0
                        if not completion_tokens:
                            completion_tokens = max(1, len("".join(generated_text).split()))
                        percent = min(89, 55 + int((completion_tokens / max_tokens) * 34))
                        progress(
                            percent,
                            "LM Studio is writing summary...",
                            completion_tokens=completion_tokens,
                        )
                        last_progress_at = now
        except ModelError:
            raise
        except requests.exceptions.ConnectionError as exc:
            raise ModelError(
                "Cannot connect to LM Studio. Open LM Studio, start the local server, and confirm it uses port 1234.",
                "model_disconnected",
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise ModelError(
                "LM Studio took too long to answer. Long videos can take several minutes before the model starts writing. Try a shorter video, a smaller model, or close other heavy apps.",
                "model_timeout",
            ) from exc
        except Exception as exc:
            raise ModelError(f"LM Studio error: {exc}") from exc

        try:
            summary = "".join(generated_text).strip()
            if not usage:
                usage = {}
            elapsed_seconds = max(time.monotonic() - started_at, 0.01)
            completion_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or 0
            if not completion_tokens:
                completion_tokens = len(summary.split())
            tokens_per_second = round(float(completion_tokens) / elapsed_seconds, 2) if completion_tokens else None
            return {
                "text": summary,
                "usage": usage,
                "completion_tokens": completion_tokens,
                "elapsed_seconds": round(elapsed_seconds, 2),
                "tokens_per_second": tokens_per_second,
            }
        except Exception as exc:
            raise ModelError("LM Studio returned an unexpected response format.") from exc

    def _ollama_summarize(
        self,
        transcript: str,
        system_prompt: str,
        model: str,
        max_tokens: int = SUMMARY_MAX_TOKENS,
    ) -> dict:
        started_at = time.monotonic()
        resolved_model = self.resolve_model(model)
        try:
            response = requests.post(
                f"{self.ollama_base_url}/api/chat",
                json={
                    "model": resolved_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Transcript:\n{transcript}"},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": max_tokens},
                },
                timeout=600,
            )
            response.raise_for_status()
        except requests.exceptions.ConnectionError as exc:
            raise ModelError("Cannot connect to Ollama. Open Ollama or run 'ollama serve'.", "model_disconnected") from exc
        except requests.exceptions.Timeout as exc:
            raise ModelError("Ollama took too long to answer. The first run can be slow, so try again or use a shorter video.", "model_timeout") from exc
        except Exception as exc:
            raise ModelError(f"Ollama error: {exc}") from exc

        try:
            payload = response.json()
            summary = payload["message"]["content"].strip()
            elapsed_seconds = max(time.monotonic() - started_at, 0.01)
            eval_count = payload.get("eval_count") or 0
            tokens_per_second = round(float(eval_count) / elapsed_seconds, 2) if eval_count else None
            return {
                "text": summary,
                "usage": {
                    "prompt_eval_count": payload.get("prompt_eval_count"),
                    "eval_count": eval_count,
                },
                "completion_tokens": eval_count,
                "elapsed_seconds": round(elapsed_seconds, 2),
                "tokens_per_second": tokens_per_second,
            }
        except Exception as exc:
            raise ModelError("Ollama returned an unexpected response format.") from exc

    def chat(self, *, summary: str, question: str, model: str | None = None) -> str:
        return self._ollama_chat(summary=summary, question=question, model=model) if self.selected_provider() == "ollama" else self._lm_studio_chat(summary=summary, question=question, model=model)

    def _lm_studio_chat(self, *, summary: str, question: str, model: str | None = None) -> str:
        cleaned_summary = (summary or "").strip()
        cleaned_question = (question or "").strip()
        if not cleaned_question:
            raise ModelError("Type a question first.", "missing_chat_question", 400)
        resolved_model = self.resolve_model(model)
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": resolved_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Answer questions about the provided YouTube summary. Be clear, concise, and stay grounded in the summary when possible.",
                        },
                        {
                            "role": "user",
                            "content": f"Summary:\n{cleaned_summary}\n\nQuestion:\n{cleaned_question}",
                        },
                    ],
                    "temperature": 0.3,
                    "max_tokens": 900,
                },
                timeout=120,
            )
        except requests.exceptions.ConnectionError as exc:
            raise ModelError(
                "Cannot connect to LM Studio. Open LM Studio, start the local server, and confirm it uses port 1234.",
                "model_disconnected",
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise ModelError("LM Studio took too long to answer.", "model_timeout") from exc
        except Exception as exc:
            raise ModelError(f"LM Studio error: {exc}") from exc

        if not response.ok:
            try:
                payload = response.json()
                error_message = str(payload.get("error", payload))
            except Exception:
                error_message = response.text
            raise ModelError(f"LM Studio error: {error_message}")

        try:
            payload = response.json()
            return payload["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            raise ModelError("LM Studio returned an unexpected response format.") from exc

    def _ollama_chat(self, *, summary: str, question: str, model: str | None = None) -> str:
        cleaned_summary = (summary or "").strip()
        cleaned_question = (question or "").strip()
        if not cleaned_question:
            raise ModelError("Type a question first.", "missing_chat_question", 400)
        resolved_model = self.resolve_model(model)
        try:
            response = requests.post(
                f"{self.ollama_base_url}/api/chat",
                json={
                    "model": resolved_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Answer questions about the provided YouTube summary. Be clear, concise, and stay grounded in the summary when possible.",
                        },
                        {
                            "role": "user",
                            "content": f"Summary:\n{cleaned_summary}\n\nQuestion:\n{cleaned_question}",
                        },
                    ],
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 900},
                },
                timeout=300,
            )
            response.raise_for_status()
        except requests.exceptions.ConnectionError as exc:
            raise ModelError("Cannot connect to Ollama. Open Ollama or run 'ollama serve'.", "model_disconnected") from exc
        except requests.exceptions.Timeout as exc:
            raise ModelError("Ollama took too long to answer. The first run can be slower than usual.", "model_timeout") from exc
        except Exception as exc:
            raise ModelError(f"Ollama error: {exc}") from exc

        try:
            payload = response.json()
            return payload["message"]["content"].strip()
        except Exception as exc:
            raise ModelError("Ollama returned an unexpected response format.") from exc

    def chat_payload(self, *, summary: str, question: str, model: str | None = None, stream: bool = False) -> dict:
        cleaned_summary = (summary or "").strip()
        cleaned_question = (question or "").strip()
        if not cleaned_question:
            raise ModelError("Type a question first.", "missing_chat_question", 400)
        return {
            "model": self.resolve_model(model),
            "messages": [
                {
                    "role": "system",
                    "content": "Answer questions about the provided YouTube summary. Be clear, concise, and stay grounded in the summary when possible.",
                },
                {
                    "role": "user",
                    "content": f"Summary:\n{cleaned_summary}\n\nQuestion:\n{cleaned_question}",
                },
            ],
            "temperature": 0.3,
            "max_tokens": 900,
            "stream": stream,
        }

    def stream_chat(self, *, summary: str, question: str, model: str | None = None):
        if self.selected_provider() == "ollama":
            yield from self._ollama_stream_chat(summary=summary, question=question, model=model)
            return
        payload = self.chat_payload(summary=summary, question=question, model=model, stream=True)
        try:
            with requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=120,
                stream=True,
            ) as response:
                if not response.ok:
                    raise ModelError(f"LM Studio error: {response.text}")
                response.encoding = "utf-8"
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    if line.startswith("data: "):
                        line = line[6:]
                    if line.strip() == "[DONE]":
                        break
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    delta = event.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
        except requests.exceptions.ConnectionError as exc:
            raise ModelError(
                "Cannot connect to LM Studio. Open LM Studio, start the local server, and confirm it uses port 1234.",
                "model_disconnected",
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise ModelError("LM Studio took too long to answer.", "model_timeout") from exc

    def _ollama_stream_chat(self, *, summary: str, question: str, model: str | None = None):
        cleaned_summary = (summary or "").strip()
        cleaned_question = (question or "").strip()
        if not cleaned_question:
            raise ModelError("Type a question first.", "missing_chat_question", 400)
        resolved_model = self.resolve_model(model)
        try:
            with requests.post(
                f"{self.ollama_base_url}/api/chat",
                json={
                    "model": resolved_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Answer questions about the provided YouTube summary. Be clear, concise, and stay grounded in the summary when possible.",
                        },
                        {
                            "role": "user",
                            "content": f"Summary:\n{cleaned_summary}\n\nQuestion:\n{cleaned_question}",
                        },
                    ],
                    "stream": True,
                    "options": {"temperature": 0.3, "num_predict": 900},
                },
                timeout=300,
                stream=True,
            ) as response:
                response.raise_for_status()
                response.encoding = "utf-8"
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    content = (event.get("message") or {}).get("content", "")
                    if content:
                        yield content
                    if event.get("done"):
                        break
        except requests.exceptions.ConnectionError as exc:
            raise ModelError("Cannot connect to Ollama. Open Ollama or run 'ollama serve'.", "model_disconnected") from exc
        except requests.exceptions.Timeout as exc:
            raise ModelError("Ollama took too long to answer. The first run can be slower than usual.", "model_timeout") from exc
