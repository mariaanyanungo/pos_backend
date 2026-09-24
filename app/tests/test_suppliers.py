def _supplier(**overrides):
    payload = {
        "name": "Acme Wholesale",
        "email": "orders@acme-wholesale.com",
        "phone": "+37060000000",
        "address": "1 Market Street, Vilnius",
    }
    payload.update(overrides)
    return payload


def test_manager_creates_lists_and_gets_supplier(client, manager_headers):
    created = client.post("/suppliers", json=_supplier(), headers=manager_headers)
    assert created.status_code == 201
    supplier_id = created.json()["supplier_id"]
    assert (
        client.get("/suppliers", headers=manager_headers).json()[0]["supplier_id"]
        == supplier_id
    )
    assert (
        client.get(f"/suppliers/{supplier_id}", headers=manager_headers).status_code
        == 200
    )


def test_cashier_cannot_access_suppliers(client, auth_headers):
    assert client.get("/suppliers", headers=auth_headers).status_code == 403
    assert (
        client.post("/suppliers", json=_supplier(), headers=auth_headers).status_code
        == 403
    )


def test_duplicate_supplier_email_returns_409(client, manager_headers):
    client.post("/suppliers", json=_supplier(), headers=manager_headers)
    response = client.post(
        "/suppliers", json=_supplier(name="Other"), headers=manager_headers
    )
    assert response.status_code == 409


def test_supplier_validation(client, manager_headers):
    assert (
        client.post(
            "/suppliers", json=_supplier(email="nope"), headers=manager_headers
        ).status_code
        == 422
    )
    body = _supplier()
    del body["address"]
    assert (
        client.post("/suppliers", json=body, headers=manager_headers).status_code == 422
    )


def test_update_and_soft_delete_supplier(client, manager_headers):
    supplier_id = client.post(
        "/suppliers", json=_supplier(), headers=manager_headers
    ).json()["supplier_id"]
    updated = client.put(
        f"/suppliers/{supplier_id}",
        json={"phone": "+37061111111"},
        headers=manager_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["phone"] == "+37061111111"
    assert (
        client.delete(f"/suppliers/{supplier_id}", headers=manager_headers).status_code
        == 204
    )
    assert client.get("/suppliers", headers=manager_headers).json() == []
    assert (
        client.get(f"/suppliers/{supplier_id}", headers=manager_headers).status_code
        == 200
    )  # still readable by id


def test_get_nonexistent_supplier_returns_404(client, manager_headers):
    assert (
        client.get(
            "/suppliers/00000000-0000-0000-0000-000000000000", headers=manager_headers
        ).status_code
        == 404
    )
