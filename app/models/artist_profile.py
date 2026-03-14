from sqlalchemy import Column, String, Text, ForeignKey, event
from sqlalchemy.orm import relationship, Session
from app.db.database import Base
from app.core.security import generate_vg_id 

class ArtistProfile(Base):
    __tablename__ = "artist_profiles"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)

    stage_name = Column(String, nullable=False)
    bio = Column(Text, nullable=True)
    avatar = Column(String, nullable=True)  

    user = relationship("User", backref="artist_profile")



def create_artist_profile_signal(mapper, connection, target):
   
    from app.models.user import User 

    if target.role == "ARTIST":
        profile_id = generate_vg_id("VG-A")
        
        connection.execute(
            ArtistProfile.__table__.insert().values(
                id=profile_id,
                user_id=target.id,
                stage_name=target.username or "New Artist",
                bio="Welcome to my Vibe Garage artist profile!"
            )
        )


from app.models.user import User
event.listen(User, "after_insert", create_artist_profile_signal)
