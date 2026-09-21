from datetime import timedelta

from app.core.security import create_access_token
from app.models.user import User


def test_register_creates_cashier_without_leaking_password(client):
    response = client.post(
        "/auth/register",
        json={"username": "Alice", "email": "Alice@Gmail.com", "password": "testpassword"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "alice"  # normalised
    assert body["email"] == "alice@gmail.com"
    assert body["role"] == "cashier"
    assert body["is_active"] is True
    assert "password" not in body and "hashed_password" not in body


def test_register_cannot_choose_a_role(client):
    response = client.post(
        "/auth/register",
        json={"username": "sneaky", "email": "sneaky@gmail.com", "password": "testpassword", "role": "admin"},
    )
    assert response.status_code == 201
    assert response.json()["role"] == "cashier"


def test_register_duplicate_username_returns_409(client, test_user):
    response = client.post(
        "/auth/register",
        json={"username": "TestUser", "email": "other@gmail.com", "password": "testpassword"},
    )
    assert response.status_code == 409


def test_register_duplicate_email_returns_409(client, test_user):
    response = client.post(
        "/auth/register",
        json={"username": "another", "email": test_user["email"], "password": "testpassword"},
    )
    assert response.status_code == 409


def test_register_short_password_returns_422(client):
    response = client.post(
        "/auth/register",
        json={"username": "alice", "email": "alice@gmail.com", "password": "short"},
    )
    assert response.status_code == 422


def test_register_invalid_email_returns_422(client):
    response = client.post(
        "/auth/register",
        json={"username": "alice", "email": "not-an-email", "password": "testpassword"},
    )
    assert response.status_code == 422


def test_password_is_stored_hashed(client, test_user, db_session):
    user = db_session.query(User).filter_by(username="testuser").one()
    assert user.hashed_password != test_user["password"]
    assert user.hashed_password.startswith("$argon2")


def test_login_returns_bearer_token_that_works(client, test_user):
    response = client.post(
        "/auth/login",
        data={"username": test_user["username"], "password": test_user["password"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    me = client.get("/users/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["username"] == "testuser"


def test_login_username_is_case_insensitive(client, test_user):
    response = client.post("/auth/login", data={"username": "TESTUSER", "password": test_user["password"]})
    assert response.status_code == 200


def test_login_with_wrong_password_returns_401(client, test_user):
    response = client.post("/auth/login", data={"username": "testuser", "password": "wrongpassword"})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_login_with_unknown_user_returns_same_401(client, test_user):
    unknown = client.post("/auth/login", data={"username": "ghost", "password": "testpassword"})
    wrong = client.post("/auth/login", data={"username": "testuser", "password": "nope-nope"})
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()


def test_inactive_user_cannot_log_in(client, test_user, db_session):
    db_session.query(User).filter_by(username="testuser").update({"is_active": False})
    db_session.commit()
    response = client.post("/auth/login", data={"username": "testuser", "password": test_user["password"]})
    assert response.status_code == 401


def test_protected_route_without_token_returns_401(client):
    assert client.get("/products").status_code == 401
    assert client.get("/sales").status_code == 401


def test_garbage_token_returns_401(client):
    response = client.get("/products", headers={"Authorization": "Bearer not.a.token"})
    assert response.status_code == 401


def test_expired_token_returns_401(client, test_user, db_session):
    user = db_session.query(User).filter_by(username="testuser").one()
    token = create_access_token(user.user_id, expires_delta=timedelta(seconds=-1))
    response = client.get("/products", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_token_for_deleted_user_returns_401(client):
    import uuid

    token = create_access_token(uuid.uuid4())
    response = client.get("/products", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_token_of_deactivated_user_returns_403(client, test_user, auth_headers, db_session):
    db_session.query(User).filter_by(username="testuser").update({"is_active": False})
    db_session.commit()
    response = client.get("/products", headers=auth_headers)
    assert response.status_code == 403


def test_bootstrap_admin_is_created_once_and_can_log_in(client, db_session, monkeypatch):
    from dataclasses import replace

    from app.services import auth_service

    monkeypatch.setattr(
        auth_service,
        "settings",
        replace(
            auth_service.settings,
            bootstrap_admin_username="Root",
            bootstrap_admin_email="root@pos.com",
            bootstrap_admin_password="rootpassword1",
        ),
    )
    created = auth_service.bootstrap_admin(db_session)
    assert created is not None and created.role == "admin"
    assert auth_service.bootstrap_admin(db_session) is None  # idempotent
    login = client.post("/auth/login", data={"username": "root", "password": "rootpassword1"})
    assert login.status_code == 200


def test_bootstrap_admin_does_nothing_when_not_configured(client, db_session):
    from app.services import auth_service

    assert auth_service.bootstrap_admin(db_session) is None