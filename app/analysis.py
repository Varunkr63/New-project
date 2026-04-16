from __future__ import annotations

from collections import Counter

POSITIVE_WORDS = {
    "happy",
    "joy",
    "grateful",
    "good",
    "great",
    "better",
    "calm",
    "peaceful",
    "excited",
    "hopeful",
    "love",
    "proud",
    "relaxed",
    "productive",
    "smile",
    "thankful",
    "awesome",
    "confident",
    "energized",
    "progress",
    "win",
    "better",
}

NEGATIVE_WORDS = {
    "sad",
    "angry",
    "tired",
    "upset",
    "stress",
    "stressed",
    "anxious",
    "worried",
    "bad",
    "hate",
    "lonely",
    "fear",
    "afraid",
    "overwhelmed",
    "cry",
    "hurt",
    "drained",
    "panic",
    "frustrated",
    "confused",
    "lost",
}


def _tokenize(text: str) -> list[str]:
    cleaned = "".join(ch.lower() if ch.isalpha() or ch.isspace() else " " for ch in text)
    return [token for token in cleaned.split() if token]


def analyze_mood(transcript: str, voice_energy: float, duration_seconds: float) -> dict[str, float | str]:
    tokens = _tokenize(transcript)
    counts = Counter(tokens)
    positive_hits = sum(counts[word] for word in POSITIVE_WORDS)
    negative_hits = sum(counts[word] for word in NEGATIVE_WORDS)
    token_count = max(len(tokens), 1)

    text_sentiment = (positive_hits - negative_hits) / token_count
    duration_factor = min(duration_seconds / 180.0, 1.0)
    voice_component = ((voice_energy - 0.15) * 0.8) + (duration_factor * 0.15)

    if not transcript.strip():
        combined_score = max(min(voice_component, 1.0), -1.0)
    else:
        text_weight = 0.85 if token_count >= 6 else 0.6
        voice_weight = 1 - text_weight
        combined_score = max(min((text_sentiment * text_weight) + (voice_component * voice_weight), 1.0), -1.0)

    if combined_score >= 0.2:
        label = "Positive"
    elif combined_score <= -0.12:
        label = "Low"
    else:
        label = "Reflective"

    insight = build_insight(label, transcript, positive_hits, negative_hits, duration_seconds)
    return {
        "mood_label": label,
        "mood_score": round(combined_score, 3),
        "text_sentiment": round(text_sentiment, 3),
        "insight_summary": insight,
    }


def build_insight(
    mood_label: str,
    transcript: str,
    positive_hits: int,
    negative_hits: int,
    duration_seconds: float,
) -> str:
    if not transcript.strip():
        if mood_label == "Positive":
            return "Your voice energy sounded lively even though the transcript was short. Add notes if you want a richer daily summary."
        if mood_label == "Low":
            return "The recording was brief and low-energy. Add a note about what happened today so the journal can capture more context."
        return "A short check-in was captured. Add a few notes to make the daily insight richer."
    if mood_label == "Positive":
        return (
            f"Your journal sounds steady and upbeat. Positive cues outnumbered negative ones by "
            f"{max(positive_hits - negative_hits, 0)} and you spoke for about {int(duration_seconds)} seconds."
        )
    if mood_label == "Low":
        return (
            "Your entry carries some strain or fatigue. Consider tagging what triggered it and one "
            "small action that could make tomorrow easier."
        )
    return (
        "This entry feels balanced and thoughtful. You may be processing rather than reacting, "
        "which is often a good time to look for patterns across the week."
    )
