def test_create_category(client, manager_headers):
    response = client.post("/categories", json={"name": "Snacks"}, headers=manager_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Snacks"
    assert body["is_active"] is True
    assert "category_id" in body and "created_at" in body


def test_duplicate_category_name_returns_409(client, manager_headers, category):
    response = client.post("/categories", json={"name": category["name"]}, headers=manager_headers)
    assert response.status_code == 409


def test_create_category_without_name_returns_422(client, manager_headers):
    assert client.post("/categories", json={}, headers=manager_headers).status_code == 422
    assert client.post("/categories", json={"name": ""}, headers=manager_headers).status_code == 422


def test_cashier_can_read_but_not_write_categories(client, auth_headers, category):
    assert client.get("/categories", headers=auth_headers).status_code == 200
    assert client.get(f"/categories/{category['category_id']}", headers=auth_headers).status_code == 200
    assert client.post("/categories", json={"name": "X"}, headers=auth_headers).status_code == 403
    assert client.put(f"/categories/{category['category_id']}", json={"name": "Y"}, headers=auth_headers).status_code == 403
    assert client.delete(f"/categories/{category['category_id']}", headers=auth_headers).status_code == 403


def test_categories_require_login(client):
    assert client.get("/categories").status_code == 401


def test_get_nonexistent_category_returns_404(client, auth_headers):
    assert client.get("/categories/00000000-0000-0000-0000-000000000000", headers=auth_headers).status_code == 404


def test_update_category(client, manager_headers, category):
    response = client.put(
        f"/categories/{category['category_id']}", json={"name": "Drinks"}, headers=manager_headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Drinks"


def test_delete_category_is_soft(client, manager_headers, auth_headers):
    created = client.post("/categories", json={"name": "Temp"}, headers=manager_headers).json()
    assert client.delete(f"/categories/{created['category_id']}", headers=manager_headers).status_code == 204
    names = [c["name"] for c in client.get("/categories", headers=auth_headers).json()]
    assert "Temp" not in names
    names = [c["name"] for c in client.get("/categories?include_inactive=true", headers=auth_headers).json()]
    assert "Temp" in names


def test_cannot_delete_category_with_active_products(client, manager_headers, category, make_product):
    make_product()
    response = client.delete(f"/categories/{category['category_id']}", headers=manager_headers)
    assert response.status_code == 409


def test_pagination(client, manager_headers):
    for index in range(5):
        client.post("/categories", json={"name": f"Cat {index}"}, headers=manager_headers)
    page = client.get("/categories?skip=1&limit=2", headers=manager_headers).json()
    assert len(page) == 2
    assert client.get("/categories?limit=0", headers=manager_headers).status_code == 422