import uuid

import pytest


def test_create_customer(client, auth_headers):
    customer_data = {
        "name": "John Smith",
        "email": "john@example.com",
        "phone": "+37064444444",
    }
    response = client.post("/customers", json=customer_data, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert uuid.UUID(body["customer_id"])
    assert body["name"] == "John Smith"
    assert body["email"] == "john@example.com"
    assert body["phone"] == "+37064444444"
    assert body["is_active"] is True
    assert "created_at" in body


def test_create_customer_with_only_a_name(client, auth_headers):
    response = client.post("/customers", json={"name": "Walk In"}, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] is None
    assert body["phone"] is None


def test_create_two_customers_without_email(client, auth_headers):
    first = client.post("/customers", json={"name": "Walk In One"}, headers=auth_headers)
    second = client.post("/customers", json={"name": "Walk In Two"}, headers=auth_headers)
    assert first.status_code == 201
    assert second.status_code == 201


def test_create_customer_without_name_returns_422(client, auth_headers):
    response = client.post(
        "/customers", json={"email": "noname@example.com"}, headers=auth_headers
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "overrides", [{"name": ""}, {"name": "   "}, {"email": "not-an-email"}]
)
def test_create_customer_with_invalid_data_returns_422(client, auth_headers, overrides):
    customer_data = {"name": "John Smith", "email": "john@example.com"}
    customer_data.update(overrides)
    response = client.post("/customers", json=customer_data, headers=auth_headers)
    assert response.status_code == 422


def test_create_customer_with_duplicate_email_returns_409(client, auth_headers, customer):
    response = client.post(
        "/customers",
        json={"name": "Someone Else", "email": customer["email"]},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_create_customer_without_login_returns_401(client):
    response = client.post("/customers", json={"name": "John Smith"})
    assert response.status_code == 401


def test_list_customers_empty(client, auth_headers):
    response = client.get("/customers", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_list_customers(client, auth_headers, customer):
    other = client.post(
        "/customers", json={"name": "John Smith"}, headers=auth_headers
    ).json()
    response = client.get("/customers", headers=auth_headers)
    assert response.status_code == 200
    ids = {c["customer_id"] for c in response.json()}
    assert ids == {customer["customer_id"], other["customer_id"]}


def test_get_customer(client, auth_headers, customer):
    response = client.get(f"/customers/{customer['customer_id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == customer


def test_get_nonexistent_customer_returns_404(client, auth_headers):
    response = client.get(f"/customers/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_get_customer_with_malformed_id_returns_422(client, auth_headers):
    response = client.get("/customers/10000", headers=auth_headers)
    assert response.status_code == 422




def test_update_customer(client, auth_headers, customer):
    response = client.put(
        f"/customers/{customer['customer_id']}",
        json={"name": "Jane Smith", "phone": "+37065555555"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Jane Smith"
    assert body["phone"] == "+37065555555"
    assert body["email"] == customer["email"]


def test_update_customer_with_empty_body_changes_nothing(client, auth_headers, customer):
    response = client.put(
        f"/customers/{customer['customer_id']}", json={}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json() == customer


def test_update_customer_to_duplicate_email_returns_409(client, auth_headers, customer):
    other = client.post(
        "/customers",
        json={"name": "John Smith", "email": "john@example.com"},
        headers=auth_headers,
    ).json()
    response = client.put(
        f"/customers/{other['customer_id']}",
        json={"email": customer["email"]},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_update_customer_keeping_its_own_email_returns_200(client, auth_headers, customer):
    response = client.put(
        f"/customers/{customer['customer_id']}",
        json={"email": customer["email"], "name": "Renamed"},
        headers=auth_headers,
    )
    assert response.status_code == 200


def test_update_customer_with_invalid_email_returns_422(client, auth_headers, customer):
    response = client.put(
        f"/customers/{customer['customer_id']}",
        json={"email": "nope"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_update_nonexistent_customer_returns_404(client, auth_headers):
    response = client.put(
        f"/customers/{uuid.uuid4()}", json={"name": "Ghost"}, headers=auth_headers
    )
    assert response.status_code == 404



def test_delete_customer(client, auth_headers, customer):
    response = client.delete(f"/customers/{customer['customer_id']}", headers=auth_headers)
    assert response.status_code == 204


def test_deleted_customer_is_hidden_from_default_list(client, auth_headers, customer):
    client.delete(f"/customers/{customer['customer_id']}", headers=auth_headers)

    assert client.get("/customers", headers=auth_headers).json() == []
    inactive = client.get("/customers?is_active=false", headers=auth_headers).json()
    assert [c["customer_id"] for c in inactive] == [customer["customer_id"]]


def test_deleted_customer_can_still_be_fetched_as_inactive(client, auth_headers, customer):
    client.delete(f"/customers/{customer['customer_id']}", headers=auth_headers)
    response = client.get(f"/customers/{customer['customer_id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_delete_nonexistent_customer_returns_404(client, auth_headers):
    response = client.delete(f"/customers/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404