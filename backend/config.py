from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Google Gemini API (vision only)
    google_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    
    # Groq API (text generation)
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    
    # Opik Observability
    opik_api_key: str = ""
    opik_workspace: str = ""
    opik_url_override: str = "https://www.comet.com/opik/api"
    opik_project_name: str = "calorie-tracker"
    
    # USDA FDC API for nutrition data
    fdc_api_key: str = ""  # Get free key at https://fdc.nal.usda.gov/api-key-signup
    
    # JWT Authentication
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./calorie_tracker.db"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
