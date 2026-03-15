import shim
import os
from fastapi import FastAPI
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
from app.db.init_db import init_db
from app.routers import (
    auth, artist, billing, track, 
    listener_dashboard, trending, 
    album, admin, lyrics, clips, payouts, library, discovery, explore, playlists,
    daily_mix, account
)
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
from app.core.config import settings 

load_dotenv()
auth_scheme = HTTPBearer()


def ensure_upload_dirs():
    directories = [
        "app/uploads/avatars",
        "app/uploads/audio",
        "app/uploads/covers",
        "app/uploads/clips"
    ]
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)

@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_upload_dirs() 
    try:
        init_db()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")
    yield

app = FastAPI(
    title="VibeGarage API",
    description="API for VibeGarage music streaming service",
    version="1.0.0",
    swagger_ui_parameters={"persistAuthorization": True},
    lifespan=lifespan 
)

# --- Mounting Static Files ---
app.mount("/static", StaticFiles(directory="app/uploads"), name="static")

# Registered Routers
app.include_router(auth.router)
app.include_router(account.router)
app.include_router(trending.router)
app.include_router(discovery.router)
app.include_router(explore.router)
app.include_router(artist.router)
app.include_router(track.router)
app.include_router(listener_dashboard.router)
app.include_router(album.router)
app.include_router(library.router)
app.include_router(playlists.router)
app.include_router(daily_mix.router)
app.include_router(admin.router)
app.include_router(lyrics.router)
app.include_router(clips.router)
app.include_router(billing.router)
app.include_router(payouts.router)



@app.get("/")
def root():
    return {"message": "VibeGarage python backend is running"}