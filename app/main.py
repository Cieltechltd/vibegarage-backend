from fastapi import FastAPI
from fastapi.security import HTTPBearer
from app.db.init_db import init_db
from app.routers import auth, artist, track, user, search, listener_dashboard, trending, album
from dotenv import load_dotenv

auth_scheme = HTTPBearer()
load_dotenv()

app = FastAPI(
    title="VibeGarage API",
    description="API for VibeGarage music streaming service",
    version="1.0.0",
    swagger_ui_parameters={"persistAuthorization": True} 
)


@app.on_event("startup")
def on_startup():
    init_db()

app.include_router(auth.router)
app.include_router(artist.router)
app.include_router(track.router)
app.include_router(user.router)
app.include_router(search.router)
app.include_router(listener_dashboard.router)
app.include_router(trending.router)
app.include_router(album.router)

@app.get("/")
def root():
    return {"message": "VibeGarage python backend is running"}