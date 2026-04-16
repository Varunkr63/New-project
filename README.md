# Voice Journal

A multilingual voice journal built with FastAPI, SQLite, and Whisper.

## Features

- Record your voice directly in the browser
- Convert speech to text with Whisper
- Store a daily journal with transcript, mood, and tags
- Search past entries by text, language, mood, or date
- Analyze mood from both transcript content and voice energy
- View a daily insight dashboard
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

## Notes

- Whisper may download model files the first time it runs.
- Browser recording uses `MediaRecorder`; Chrome and Edge work well.
- If your machine does not support the Whisper dependency stack, replace the implementation in `app/services/transcription.py` with the OpenAI Audio API or `faster-whisper`.
