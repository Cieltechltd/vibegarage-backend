from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    ADMIN_EMAIL: str
    
    PAYSTACK_SECRET_KEY: str
    BASE_URL: str = "https://vibegarage.app"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()