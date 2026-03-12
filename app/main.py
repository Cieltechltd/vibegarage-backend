import os
from fastapi import FastAPI
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
from app.db.init_db import init_db
from app.routers import (
    auth, artist, billing, track, user, 
    search, listener_dashboard, trending, 
    album, admin, lyrics, clips, payouts
)
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles

load_dotenv()
auth_scheme = HTTPBearer()

if not os.path.exists("uploads"):
    os.makedirs("uploads")

@asynccontextmanager
async def lifespan(app: FastAPI):
    
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

# Mounting the uploads folder
app.mount("/static", StaticFiles(directory="uploads"), name="static")

# Registered Routers
app.include_router(auth.router)
app.include_router(artist.router)
app.include_router(track.router)
app.include_router(user.router)
app.include_router(search.router)
app.include_router(listener_dashboard.router)
app.include_router(trending.router)
app.include_router(album.router)
app.include_router(admin.router)
app.include_router(lyrics.router)
app.include_router(clips.router)
app.include_router(billing.router)
app.include_router(payouts.router)

@app.get("/")
def root():
    return {"message": "VibeGarage python backend is running"}