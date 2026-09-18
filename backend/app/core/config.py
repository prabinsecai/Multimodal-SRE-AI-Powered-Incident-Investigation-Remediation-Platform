from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    database_url: str = Field(..., description="PostgreSQL async URL")
    redis_url: str = Field(..., description="Redis URL")
    qdrant_url: str = Field(..., description="Qdrant Vector DB URL")
    prometheus_url: str = Field(..., description="Prometheus URL")
    jwt_secret: str = Field(..., description="JWT Secret Key")
    model_provider: str = "deterministic"
    model_name: str = "local"
    ollama_base_url: str = "http://localhost:11434"
    openai_api_key: str = ""
    execution_mode: str = "simulation"
    max_investigation_loops: int = 3
    anomaly_threshold: float = 0.65
    log_level: str = "INFO"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
