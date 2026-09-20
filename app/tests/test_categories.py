import uuid

import pytest


def test_create_category(client, auth_headers):
    response = client.post("/categories", json={"name": "Snacks"}, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert uuid.UUID(body["category_id"])
    assert body["name"] == "Snacks"
    assert body["is_active"] is True
    assert "created_at" in body


def test_create_category_trims_whitespace(client, auth_headers):
    response = client.post(
        "/categories", json={"name": "  Snacks  "}, headers=auth_headers
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Snacks"


def test_create_category_without_name_returns_422(client, auth_headers):
    response = client.post("/categories", json={}, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.parametrize("name", ["", "   "])
def test_create_category_with_blank_name_returns_422(client, auth_headers, name):
    response = client.post("/categories", json={"name": name}, headers=auth_headers)
    assert response.status_code == 422


def test_create_category_with_duplicate_name_returns_409(client, auth_headers, category):
    response = client.post(
        "/categories", json={"name": category["name"]}, headers=auth_headers
    )
    assert response.status_code == 409


def test_create_category_without_login_returns_401(client):
    response = client.post("/categories", json={"name": "Snacks"})
    assert response.status_code == 401


def test_list_categories_empty(client, auth_headers):
    response = client.get("/categories", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_list_categories(client, auth_headers, category):
    other = client.post(
        "/categories", json={"name": "Snacks"}, headers=auth_headers
    ).json()
    response = client.get("/categories", headers=auth_headers)
    assert response.status_code == 200
    names = [c["name"] for c in response.json()]
    assert names == ["Beverages", "Snacks"]
    assert other["category_id"] in [c["category_id"] for c in response.json()]


def test_get_category(client, auth_headers, category):
    response = client.get(f"/categories/{category['category_id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == category


def test_get_nonexistent_category_returns_404(client, auth_headers):
    response = client.get(f"/categories/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_get_category_with_malformed_id_returns_422(client, auth_headers):
    response = client.get("/categories/10000", headers=auth_headers)
    assert response.status_code == 422


def test_update_category(client, auth_headers, category):
    response = client.put(
        f"/categories/{category['category_id']}",
        json={"name": "Drinks"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Drinks"

    persisted = client.get(f"/categories/{category['category_id']}", headers=auth_headers)
    assert persisted.json()["name"] == "Drinks"


def test_update_category_keeping_its_own_name_returns_200(client, auth_headers, category):
    response = client.put(
        f"/categories/{category['category_id']}",
        json={"name": category["name"]},
        headers=auth_headers,
    )
    assert response.status_code == 200


def test_update_category_to_duplicate_name_returns_409(client, auth_headers, category):
    other = client.post(
        "/categories", json={"name": "Snacks"}, headers=auth_headers
    ).json()
    response = client.put(
        f"/categories/{other['category_id']}",
        json={"name": category["name"]},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_update_category_with_blank_name_returns_422(client, auth_headers, category):
    response = client.put(
        f"/categories/{category['category_id']}",
        json={"name": "  "},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_update_nonexistent_category_returns_404(client, auth_headers):
    response = client.put(
        f"/categories/{uuid.uuid4()}", json={"name": "Ghost"}, headers=auth_headers
    )
    assert response.status_code == 404


def test_delete_category(client, auth_headers, category):
    response = client.delete(
        f"/categories/{category['category_id']}", headers=auth_headers
    )
    assert response.status_code == 204


def test_deleted_category_is_hidden_from_default_list(client, auth_headers, category):
    client.delete(f"/categories/{category['category_id']}", headers=auth_headers)

    assert client.get("/categories", headers=auth_headers).json() == []
    inactive = client.get("/categories?is_active=false", headers=auth_headers).json()
    assert [c["category_id"] for c in inactive] == [category["category_id"]]


def test_delete_category_with_active_products_returns_409(
    client, auth_headers, category, product
):
    response = client.delete(
        f"/categories/{category['category_id']}", headers=auth_headers
    )
    assert response.status_code == 409

    persisted = client.get(f"/categories/{category['category_id']}", headers=auth_headers)
    assert persisted.json()["is_active"] is True


def test_delete_category_allowed_once_products_are_deactivated(
    client, auth_headers, category, product
):
    client.delete(f"/products/{product['product_id']}", headers=auth_headers)
    response = client.delete(
        f"/categories/{category['category_id']}", headers=auth_headers
    )
    assert response.status_code == 204


def test_delete_nonexistent_category_returns_404(client, auth_headers):
    response = client.delete(f"/categories/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404