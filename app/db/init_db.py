from app.db.database import engine, Base
from app.models.user import User
from app.models.artist_profile import ArtistProfile

def init_db():
    Base.metadata.create_all(bind=engine)
