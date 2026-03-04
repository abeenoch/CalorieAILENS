from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


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
    access_token_expire_minutes: int = 60
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./calorie_tracker.db"

    # Security hardening
    enable_api_docs: bool = False
    enable_debug_routes: bool = False
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    max_image_bytes: int = 5_000_000
    max_history_limit: int = 100
    share_token_expire_days: int = 30

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
