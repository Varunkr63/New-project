# Voice Journal

A multilingual voice journal built with FastAPI, SQLite, and Whisper.

## Features

- User signup and login with session-based access
- Record your voice directly in the browser
- Convert speech to text with Whisper
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

Example values for a Render persistent disk mounted at `/var/data`:

```text
SESSION_SECRET=replace-this-with-a-long-random-secret
DATABASE_PATH=/var/data/journal.db
AUDIO_DIR=/var/data/audio
DATA_DIR=/var/data
```

Recommended Render start command:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

## Notes

- Whisper may download model files the first time it runs.
- Browser recording uses `MediaRecorder`; Chrome and Edge work well.
- If your machine does not support the Whisper dependency stack, replace the implementation in `app/services/transcription.py` with the OpenAI Audio API or `faster-whisper`.
