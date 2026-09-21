import uuid
from datetime import timedelta

import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password():
    password = "testpassword"
    hashed_password = hash_password(password)
    assert isinstance(hashed_password, str)
    assert hashed_password != password


def test_hash_password_is_salted():
    assert hash_password("testpassword") != hash_password("testpassword")


def test_verify_password():
    password = "testpassword"
    hashed_password = hash_password(password)
    assert verify_password(password, hashed_password)
    assert not verify_password("test_password1", hashed_password)


def test_verify_password_with_unknown_hash_format_is_false():
    assert verify_password("testpassword", "not-a-real-hash") is False


def test_access_token_round_trip():
    user_id = uuid.uuid4()
    payload = decode_access_token(create_access_token(user_id))
    assert payload["sub"] == str(user_id)
    assert "exp" in payload and "iat" in payload


def test_expired_token_is_rejected():
    token = create_access_token(uuid.uuid4(), expires_delta=timedelta(seconds=-5))
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_token_signed_with_other_secret_is_rejected():
    forged = jwt.encode({"sub": str(uuid.uuid4()), "exp": 9999999999}, "x" * 40, algorithm="HS256")
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(forged)


def test_tampered_token_is_rejected():
    token = create_access_token(uuid.uuid4())
    header, payload, signature = token.split(".")
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(f"{header}.{payload}.{signature[:-2]}aa")


def test_unsigned_alg_none_token_is_rejected():
    token = jwt.encode({"sub": str(uuid.uuid4()), "exp": 9999999999}, key=None, algorithm="none")
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(token)


def test_token_without_subject_is_rejected():
    token = jwt.encode({"exp": 9999999999}, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    with pytest.raises(jwt.MissingRequiredClaimError):
        decode_access_token(token)


def test_garbage_token_is_rejected():
    with pytest.raises(jwt.DecodeError):
        decode_access_token("definitely.not.jwt")