import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.db import init_db
from app.routes import router

app = FastAPI(title="Voice Journal")

# Middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "voice-journal-secret-key"),
)

# ✅ Include your routes (VERY IMPORTANT)
app.include_router(router)

# ✅ Basic route (health check)
@app.get("/")
def home():
    return {"message": "Voice Journal API is running 🚀"}

# ✅ Initialize DB (optional but recommended)
@app.on_event("startup")
def startup():
    init_db()
