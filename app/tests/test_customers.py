def _customer(**overrides):
    payload = {"name": "Jane Shopper", "email": "jane@shoppers.com", "phone": "+37060000001"}
    payload.update(overrides)
    return payload


def test_cashier_can_create_and_find_customers(client, auth_headers):
    created = client.post("/customers", json=_customer(), headers=auth_headers)
    assert created.status_code == 201
    customer_id = created.json()["customer_id"]
    assert client.get(f"/customers/{customer_id}", headers=auth_headers).json()["name"] == "Jane Shopper"
    assert len(client.get("/customers", headers=auth_headers).json()) == 1


def test_customer_email_and_phone_are_optional(client, auth_headers):
    response = client.post("/customers", json={"name": "Walk-in"}, headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["email"] is None


def test_duplicate_customer_email_returns_409(client, auth_headers):
    client.post("/customers", json=_customer(), headers=auth_headers)
    response = client.post("/customers", json=_customer(name="Someone Else"), headers=auth_headers)
    assert response.status_code == 409


def test_customer_validation(client, auth_headers):
    assert client.post("/customers", json={"email": "jane@shoppers.com"}, headers=auth_headers).status_code == 422
    assert client.post("/customers", json=_customer(email="bad"), headers=auth_headers).status_code == 422


def test_update_customer(client, auth_headers):
    customer_id = client.post("/customers", json=_customer(), headers=auth_headers).json()["customer_id"]
    response = client.put(f"/customers/{customer_id}", json={"name": "Jane Q. Shopper"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Jane Q. Shopper"


def test_only_managers_can_delete_customers(client, auth_headers, manager_headers):
    customer_id = client.post("/customers", json=_customer(), headers=auth_headers).json()["customer_id"]
    assert client.delete(f"/customers/{customer_id}", headers=auth_headers).status_code == 403
    assert client.delete(f"/customers/{customer_id}", headers=manager_headers).status_code == 204
    assert client.get("/customers", headers=auth_headers).json() == []


def test_get_nonexistent_customer_returns_404(client, auth_headers):
    assert client.get("/customers/00000000-0000-0000-0000-000000000000", headers=auth_headers).status_code == 404