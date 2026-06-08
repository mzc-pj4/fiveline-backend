from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "order-service"
    environment: str = "dev"
    log_level: str = "INFO"

    database_url: str
    db_schema: str = "order_schema"

    @field_validator("database_url", mode="before")
    @classmethod
    def _fix_db_driver(cls, v: str) -> str:
        if v.startswith("postgresql://") or v.startswith("postgres://"):
            return v.replace("://", "+psycopg://", 1)
        return v

    jwt_secret: str
    jwt_algorithm: str = "HS256"

    product_service_url: str = "http://product-service:8002"
    product_service_timeout_s: float = 3.0

    failure_rate: float = 0.05
    slow_rate: float = 0.03
    slow_response_ms_min: int = 1500
    slow_response_ms_max: int = 3500


settings = Settings()
