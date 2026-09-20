import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.security import (
    JWT_ALGORITHM,
    create_access_token,
    decode_access_token,
    verify_password,
)
from app.models.user import User

RANDOM_ID = "3f2b8c1e-5a4d-4c53-9f0e-7a1d2b3c4d5e"


def deactivate_user(db_session, username):
    user = db_session.query(User).filter(User.username == username).first()
    user.is_active = False
    db_session.commit()


def test_register_user(client):
    user_data = {
        "username": "newcashier",
        "email": "newcashier@example.com",
        "password": "supersecret1",
    }
    response = client.post("/auth/register", json=user_data)
    assert response.status_code == 201
    body = response.json()
    assert uuid.UUID(body["user_id"])
    assert body["username"] == "newcashier"
    assert body["email"] == "newcashier@example.com"
    assert body["role"] == "cashier"
    assert body["is_active"] is True
    assert "created_at" in body


def test_register_never_returns_password_or_hash(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "newcashier",
            "email": "newcashier@example.com",
            "password": "supersecret1",
        },
    )
    body = response.json()
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_stores_hashed_password(client, db_session):
    client.post(
        "/auth/register",
        json={
            "username": "newcashier",
            "email": "newcashier@example.com",
            "password": "supersecret1",
        },
    )
    user = db_session.query(User).filter(User.username == "newcashier").first()
    assert user.hashed_password != "supersecret1"
    assert verify_password("supersecret1", user.hashed_password)


def test_register_ignores_role_in_payload(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "sneaky",
            "email": "sneaky@example.com",
            "password": "supersecret1",
            "role": "admin",
        },
    )
    assert response.status_code == 201
    assert response.json()["role"] == "cashier"


def test_register_duplicate_username_returns_409(client, test_user):
    response = client.post(
        "/auth/register",
        json={
            "username": test_user["username"],
            "email": "different@example.com",
            "password": "supersecret1",
        },
    )
    assert response.status_code == 409


def test_register_duplicate_email_returns_409(client, test_user):
    response = client.post(
        "/auth/register",
        json={
            "username": "differentuser",
            "email": test_user["email"],
            "password": "supersecret1",
        },
    )
    assert response.status_code == 409


@pytest.mark.parametrize(
    "overrides",
    [
        {"username": "ab"},
        {"email": "not-an-email"},
        {"password": "short"},
        {"username": ""},
    ],
)
def test_register_with_invalid_data_returns_422(client, overrides):
    user_data = {
        "username": "newcashier",
        "email": "newcashier@example.com",
        "password": "supersecret1",
    }
    user_data.update(overrides)
    response = client.post("/auth/register", json=user_data)
    assert response.status_code == 422


@pytest.mark.parametrize("missing_field", ["username", "email", "password"])
def test_register_missing_field_returns_422(client, missing_field):
    user_data = {
        "username": "newcashier",
        "email": "newcashier@example.com",
        "password": "supersecret1",
    }
    user_data.pop(missing_field)
    response = client.post("/auth/register", json=user_data)
    assert response.status_code == 422


def test_login_returns_bearer_token(client, test_user):
    response = client.post(
        "/auth/login",
        data={
            "username": test_user["username"],
            "password": test_user["password"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_token_identifies_the_user(client, test_user, auth_headers):
    token = auth_headers["Authorization"].split(" ")[1]
    me = client.get("/auth/me", headers=auth_headers).json()
    assert decode_access_token(token)["sub"] == me["user_id"]


def test_login_with_wrong_password_returns_401(client, test_user):
    response = client.post(
        "/auth/login",
        data={"username": test_user["username"], "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_login_unknown_user_gives_same_error_as_wrong_password(client, test_user):
    wrong_password = client.post(
        "/auth/login",
        data={"username": test_user["username"], "password": "wrongpassword"},
    )
    unknown_user = client.post(
        "/auth/login",
        data={"username": "ghost", "password": "wrongpassword"},
    )
    assert unknown_user.status_code == 401
    assert unknown_user.json() == wrong_password.json()


def test_login_without_credentials_returns_422(client):
    response = client.post("/auth/login", data={})
    assert response.status_code == 422


def test_login_inactive_user_returns_403(client, test_user, db_session):
    deactivate_user(db_session, test_user["username"])
    response = client.post(
        "/auth/login",
        data={
            "username": test_user["username"],
            "password": test_user["password"],
        },
    )
    assert response.status_code == 403



def test_me_returns_current_user(client, test_user, auth_headers):
    response = client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == test_user["username"]
    assert body["email"] == test_user["email"]
    assert "hashed_password" not in body


def test_me_without_token_returns_401(client):
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_me_with_garbage_token_returns_401(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer garbage"})
    assert response.status_code == 401


def test_me_with_wrong_scheme_returns_401(client, auth_headers):
    token = auth_headers["Authorization"].split(" ")[1]
    response = client.get("/auth/me", headers={"Authorization": f"Basic {token}"})
    assert response.status_code == 401


def test_me_with_expired_token_returns_401(client, auth_headers):
    user_id = client.get("/auth/me", headers=auth_headers).json()["user_id"]
    token = create_access_token(user_id, expires_delta=timedelta(seconds=-1))
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_me_with_token_signed_by_another_secret_returns_401(client, auth_headers):
    user_id = client.get("/auth/me", headers=auth_headers).json()["user_id"]
    now = datetime.now(timezone.utc)
    forged = jwt.encode(
        {
            "sub": user_id,
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "type": "access",
        },
        "another-secret-key-that-is-32-chars-or-more",
        algorithm=JWT_ALGORITHM,
    )
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


def test_me_with_token_for_unknown_user_returns_401(client):
    token = create_access_token(uuid.uuid4())
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_me_with_non_uuid_subject_returns_401(client):
    token = create_access_token("not-a-uuid")
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_me_with_inactive_user_returns_403(client, test_user, auth_headers, db_session):
    deactivate_user(db_session, test_user["username"])
    response = client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 403


PROTECTED_ENDPOINTS = [
    ("GET", "/auth/me"),
    ("GET", "/products"),
    ("POST", "/products"),
    ("GET", f"/products/{RANDOM_ID}"),
    ("PUT", f"/products/{RANDOM_ID}"),
    ("DELETE", f"/products/{RANDOM_ID}"),
    ("GET", "/categories"),
    ("POST", "/categories"),
    ("GET", f"/categories/{RANDOM_ID}"),
    ("PUT", f"/categories/{RANDOM_ID}"),
    ("DELETE", f"/categories/{RANDOM_ID}"),
    ("GET", "/suppliers"),
    ("POST", "/suppliers"),
    ("GET", f"/suppliers/{RANDOM_ID}"),
    ("PUT", f"/suppliers/{RANDOM_ID}"),
    ("DELETE", f"/suppliers/{RANDOM_ID}"),
    ("GET", "/customers"),
    ("POST", "/customers"),
    ("GET", f"/customers/{RANDOM_ID}"),
    ("PUT", f"/customers/{RANDOM_ID}"),
    ("DELETE", f"/customers/{RANDOM_ID}"),
    ("POST", f"/inventory/{RANDOM_ID}/adjust"),
    ("GET", f"/inventory/{RANDOM_ID}/movements"),
    ("GET", "/sales"),
    ("POST", "/sales/checkout"),
    ("GET", f"/sales/{RANDOM_ID}"),
    ("POST", f"/sales/{RANDOM_ID}/void"),
    ("POST", f"/sales/{RANDOM_ID}/return"),
    ("GET", f"/payments/{RANDOM_ID}"),
    ("POST", f"/payments/{RANDOM_ID}/capture"),
    ("POST", f"/payments/{RANDOM_ID}/fail"),
    ("GET", f"/receipts/{RANDOM_ID}"),
]


@pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
def test_endpoint_without_login_returns_401(client, method, path):
    response = client.request(method, path)
    assert response.status_code == 401