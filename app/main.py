from fastapi import FastAPI
from app.db.init_db import init_db
from app.routers import auth, artist, track, user, search, listener_dashboard, trending

app = FastAPI(title="VibeGarage API")


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




@app.get("/")
def root():
    return {"message": "VibeGarage python backend is running"}
