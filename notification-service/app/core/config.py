from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "notification-service"
    database_url: str
    db_schema: str = "notification_schema"
    jwt_secret: str
    jwt_algorithm: str = "HS256"

    @field_validator("database_url", mode="before")
    @classmethod
    def _fix_db_driver(cls, v: str) -> str:
        if v.startswith("postgresql://") or v.startswith("postgres://"):
            return v.replace("://", "+psycopg://", 1)
        return v

    sqs_queue_url: str = ""
    aws_region: str = "ap-northeast-2"


settings = Settings()
