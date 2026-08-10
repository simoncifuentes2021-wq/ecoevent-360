from functools import lru_cache

from pydantic import AliasChoices, AnyHttpUrl, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "EcoEvent 360 API"
    app_env: str = Field(default="local", validation_alias=AliasChoices("ENVIRONMENT", "APP_ENV"))
    api_v1_prefix: str = "/api/v1"
    database_url: str
    migration_database_url: str | None = None
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
    public_app_url: str | None = Field(default=None, validation_alias=AliasChoices("PUBLIC_APP_URL", "FRONTEND_PUBLIC_URL"))
    cloudflare_r2_bucket: str | None = None
    cloudflare_r2_account_id: str | None = None
    cloudflare_r2_access_key_id: str | None = None
    cloudflare_r2_secret_access_key: str | None = None
    cloudflare_r2_public_base_url: str | None = None
    cloudflare_r2_endpoint: str | None = None
    cloudflare_r2_region: str = "auto"
    r2_private_prefix: str = "private"
    r2_public_prefix: str = "public"
    r2_signed_url_expires_seconds: int = 300
    local_private_storage_root: str = "uploads/private"
    force_local_storage: bool = False
    local_public_storage_root: str = "uploads/public"
    max_upload_size_mb: int = 10
    max_image_pixels: int = 40_000_000
    redis_url: str | None = None
    trusted_proxy_count: int = 0
    rate_limit_login_ip: str = "10/60"
    rate_limit_login_identity: str = "5/300"
    rate_limit_public_read: str = "60/60"
    rate_limit_public_submit: str = "10/300"
    rate_limit_bike_code: str = "30/60"
    rate_limit_sensitive_user: str = "60/60"

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
            if not self.redis_url:
                raise ValueError("REDIS_URL is required in production for distributed rate limiting")
        return self

    @property
    def use_r2_storage(self) -> bool:
        if self.force_local_storage:
            return False
        values = (
            self.cloudflare_r2_bucket,
            self.cloudflare_r2_account_id,
            self.cloudflare_r2_access_key_id,
            self.cloudflare_r2_secret_access_key,
        )
        return all(values)

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
