from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.analysis import analyze_mood
from app.auth import hash_password, verify_password
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


def get_current_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    claim_legacy_entries(user_id)
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, full_name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()


def template_context(request: Request, ui_lang: str, **extra: object) -> dict[str, object]:
    return {
        "request": request,
        "ui_lang": ui_lang,
        "current_user": get_current_user(request),
        **extra,
    }


def get_entry_for_user(entry_id: int, user_id: int):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM journal_entries WHERE id = ? AND user_id = ?",
            (entry_id, user_id),
        ).fetchone()


def claim_legacy_entries(user_id: int) -> None:
    with get_connection() as conn:
        has_owned_entries = conn.execute(
            "SELECT 1 FROM journal_entries WHERE user_id = ? LIMIT 1",
            (user_id,),
        ).fetchone()
        has_legacy_entries = conn.execute(
            "SELECT 1 FROM journal_entries WHERE user_id IS NULL LIMIT 1"
        ).fetchone()
        if has_owned_entries is None and has_legacy_entries is not None:
            conn.execute(
                "UPDATE journal_entries SET user_id = ? WHERE user_id IS NULL",
                (user_id,),
            )
            conn.commit()


@router.get("/", response_class=HTMLResponse)
def index(request: Request, ui_lang: str = "en") -> HTMLResponse:
    user = get_current_user(request)
    recent_entries = []
    if user is not None:
        with get_connection() as conn:
            recent_entries = conn.execute(
                """
                SELECT id, entry_date, title, mood_label, language, created_at
                FROM journal_entries
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 5
                """,
                (user["id"],),
            ).fetchall()

    ui_copy = UI_LANGUAGES.get(ui_lang, UI_LANGUAGES["en"])
    return templates.TemplateResponse(
        request,
        "index.html",
        template_context(
            request,
            ui_lang,
            recent_entries=recent_entries,
            language_options=LANGUAGE_OPTIONS,
            ui_copy=ui_copy,
        ),
    )


@router.get("/auth", response_class=HTMLResponse)
def auth_page(request: Request, ui_lang: str = "en", mode: str = "login") -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "auth.html",
        template_context(request, ui_lang, mode=mode, error=""),
    )


@router.post("/signup")
def signup(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    ui_lang: str = Form("en"),
):
    normalized_email = email.strip().lower()
    if len(password) < 6:
        return templates.TemplateResponse(
            request,
            "auth.html",
            template_context(
                request,
                ui_lang,
                mode="signup",
                error="Password must be at least 6 characters.",
            ),
            status_code=400,
        )

    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (normalized_email,)).fetchone()
        if existing is not None:
            return templates.TemplateResponse(
                request,
                "auth.html",
                template_context(
                    request,
                    ui_lang,
                    mode="signup",
                    error="An account with that email already exists.",
                ),
                status_code=400,
            )

        conn.execute(
            """
            INSERT INTO users (full_name, email, password_hash, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                full_name.strip(),
                normalized_email,
                hash_password(password),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()

    request.session["user_id"] = user_id
    claim_legacy_entries(user_id)
    return RedirectResponse(url=f"/?ui_lang={ui_lang}", status_code=303)


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    ui_lang: str = Form("en"),
):
    normalized_email = email.strip().lower()
    with get_connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE email = ?", (normalized_email,)).fetchone()

    if user is None or not verify_password(password, user["password_hash"]):
        return templates.TemplateResponse(
            request,
            "auth.html",
            template_context(
                request,
                ui_lang,
                mode="login",
                error="Invalid email or password.",
            ),
            status_code=400,
        )

    request.session["user_id"] = user["id"]
    claim_legacy_entries(user["id"])
    return RedirectResponse(url=f"/?ui_lang={ui_lang}", status_code=303)


@router.post("/logout")
def logout(request: Request, ui_lang: str = Form("en")) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse(url=f"/auth?mode=login&ui_lang={ui_lang}", status_code=303)


@router.post("/entries")
async def create_entry(
    request: Request,
    title: str = Form(...),
    journal_language: str = Form("auto"),
    ui_lang: str = Form("en"),
    user_notes: str = Form(""),
    voice_energy: float = Form(0.0),
    voice_duration: float = Form(0.0),
    audio: UploadFile = File(...),
) -> RedirectResponse:
    user = get_current_user(request)
    if user is None:
        return RedirectResponse(url=f"/auth?mode=login&ui_lang={ui_lang}", status_code=303)

    suffix = Path(audio.filename or "recording.webm").suffix or ".webm"
    if suffix.lower() != ".wav":
        raise HTTPException(
            status_code=400,
            detail="Please refresh the page and record again. The app now requires WAV recording on this machine.",
        )
    filename = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex}{suffix}"
    audio_path = AUDIO_DIR / filename
    audio_bytes = await audio.read()
    audio_path.write_bytes(audio_bytes)

    try:
        transcription = transcribe_audio(audio_path, journal_language)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc

    transcript = transcription["text"].strip() or user_notes.strip() or title.strip()
    analysis = analyze_mood(transcript, voice_energy, voice_duration)
    entry_date = datetime.now().date().isoformat()
    created_at = datetime.now().isoformat(timespec="seconds")

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO journal_entries (
                user_id, entry_date, created_at, title, transcript, user_notes,
                language, detected_language, mood_label, mood_score,
                text_sentiment, voice_energy, voice_duration,
                insight_summary, audio_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user["id"],
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
def view_entry(request: Request, entry_id: int, ui_lang: str = "en"):
    user = get_current_user(request)
    if user is None:
        return RedirectResponse(url=f"/auth?mode=login&ui_lang={ui_lang}", status_code=303)
    entry = get_entry_for_user(entry_id, user["id"])
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found.")
    return templates.TemplateResponse(
        request,
        "entry_detail.html",
        template_context(request, ui_lang, entry=entry),
    )


@router.get("/history", response_class=HTMLResponse)
def history(
    request: Request,
    q: str = "",
    mood: str = "",
    language: str = "",
    ui_lang: str = "en",
):
    user = get_current_user(request)
    if user is None:
        return RedirectResponse(url=f"/auth?mode=login&ui_lang={ui_lang}", status_code=303)

    clauses = ["user_id = ?"]
    params: list[str | int] = [user["id"]]
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

    query = "SELECT * FROM journal_entries WHERE " + " AND ".join(clauses) + " ORDER BY created_at DESC"

    with get_connection() as conn:
        entries = conn.execute(query, params).fetchall()

    return templates.TemplateResponse(
        request,
        "history.html",
        template_context(
            request,
            ui_lang,
            entries=entries,
            q=q,
            mood=mood,
            language=language,
            language_options=LANGUAGE_OPTIONS,
        ),
    )


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, ui_lang: str = "en"):
    user = get_current_user(request)
    if user is None:
        return RedirectResponse(url=f"/auth?mode=login&ui_lang={ui_lang}", status_code=303)

    with get_connection() as conn:
        stats = conn.execute(
            """
            SELECT
                COUNT(*) AS total_entries,
                ROUND(AVG(mood_score), 3) AS average_mood,
                ROUND(AVG(voice_duration), 1) AS average_duration
            FROM journal_entries
            WHERE user_id = ?
            """,
            (user["id"],),
        ).fetchone()
        daily = conn.execute(
            """
            SELECT entry_date, COUNT(*) AS count, ROUND(AVG(mood_score), 3) AS avg_mood
            FROM journal_entries
            WHERE user_id = ?
            GROUP BY entry_date
            ORDER BY entry_date DESC
            LIMIT 7
            """,
            (user["id"],),
        ).fetchall()
        moods = conn.execute(
            """
            SELECT mood_label, COUNT(*) AS count
            FROM journal_entries
            WHERE user_id = ?
            GROUP BY mood_label
            ORDER BY count DESC
            """,
            (user["id"],),
        ).fetchall()
        recent_for_export = conn.execute(
            """
            SELECT id, title, entry_date
            FROM journal_entries
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 5
            """,
            (user["id"],),
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
        template_context(
            request,
            ui_lang,
            stats=stats,
            daily=daily,
            moods=moods,
            insight=insight,
            recent_for_export=recent_for_export,
        ),
    )


@router.get("/entries/{entry_id}/export")
def export_entry(request: Request, entry_id: int) -> Response:
    user = get_current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Login required.")
    entry = get_entry_for_user(entry_id, user["id"])
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found.")
    pdf_bytes = build_entry_pdf(dict(entry))
    filename = f"voice-journal-{entry_id}.pdf"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
