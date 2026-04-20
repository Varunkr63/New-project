from __future__ import annotations

import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = BASE_DIR / "data"
DATA_DIR = Path(os.getenv("DATA_DIR", str(DEFAULT_DATA_DIR)))
DB_PATH = Path(os.getenv("DATABASE_PATH", str(DATA_DIR / "journal.db")))
AUDIO_DIR = Path(os.getenv("AUDIO_DIR", str(DB_PATH.parent / "audio")))


def _fallback_storage_paths() -> tuple[Path, Path]:
    fallback_db_path = DEFAULT_DATA_DIR / "journal.db"
    fallback_audio_dir = DEFAULT_DATA_DIR / "audio"
    return fallback_db_path, fallback_audio_dir


def configure_storage_paths() -> None:
    global DB_PATH, AUDIO_DIR
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        DB_PATH, AUDIO_DIR = _fallback_storage_paths()
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def init_db() -> None:
    configure_storage_paths()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                entry_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                title TEXT NOT NULL,
                transcript TEXT NOT NULL,
                user_notes TEXT NOT NULL DEFAULT '',
                language TEXT NOT NULL,
                detected_language TEXT NOT NULL,
                mood_label TEXT NOT NULL,
                mood_score REAL NOT NULL,
                text_sentiment REAL NOT NULL,
                voice_energy REAL NOT NULL,
                voice_duration REAL NOT NULL,
                insight_summary TEXT NOT NULL,
                audio_path TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(journal_entries)").fetchall()
        }
        if "user_id" not in columns:
            conn.execute("ALTER TABLE journal_entries ADD COLUMN user_id INTEGER")
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_journal_entries_date
            ON journal_entries(entry_date)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_journal_entries_user
            ON journal_entries(user_id, created_at)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_journal_entries_mood
            ON journal_entries(mood_label)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_journal_entries_search
            ON journal_entries(title, transcript, user_notes)
            """
        )


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_db_path() -> Path:
    return DB_PATH


def get_audio_dir() -> Path:
    return AUDIO_DIR
