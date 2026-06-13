from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional
from pathlib import Path
import os

# Find .env file - check multiple locations
def find_env_file() -> str:
    """Find .env file in project root or backend directory."""
    # Current working directory
    cwd = Path.cwd()
    
    # Possible locations
    locations = [
        cwd / ".env",                           # Current directory
        cwd.parent / ".env",                    # Parent directory (if running from backend/)
        Path(__file__).parent.parent / ".env", # backend/.env
        Path(__file__).parent.parent.parent / ".env",  # project root/.env
    ]
    
    for loc in locations:
        if loc.exists():
            return str(loc)
    
    # Default to current directory
    return ".env"


class Settings(BaseSettings):
    """Application settings with validation."""
    
    # Environment
    environment: str = "development"  # development, staging, production
    debug: bool = False
    
    # Supabase Database
    supabase_url: str
    supabase_key: str
    supabase_service_key: str
    database_url: Optional[str] = None  # Direct PostgreSQL connection (optional)
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0
    redis_url: Optional[str] = None  # Alternative: redis://localhost:6379/0
    
    # WhatsApp
    whatsapp_webhook_url: str = "http://localhost:8000/webhook"
    whatsapp_webhook_secret: Optional[str] = None  # For Meta Cloud API verification
    
    # Gemini LLM
    gemini_api_key: str
    gemini_model: str = "gemini-2.0-flash"  # Updated from gemini-1.5-flash
    gemini_temperature: float = 0.7
    gemini_max_tokens: int = 1024
    gemini_token_limit_per_request: int = 4000  # Safety cap
    
    # LanceDB
    lancedb_path: str = "./data/lancedb"
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 20  # Messages per user per minute
    rate_limit_burst: int = 5  # Allow burst of 5 messages
    
    # Idempotency
    idempotency_ttl: int = 86400  # 24 hours in seconds
    
    # Feature Flags
    safe_mode: bool = False  # Emergency kill switch
    enable_analytics: bool = True
    enable_abandoned_cart: bool = True
    enable_recommendations: bool = True
    
    # Security
    jwt_secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    dashboard_port: int = 8501
    
    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090
    
    # Logging
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    log_format: str = "json"  # json or text
    
    # CORS
    cors_origins: list = ["http://localhost:3000", "http://localhost:8501"]
    
    # Backup
    s3_bucket_name: Optional[str] = None
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    backup_enabled: bool = False
    
    model_config = SettingsConfigDict(
        env_file=find_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars
    )
    
    @property
    def redis_connection_url(self) -> str:
        """Build Redis connection URL."""
        if self.redis_url:
            return self.redis_url
        
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"

@lru_cache()
def get_settings() -> Settings:
    """Singleton settings instance."""
    return Settings()

# Convenience export
settings = get_settings()
