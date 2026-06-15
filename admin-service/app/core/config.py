from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "admin-service"
    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 8

    @field_validator("database_url", mode="before")
    @classmethod
    def _fix_db_driver(cls, v: str) -> str:
        if v.startswith(("postgresql://", "postgres://")):
            return v.replace("://", "+psycopg://", 1)
        return v

    user_schema: str = "user_schema"
    product_schema: str = "product_schema"
    order_schema: str = "order_schema"


settings = Settings()
