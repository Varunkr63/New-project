# Voice Journal

A multilingual voice journal built with FastAPI, SQLite, and configurable transcription backends.

## Features

- User signup and login with session-based access
- Record your voice directly in the browser
- Convert speech to text with API-based transcription or optional local Whisper
- Store a private daily journal with transcript, mood, and tags
- Search past entries by text, language, mood, or date
- Analyze mood from both transcript content and voice energy
- View a personal daily insight dashboard
- Export any journal entry to PDF

## Quick Start

1. Create a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

3. Run the app:

```powershell
uvicorn main:app --reload
```

4. Open `http://127.0.0.1:8000`

5. Create an account, log in, and start recording entries.

## Render Environment Variables

For Render, the app now supports these environment variables:

- `SESSION_SECRET`
- `DATABASE_PATH`
- `AUDIO_DIR`
- `DATA_DIR`
- `TRANSCRIPTION_BACKEND`
- `OPENAI_API_KEY`
- `OPENAI_TRANSCRIPTION_MODEL`

Example values for a Render persistent disk mounted at `/var/data`:

```text
SESSION_SECRET=replace-this-with-a-long-random-secret
DATABASE_PATH=/var/data/journal.db
AUDIO_DIR=/var/data/audio
DATA_DIR=/var/data
TRANSCRIPTION_BACKEND=openai
OPENAI_API_KEY=your-openai-api-key
OPENAI_TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe
```

Recommended Render start command:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

This repo now also includes [render.yaml](C:/Users/hp/OneDrive/Documents/New%20project/render.yaml) with a Render-ready web service definition and `/healthz` health check.

## Notes

- For cloud deployment, `TRANSCRIPTION_BACKEND=openai` is the safest option.
- Local Whisper is still supported, but only when you set `ENABLE_LOCAL_WHISPER=1` or `TRANSCRIPTION_BACKEND=local` and install the Whisper package yourself.
- Browser recording uses `MediaRecorder`; Chrome and Edge work well.
- If transcription is disabled or unavailable, journal entries can still be saved and mood analysis will fall back to notes/title text.
