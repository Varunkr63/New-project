from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import whisper


@lru_cache(maxsize=1)
def get_model() -> whisper.Whisper:
    return whisper.load_model("base")


def transcribe_audio(audio_path: Path, language: str) -> dict[str, str]:
    model = get_model()
    options: dict[str, str | bool] = {"task": "transcribe"}
    if language != "auto":
        options["language"] = language

    result = model.transcribe(str(audio_path), **options)
    return {
        "text": result.get("text", "").strip(),
        "language": result.get("language", language if language != "auto" else "unknown"),
    }
