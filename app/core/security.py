import os
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from pwdlib import PasswordHash

load_dotenv()

password_hash = PasswordHash.recommended()

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
ACCESS_TOKEN_TYPE = "access"
MIN_SECRET_LENGTH = 32


def _get_jwt_secret() -> str:
    """Read the signing secret at call time so it is never stored in source
    and can be swapped in tests."""
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET is not set. Add it to your .env file.")
    if len(secret) < MIN_SECRET_LENGTH:
        raise RuntimeError(
            f"JWT_SECRET must be at least {MIN_SECRET_LENGTH} characters long."
        )
    return secret


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return password_hash.verify(plain_password, hashed_password)
    except Exception:
        # Malformed or unrecognised hash: treat as a failed verification.
        return False


def create_access_token(
    user_id: uuid.UUID | str,
    expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expire,
        "jti": uuid.uuid4().hex,
        "type": ACCESS_TOKEN_TYPE,
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate an access token.

    Raises a subclass of jwt.PyJWTError when the token is expired, tampered
    with, malformed, uses a different algorithm, lacks required claims, or is
    not an access token.
    """
    payload = jwt.decode(
        token,
        _get_jwt_secret(),
        algorithms=[JWT_ALGORITHM],
        options={"require": ["exp", "sub", "iat"]},
    )
    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise jwt.InvalidTokenError("Token is not an access token")
    return payload
    