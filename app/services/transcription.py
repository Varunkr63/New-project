from __future__ import annotations

import audioop
import wave
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np


@lru_cache(maxsize=1)
def get_model() -> Any:
    try:
        import whisper
    except Exception as exc:
        raise RuntimeError(
            "Whisper is not available in this environment. The app can run, but voice transcription is disabled."
        ) from exc
    return whisper.load_model("base")


def load_wav_audio(audio_path: Path) -> np.ndarray:
    with wave.open(str(audio_path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        frame_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
        audio_bytes = wav_file.readframes(frame_count)

    if sample_width != 2:
        raise RuntimeError("Only 16-bit WAV recordings are supported without ffmpeg.")

    if channels > 1:
        audio_bytes = audioop.tomono(audio_bytes, sample_width, 0.5, 0.5)

    if frame_rate != 16000:
        audio_bytes, _ = audioop.ratecv(audio_bytes, sample_width, 1, frame_rate, 16000, None)

    audio = np.frombuffer(audio_bytes, np.int16).astype(np.float32) / 32768.0
    return audio


def transcribe_audio(audio_path: Path, language: str) -> dict[str, str]:
    model = get_model()
    options: dict[str, str | bool] = {"task": "transcribe"}
    if language != "auto":
        options["language"] = language

    if audio_path.suffix.lower() == ".wav":
        audio_input = load_wav_audio(audio_path)
    else:
        audio_input = str(audio_path)

    try:
        result = model.transcribe(audio_input, **options)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "ffmpeg is not installed. Record in WAV format or install ffmpeg to transcribe other audio types."
        ) from exc

    return {
        "text": result.get("text", "").strip(),
        "language": result.get("language", language if language != "auto" else "unknown"),
    }
