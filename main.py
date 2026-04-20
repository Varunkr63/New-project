import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.db import get_audio_dir, get_db_path, init_db
from app.routes import router

app = FastAPI(title="Voice Journal")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "voice-journal-secret-key"),
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(router)


@app.on_event("startup")
def startup() -> None:
    init_db()
    print(f"Voice Journal startup complete. DB_PATH={get_db_path()} AUDIO_DIR={get_audio_dir()}")
