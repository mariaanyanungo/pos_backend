import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    prices_include_tax: bool = False
    bootstrap_admin_username: str | None = None
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None


def load_settings() -> Settings:
    secret = os.getenv("JWT_SECRET")
    if not secret or len(secret) < 32:
        raise RuntimeError(
            "CRITICAL CONFIG ERROR: 'JWT_SECRET' must be set to a random string of at least "
            "32 characters (generate one with `openssl rand -hex 32`)."
        )
    return Settings(
        jwt_secret=secret,
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")),
        prices_include_tax=_env_bool("PRICES_INCLUDE_TAX", False),
        bootstrap_admin_username=os.getenv("BOOTSTRAP_ADMIN_USERNAME"),
        bootstrap_admin_email=os.getenv("BOOTSTRAP_ADMIN_EMAIL"),
        bootstrap_admin_password=os.getenv("BOOTSTRAP_ADMIN_PASSWORD"),
    )


settings = load_settings()