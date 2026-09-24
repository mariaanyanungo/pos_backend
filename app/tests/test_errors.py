import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.enums import PaymentStatus
from app.core.errors import (
    ConflictError,
    DomainError,
    ForbiddenError,
    IdempotencyConflictError,
    InsufficientStockError,
    InvalidTransitionError,
    NotFoundError,
    UnauthorizedError,
    ValidationFailedError,
    register_exception_handlers,
)


def make_client(exc, raise_server_exceptions=True):
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    def boom():
        raise exc

    return TestClient(app, raise_server_exceptions=raise_server_exceptions)


ERROR_CASES = [
    (DomainError, 400, "domain_error"),
    (NotFoundError, 404, "not_found"),
    (ConflictError, 409, "conflict"),
    (ValidationFailedError, 422, "validation_error"),
    (UnauthorizedError, 401, "unauthorized"),
    (ForbiddenError, 403, "forbidden"),
]


@pytest.mark.parametrize("error_class,status_code,code", ERROR_CASES)
def test_error_maps_to_status_and_code(error_class, status_code, code):
    response = make_client(error_class()).get("/boom")
    assert response.status_code == status_code
    assert response.json() == {"detail": error_class.default_detail, "code": code}


@pytest.mark.parametrize("error_class,status_code,code", ERROR_CASES)
def test_error_uses_custom_detail(error_class, status_code, code):
    response = make_client(error_class("Something specific")).get("/boom")
    assert response.status_code == status_code
    assert response.json()["detail"] == "Something specific"


def test_default_detail_text_is_stable():
    assert NotFoundError.default_detail == "Resource not found."


def test_str_of_error_is_its_detail():
    assert str(NotFoundError("Product not found")) == "Product not found"
    assert str(NotFoundError()) == "Resource not found."


def test_unauthorized_sends_bearer_challenge_header():
    response = make_client(UnauthorizedError()).get("/boom")
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_unauthorized_custom_headers_override_the_default():
    response = make_client(
        UnauthorizedError(headers={"WWW-Authenticate": "Basic"})
    ).get("/boom")
    assert response.headers["WWW-Authenticate"] == "Basic"


@pytest.mark.parametrize(
    "error_class", [DomainError, NotFoundError, ConflictError, ForbiddenError]
)
def test_other_errors_do_not_send_a_challenge_header(error_class):
    response = make_client(error_class()).get("/boom")
    assert "www-authenticate" not in response.headers


def test_error_extra_fields_are_included_in_the_body():
    response = make_client(DomainError("Nope", extra={"field": "price"})).get("/boom")
    assert response.json() == {
        "detail": "Nope",
        "code": "domain_error",
        "field": "price",
    }


def test_invalid_transition_error_with_enums():
    error = InvalidTransitionError(
        "payment", PaymentStatus.CAPTURED, PaymentStatus.PENDING
    )
    response = make_client(error).get("/boom")
    assert response.status_code == 409
    assert response.json() == {
        "detail": "Cannot change payment status from 'captured' to 'pending'.",
        "code": "invalid_transition",
        "current": "captured",
        "target": "pending",
    }


def test_invalid_transition_error_with_plain_strings():
    error = InvalidTransitionError("sale", "voided", "completed")
    assert str(error) == "Cannot change sale status from 'voided' to 'completed'."


def test_insufficient_stock_error():
    error = InsufficientStockError("Cola", requested=5, available=3)
    response = make_client(error).get("/boom")
    assert response.status_code == 409
    assert response.json() == {
        "detail": "Insufficient stock for Cola: requested 5, available 3.",
        "code": "insufficient_stock",
        "requested": 5,
        "available": 3,
    }
    assert error.name == "Cola"
    assert error.requested == 5
    assert error.available == 3


def test_idempotency_conflict_error():
    response = make_client(IdempotencyConflictError()).get("/boom")
    assert response.status_code == 409
    assert response.json()["code"] == "idempotency_conflict"


def test_error_hierarchy():
    assert issubclass(InvalidTransitionError, ConflictError)
    assert issubclass(InsufficientStockError, ConflictError)
    assert issubclass(IdempotencyConflictError, ConflictError)
    for error_class, _, _ in ERROR_CASES:
        assert issubclass(error_class, DomainError)


def test_unexpected_exceptions_are_not_swallowed():
    client = make_client(RuntimeError("bug"), raise_server_exceptions=False)
    response = client.get("/boom")
    assert response.status_code == 500
