from functools import lru_cache

from pydantic import AliasChoices, AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "EcoEvent 360 API"
    app_env: str = "local"
    api_v1_prefix: str = "/api/v1"
    database_url: str
    secret_key: str = Field(validation_alias=AliasChoices("SECRET_KEY", "JWT_SECRET_KEY"))
    algorithm: str = Field(default="HS256", validation_alias=AliasChoices("ALGORITHM", "JWT_ALGORITHM"))
    access_token_expire_minutes: int = 120
    first_super_admin_email: str = "admin@ecoevent.cl"
    first_super_admin_password: str = "123456"
    first_super_admin_name: str = "EcoEvent Admin"
    backend_cors_origins: list[AnyHttpUrl] | list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
