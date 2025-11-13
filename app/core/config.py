from functools import lru_cache
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

class RateLimitSettings(BaseModel):
    signin_ip_window_s: int = Field(60, description="Time window for per-IP sign-in attempts")
    signin_ip_max: int = Field(10, description="Max attempts per IP within the window")
    signin_email_window_s: int = Field(900, description="Time window for per-email attempts")
    signin_email_max: int = Field(10, description="Max attempts per email within the window")
    lock_minutes: int = Field(10, description="Lock duration once threshold exceeded")
    captcha_hint_after: int = Field(5, description="Attempt count to hint CAPTCHA requirement")


class Settings(BaseSettings):
    api_title: str = "AI Todo Auth API"
    api_version: str = "1.0.0"

    database_url: str = Field(..., env="DATABASE_URL")
    redis_url: str = Field(..., env="REDIS_URL")

    jwt_secret: str = Field(..., env="JWT_SECRET")
    jwt_iss: str = Field(..., env="JWT_ISS")
    cookie_domain: str = Field(..., env="COOKIE_DOMAIN")

    access_token_minutes: int = 15
    refresh_token_days: int = 7

    enforce_https: bool = True
    hsts_max_age: int = 31536000

    csrf_cookie_name: str = "csrf_token"
    csrf_header_name: str = "x-csrf-token"

    mail_sender: str = Field(..., env="MAIL_SENDER")
    mail_host: str = Field(..., env="MAIL_HOST")
    mail_port: int = Field(587, env="MAIL_PORT")
    mail_username: str = Field(..., env="MAIL_USERNAME")
    mail_password: str = Field(..., env="MAIL_PASSWORD")
    mail_use_tls: bool = True

    rate_limit: RateLimitSettings = RateLimitSettings()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
