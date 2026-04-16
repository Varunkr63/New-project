from __future__ import annotations

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
AUDIO_DIR = DATA_DIR / "audio"
DB_PATH = DATA_DIR / "journal.db"


def init_db() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    AUDIO_DIR.mkdir(exist_ok=True)
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
