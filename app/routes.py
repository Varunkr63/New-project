from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.analysis import analyze_mood
from app.db import AUDIO_DIR, get_connection
from app.pdf_export import build_entry_pdf
from app.services.transcription import transcribe_audio

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

LANGUAGE_OPTIONS = [
    ("auto", "Auto detect"),
    ("en", "English"),
    ("hi", "Hindi"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("de", "German"),
    ("ja", "Japanese"),
]

UI_LANGUAGES = {
    "en": {
        "hero": "Voice Journal",
        "sub": "Record your day, transcribe it with Whisper, and track patterns over time.",
    },
    "hi": {
        "hero": "Voice Journal",
        "sub": "Apni awaaz record karein, Whisper se transcript banayein, aur rozana patterns dekhein.",
    },
    "es": {
        "hero": "Diario de Voz",
        "sub": "Graba tu voz, convierte el audio en texto y encuentra patrones diarios.",
    },
}


@router.get("/", response_class=HTMLResponse)
def index(request: Request, ui_lang: str = "en") -> HTMLResponse:
    with get_connection() as conn:
        recent_entries = conn.execute(
            """
            SELECT id, entry_date, title, mood_label, language, created_at
            FROM journal_entries
            ORDER BY created_at DESC
            LIMIT 5
            """
        ).fetchall()

    ui_copy = UI_LANGUAGES.get(ui_lang, UI_LANGUAGES["en"])
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "recent_entries": recent_entries,
            "language_options": LANGUAGE_OPTIONS,
            "ui_lang": ui_lang,
            "ui_copy": ui_copy,
        },
    )


@router.post("/entries")
async def create_entry(
    title: str = Form(...),
    journal_language: str = Form("auto"),
    ui_lang: str = Form("en"),
    user_notes: str = Form(""),
    voice_energy: float = Form(0.0),
    voice_duration: float = Form(0.0),
    audio: UploadFile = File(...),
) -> RedirectResponse:
    suffix = Path(audio.filename or "recording.webm").suffix or ".webm"
    filename = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex}{suffix}"
    audio_path = AUDIO_DIR / filename
    audio_bytes = await audio.read()
    audio_path.write_bytes(audio_bytes)

    try:
        transcription = transcribe_audio(audio_path, journal_language)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc

    transcript = transcription["text"]
    analysis = analyze_mood(transcript, voice_energy, voice_duration)
    entry_date = datetime.now().date().isoformat()
    created_at = datetime.now().isoformat(timespec="seconds")

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO journal_entries (
                entry_date, created_at, title, transcript, user_notes,
                language, detected_language, mood_label, mood_score,
                text_sentiment, voice_energy, voice_duration,
                insight_summary, audio_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry_date,
                created_at,
                title,
                transcript,
                user_notes,
                journal_language,
                transcription["language"],
                analysis["mood_label"],
                analysis["mood_score"],
                analysis["text_sentiment"],
                voice_energy,
                voice_duration,
                analysis["insight_summary"],
                str(audio_path),
            ),
        )
        entry_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()

    return RedirectResponse(url=f"/entries/{entry_id}?ui_lang={ui_lang}", status_code=303)


@router.get("/entries/{entry_id}", response_class=HTMLResponse)
def view_entry(request: Request, entry_id: int, ui_lang: str = "en") -> HTMLResponse:
    with get_connection() as conn:
        entry = conn.execute("SELECT * FROM journal_entries WHERE id = ?", (entry_id,)).fetchone()
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found.")
    return templates.TemplateResponse(
        request,
        "entry_detail.html",
        {"entry": entry, "ui_lang": ui_lang},
    )


@router.get("/history", response_class=HTMLResponse)
def history(
    request: Request,
    q: str = "",
    mood: str = "",
    language: str = "",
    ui_lang: str = "en",
) -> HTMLResponse:
    clauses = []
    params: list[str] = []
    if q:
        clauses.append("(title LIKE ? OR transcript LIKE ? OR user_notes LIKE ?)")
        term = f"%{q}%"
        params.extend([term, term, term])
    if mood:
        clauses.append("mood_label = ?")
        params.append(mood)
    if language:
        clauses.append("(language = ? OR detected_language = ?)")
        params.extend([language, language])

    query = "SELECT * FROM journal_entries"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at DESC"

    with get_connection() as conn:
        entries = conn.execute(query, params).fetchall()

    return templates.TemplateResponse(
        request,
        "history.html",
        {
            "entries": entries,
            "q": q,
            "mood": mood,
            "language": language,
            "language_options": LANGUAGE_OPTIONS,
            "ui_lang": ui_lang,
        },
    )


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, ui_lang: str = "en") -> HTMLResponse:
    with get_connection() as conn:
        stats = conn.execute(
            """
            SELECT
                COUNT(*) AS total_entries,
                ROUND(AVG(mood_score), 3) AS average_mood,
                ROUND(AVG(voice_duration), 1) AS average_duration
            FROM journal_entries
            """
        ).fetchone()
        daily = conn.execute(
            """
            SELECT entry_date, COUNT(*) AS count, ROUND(AVG(mood_score), 3) AS avg_mood
            FROM journal_entries
            GROUP BY entry_date
            ORDER BY entry_date DESC
            LIMIT 7
            """
        ).fetchall()
        moods = conn.execute(
            """
            SELECT mood_label, COUNT(*) AS count
            FROM journal_entries
            GROUP BY mood_label
            ORDER BY count DESC
            """
        ).fetchall()

    top_mood = moods[0]["mood_label"] if moods else "No data yet"
    insight = (
        f"Your most common mood trend is {top_mood}. Keep an eye on how your speaking length changes with mood."
        if moods
        else "Start by recording your first journal to unlock trend insights."
    )

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "stats": stats,
            "daily": daily,
            "moods": moods,
            "insight": insight,
            "ui_lang": ui_lang,
        },
    )


@router.get("/entries/{entry_id}/export")
def export_entry(entry_id: int) -> Response:
    with get_connection() as conn:
        entry = conn.execute("SELECT * FROM journal_entries WHERE id = ?", (entry_id,)).fetchone()
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found.")
    pdf_bytes = build_entry_pdf(dict(entry))
    filename = f"voice-journal-{entry_id}.pdf"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
