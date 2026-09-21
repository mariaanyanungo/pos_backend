def _user_payload(**overrides):
    payload = {
        "username": "newmanager",
        "email": "newmanager@pos.com",
        "password": "supersecret1",
        "title": "Store Manager",
        "role": "manager",
    }
    payload.update(overrides)
    return payload


def test_admin_creates_user_with_role(client, admin_headers):
    response = client.post("/users", json=_user_payload(), headers=admin_headers)
    assert response.status_code == 201
    assert response.json()["role"] == "manager"
    login = client.post("/auth/login", data={"username": "newmanager", "password": "supersecret1"})
    assert login.status_code == 200


def test_invalid_role_returns_422(client, admin_headers):
    response = client.post("/users", json=_user_payload(role="superuser"), headers=admin_headers)
    assert response.status_code == 422


def test_cashier_and_manager_cannot_manage_users(client, auth_headers, manager_headers):
    for headers in (auth_headers, manager_headers):
        assert client.get("/users", headers=headers).status_code == 403
        assert client.post("/users", json=_user_payload(), headers=headers).status_code == 403


def test_admin_lists_and_gets_users(client, admin_headers, admin_user):
    listing = client.get("/users", headers=admin_headers)
    assert listing.status_code == 200
    assert [u["username"] for u in listing.json()] == ["admin"]
    detail = client.get(f"/users/{admin_user.user_id}", headers=admin_headers)
    assert detail.status_code == 200
    assert client.get("/users/00000000-0000-0000-0000-000000000000", headers=admin_headers).status_code == 404


def test_users_me_returns_current_user(client, auth_headers):
    response = client.get("/users/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"


def test_admin_updates_role_and_password(client, admin_headers, test_user):
    users = client.get("/users", headers=admin_headers).json()
    target = next(u for u in users if u["username"] == "testuser")
    response = client.put(
        f"/users/{target['user_id']}",
        json={"role": "manager", "password": "brandnewpass1"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["role"] == "manager"
    assert client.post("/auth/login", data={"username": "testuser", "password": "testpassword"}).status_code == 401
    assert client.post("/auth/login", data={"username": "testuser", "password": "brandnewpass1"}).status_code == 200


def test_admin_cannot_deactivate_or_demote_self(client, admin_headers, admin_user):
    url = f"/users/{admin_user.user_id}"
    assert client.put(url, json={"is_active": False}, headers=admin_headers).status_code == 409
    assert client.put(url, json={"role": "cashier"}, headers=admin_headers).status_code == 409
    assert client.delete(url, headers=admin_headers).status_code == 409


def test_delete_is_a_soft_delete_and_blocks_login(client, admin_headers, test_user):
    users = client.get("/users", headers=admin_headers).json()
    target = next(u for u in users if u["username"] == "testuser")
    assert client.delete(f"/users/{target['user_id']}", headers=admin_headers).status_code == 204
    assert client.post("/auth/login", data={"username": "testuser", "password": "testpassword"}).status_code == 401
    active = [u["username"] for u in client.get("/users", headers=admin_headers).json()]
    assert "testuser" not in active
    everyone = [u["username"] for u in client.get("/users?include_inactive=true", headers=admin_headers).json()]
    assert "testuser" in everyone