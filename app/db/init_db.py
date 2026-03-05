import os
import uuid
from app.db.database import SessionLocal
from app.models.user import User
from app.core.security import hash_password 

def init_db():
    db = SessionLocal()
    master_email = os.getenv("MASTER_ADMIN_EMAIL")
    master_pass = os.getenv("MASTER_ADMIN_PASSWORD")

    if master_email:
        admin = db.query(User).filter(User.email == master_email).first()
        if not admin:
            print(f"Creating Master Admin: {master_email}")
            new_admin = User(
                id=str(uuid.uuid4()),
                email=master_email,
                password_hash=hash_password(master_pass),
                is_verified=True,
                role="admin"
            )
            db.add(new_admin)
            db.commit()
    db.close()