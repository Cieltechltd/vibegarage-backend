import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    DATABASE_URL: str
    
    
    MASTER_ADMIN_EMAIL: str
    MASTER_ADMIN_PASSWORD: str
    
   
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    ADMIN_EMAIL: str
   
    PAYSTACK_SECRET_KEY: str
    BASE_URL: str = "https://vibegarage.app"

    
    UPLOAD_AVATAR_DIR: str = "app/uploads/avatars"
    UPLOAD_AUDIO_DIR: str = "app/uploads/audio"
    UPLOAD_COVER_DIR: str = "app/uploads/covers"
    UPLOAD_CLIP_DIR: str = "app/uploads/clips"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra='ignore' 
    )

settings = Settings()