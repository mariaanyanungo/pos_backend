import uuid

import pytest


def supplier_payload(**overrides):
    payload = {
        "name": "Fresh Foods Ltd",
        "email": "fresh@example.com",
        "phone": "+37063333333",
        "address": "3 Market Road",
    }
    payload.update(overrides)
    return payload



def test_create_supplier(client, auth_headers):
    response = client.post("/suppliers", json=supplier_payload(), headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert uuid.UUID(body["supplier_id"])
    assert body["name"] == "Fresh Foods Ltd"
    assert body["email"] == "fresh@example.com"
    assert body["phone"] == "+37063333333"
    assert body["address"] == "3 Market Road"
    assert body["is_active"] is True
    assert "created_at" in body


@pytest.mark.parametrize("missing_field", ["name", "email", "phone", "address"])
def test_create_supplier_missing_required_field_returns_422(
    client, auth_headers, missing_field
):
    payload = supplier_payload()
    payload.pop(missing_field)
    response = client.post("/suppliers", json=payload, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.parametrize(
    "overrides",
    [{"email": "not-an-email"}, {"name": ""}, {"phone": ""}, {"address": ""}],
)
def test_create_supplier_with_invalid_data_returns_422(client, auth_headers, overrides):
    response = client.post(
        "/suppliers", json=supplier_payload(**overrides), headers=auth_headers
    )
    assert response.status_code == 422


def test_create_supplier_with_duplicate_email_returns_409(client, auth_headers, supplier):
    response = client.post(
        "/suppliers",
        json=supplier_payload(email=supplier["email"]),
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_create_supplier_without_login_returns_401(client):
    response = client.post("/suppliers", json=supplier_payload())
    assert response.status_code == 401


def test_list_suppliers_empty(client, auth_headers):
    response = client.get("/suppliers", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_list_suppliers(client, auth_headers, supplier):
    other = client.post(
        "/suppliers", json=supplier_payload(), headers=auth_headers
    ).json()
    response = client.get("/suppliers", headers=auth_headers)
    assert response.status_code == 200
    ids = {s["supplier_id"] for s in response.json()}
    assert ids == {supplier["supplier_id"], other["supplier_id"]}


def test_get_supplier(client, auth_headers, supplier):
    response = client.get(f"/suppliers/{supplier['supplier_id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == supplier


def test_get_nonexistent_supplier_returns_404(client, auth_headers):
    response = client.get(f"/suppliers/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_get_supplier_with_malformed_id_returns_422(client, auth_headers):
    response = client.get("/suppliers/10000", headers=auth_headers)
    assert response.status_code == 422


def test_update_supplier(client, auth_headers, supplier):
    response = client.put(
        f"/suppliers/{supplier['supplier_id']}",
        json={"name": "Acme Global", "phone": "+37069999999"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Acme Global"
    assert body["phone"] == "+37069999999"
    assert body["email"] == supplier["email"]
    assert body["address"] == supplier["address"]


def test_update_supplier_with_empty_body_changes_nothing(client, auth_headers, supplier):
    response = client.put(
        f"/suppliers/{supplier['supplier_id']}", json={}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json() == supplier


def test_update_supplier_to_duplicate_email_returns_409(client, auth_headers, supplier):
    other = client.post(
        "/suppliers", json=supplier_payload(), headers=auth_headers
    ).json()
    response = client.put(
        f"/suppliers/{other['supplier_id']}",
        json={"email": supplier["email"]},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_update_supplier_keeping_its_own_email_returns_200(client, auth_headers, supplier):
    response = client.put(
        f"/suppliers/{supplier['supplier_id']}",
        json={"email": supplier["email"], "name": "Renamed"},
        headers=auth_headers,
    )
    assert response.status_code == 200


def test_update_supplier_with_invalid_email_returns_422(client, auth_headers, supplier):
    response = client.put(
        f"/suppliers/{supplier['supplier_id']}",
        json={"email": "nope"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_update_nonexistent_supplier_returns_404(client, auth_headers):
    response = client.put(
        f"/suppliers/{uuid.uuid4()}", json={"name": "Ghost"}, headers=auth_headers
    )
    assert response.status_code == 404



def test_delete_supplier(client, auth_headers, supplier):
    response = client.delete(f"/suppliers/{supplier['supplier_id']}", headers=auth_headers)
    assert response.status_code == 204


def test_deleted_supplier_is_hidden_from_default_list(client, auth_headers, supplier):
    client.delete(f"/suppliers/{supplier['supplier_id']}", headers=auth_headers)

    assert client.get("/suppliers", headers=auth_headers).json() == []
    inactive = client.get("/suppliers?is_active=false", headers=auth_headers).json()
    assert [s["supplier_id"] for s in inactive] == [supplier["supplier_id"]]


def test_delete_supplier_with_active_products_returns_409(
    client, auth_headers, supplier, product
):
    response = client.delete(f"/suppliers/{supplier['supplier_id']}", headers=auth_headers)
    assert response.status_code == 409

    persisted = client.get(f"/suppliers/{supplier['supplier_id']}", headers=auth_headers)
    assert persisted.json()["is_active"] is True


def test_delete_supplier_allowed_once_products_are_deactivated(
    client, auth_headers, supplier, product
):
    client.delete(f"/products/{product['product_id']}", headers=auth_headers)
    response = client.delete(f"/suppliers/{supplier['supplier_id']}", headers=auth_headers)
    assert response.status_code == 204


def test_delete_nonexistent_supplier_returns_404(client, auth_headers):
    response = client.delete(f"/suppliers/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404