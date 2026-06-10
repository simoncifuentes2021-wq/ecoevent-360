from functools import lru_cache

from pydantic import AliasChoices, AnyHttpUrl, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "EcoEvent 360 API"
    app_env: str = Field(default="local", validation_alias=AliasChoices("ENVIRONMENT", "APP_ENV"))
    api_v1_prefix: str = "/api/v1"
    database_url: str
    secret_key: str = Field(validation_alias=AliasChoices("SECRET_KEY", "JWT_SECRET_KEY"))
    algorithm: str = Field(default="HS256", validation_alias=AliasChoices("ALGORITHM", "JWT_ALGORITHM"))
    access_token_expire_minutes: int = 1440
    first_super_admin_email: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SEED_ADMIN_EMAIL", "FIRST_SUPER_ADMIN_EMAIL"),
    )
    first_super_admin_password: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SEED_ADMIN_PASSWORD", "FIRST_SUPER_ADMIN_PASSWORD"),
    )
    first_super_admin_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SEED_ADMIN_NAME", "FIRST_SUPER_ADMIN_NAME"),
    )
    backend_cors_origins: list[AnyHttpUrl] | list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    cloudflare_r2_bucket: str | None = None
    cloudflare_r2_account_id: str | None = None
    cloudflare_r2_access_key_id: str | None = None
    cloudflare_r2_secret_access_key: str | None = None
    cloudflare_r2_public_base_url: str | None = None
    max_upload_size_mb: int = 10

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        database_url = value.strip().strip("\"'")
        if database_url.startswith("postgres://"):
            return database_url.replace("postgres://", "postgresql+psycopg://", 1)
        if database_url.startswith("postgresql://"):
            return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return database_url

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.app_env.lower() == "production":
            if self.secret_key in {"change-me-in-production", "change-me", "secret"}:
                raise ValueError("SECRET_KEY must be set to a strong value in production")
            if "*" in self.backend_cors_origins:
                raise ValueError("BACKEND_CORS_ORIGINS cannot contain '*' in production")
        return self

    @property
    def use_r2_storage(self) -> bool:
        values = (
            self.cloudflare_r2_bucket,
            self.cloudflare_r2_account_id,
            self.cloudflare_r2_access_key_id,
            self.cloudflare_r2_secret_access_key,
            self.cloudflare_r2_public_base_url,
        )
        return all(values)

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
