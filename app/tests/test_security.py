import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core import security
from app.core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

TEST_SECRET = "test-secret-key-that-is-at-least-32-chars-long"


@pytest.fixture(autouse=True)
def jwt_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", TEST_SECRET)
    return TEST_SECRET

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


def test_verify_password_with_malformed_hash_returns_false():
    assert verify_password("testpassword", "not-a-real-hash") is False


def test_verify_password_with_empty_hash_returns_false():
    assert verify_password("testpassword", "") is False


def test_create_access_token_round_trip():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"
    assert "jti" in payload


def test_create_access_token_accepts_string_id():
    user_id = str(uuid.uuid4())
    payload = decode_access_token(create_access_token(user_id))
    assert payload["sub"] == user_id


def test_access_token_default_expiry():
    payload = decode_access_token(create_access_token(uuid.uuid4()))
    assert payload["exp"] - payload["iat"] == ACCESS_TOKEN_EXPIRE_MINUTES * 60


def test_access_token_custom_expiry():
    token = create_access_token(uuid.uuid4(), expires_delta=timedelta(minutes=5))
    payload = decode_access_token(token)
    assert payload["exp"] - payload["iat"] == 300


def test_each_token_has_unique_jti():
    user_id = uuid.uuid4()
    first = decode_access_token(create_access_token(user_id))
    second = decode_access_token(create_access_token(user_id))
    assert first["jti"] != second["jti"]


def test_expired_token_is_rejected():
    token = create_access_token(uuid.uuid4(), expires_delta=timedelta(seconds=-1))
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_token_signed_with_other_secret_is_rejected():
    now = datetime.now(timezone.utc)
    forged = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "type": "access",
        },
        "another-secret-key-that-is-32-chars-or-more",
        algorithm=JWT_ALGORITHM,
    )
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(forged)


def test_tampered_token_is_rejected():
    token = create_access_token(uuid.uuid4())
    header, payload, signature = token.split(".")
    flipped = "A" if signature[0] != "A" else "B"
    tampered = ".".join([header, payload, flipped + signature[1:]])
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(tampered)


def test_garbage_token_is_rejected():
    with pytest.raises(jwt.DecodeError):
        decode_access_token("not-a-token")


def test_unsigned_alg_none_token_is_rejected():
    now = datetime.now(timezone.utc)
    unsigned = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "type": "access",
        },
        key=None,
        algorithm="none",
    )
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(unsigned)


def test_token_without_exp_is_rejected():
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "iat": datetime.now(timezone.utc),
            "type": "access",
        },
        TEST_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    with pytest.raises(jwt.MissingRequiredClaimError):
        decode_access_token(token)


def test_token_without_sub_is_rejected():
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"iat": now, "exp": now + timedelta(minutes=5), "type": "access"},
        TEST_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    with pytest.raises(jwt.MissingRequiredClaimError):
        decode_access_token(token)


def test_non_access_token_type_is_rejected():
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "type": "refresh",
        },
        TEST_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)



def test_missing_secret_raises(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setattr(security, "load_dotenv", lambda *a, **k: None)
    with pytest.raises(RuntimeError, match="JWT_SECRET is not set"):
        create_access_token(uuid.uuid4())


def test_short_secret_raises(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "too-short")
    with pytest.raises(RuntimeError, match="at least 32 characters"):
        create_access_token(uuid.uuid4())